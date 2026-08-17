import os
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import create_react_agent
from langchain_groq import ChatGroq
from langchain_tavily import TavilySearch
from dotenv import load_dotenv

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command

load_dotenv()

# ---------- TOOLS ----------
search_tool = TavilySearch(max_results=3)

# ---------- LLMs ----------
writer_llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.7)

# ---------- STATE ----------
# No 'messages' field needed here — create_react_agent manages its own
# internal tool-calling loop and just hands us back a finished draft.
class State(TypedDict):
    topic: str
    draft: str
    review_feedback: str
    is_approved: bool
    attempt: int


WRITER_SYSTEM_PROMPT = (
    "You are an expert LinkedIn content writer specializing in educational, "
    "value-first posts. Your job is to write posts that TEACH the reader "
    "something concrete about the given topic — not generic hype or talk. "
    "If the topic requires up-to-date information, statistics, current "
    "trends, or specific resources (courses, tools, docs, books), use the "
    "web search tool to gather fresh, accurate details before writing. "
    "If you have already received feedback on a previous draft, carefully "
    "address every point in the new draft.\n\n"
    "Rules for good LinkedIn posts:\n"
    "- Strong hook in the first line (a specific problem, curiosity, or claim — not vague phrases like 'new era' or 'revolutionary')\n"
    "- Break the topic into 3-5 concrete sub-points/concepts the reader must know\n"
    "- For each point, give 1 short practical line (why it matters or how to start)\n"
    "- Mention 2-3 specific resources (tool/course/doc names) if relevant\n"
    "- Easy to skim — short paragraphs or bullet-style lines\n"
    "- Around 150-250 words\n"
    "- Ends with a question or call-to-action to invite engagement\n"
    "- Do not use hashtags\n"
    "Avoid empty motivational language. Write like a mentor giving a real roadmap, not a hype post."
)

writer_agent = create_react_agent(
    model=writer_llm,
    tools=[search_tool],
    prompt=WRITER_SYSTEM_PROMPT,
)


def writer_node(state: State) -> dict:
    """Writes (or rewrites) the LinkedIn post. Agent decides itself if it needs to search."""
    attempt = state.get("attempt", 0) + 1
    topic = state["topic"]
    previous_feedback = state.get("review_feedback", "")

    if attempt == 1:
        user_message = (
            f"Write a LinkedIn post on this topic: {topic}. "
            f"If you need current info, search the web first."
        )
    else:
        user_message = (
            f"Your previous draft on '{topic}' was rejected.\n"
            f"Here is the reviewer's feedback:\n\n{previous_feedback}\n\n"
            f"Write a new, improved draft that fixes every issue mentioned. "
            f"Do not repeat the same mistake."
        )

    result = writer_agent.invoke({"messages": [("human", user_message)]})
    draft = result["messages"][-1].content

    return {
        "draft": draft,
        "attempt": attempt,
    }


def human_review_node(state: State) -> dict:
    """Pauses the graph and waits for the human to approve or give feedback."""
    human_response = interrupt({
        "draft": state["draft"],
        "attempt": state["attempt"],
        "instruction": "Type 'approved' to accept, or type your feedback to request a rewrite.",
    })

    response = human_response.strip()

    if response.lower() in ["approved", "approve", "accept", "accepted", "yes", "ok", "good"]:
        return {
            "is_approved": True,
            "review_feedback": "Approved by human",
        }
    # BUG FIX: rejected drafts must NOT be marked approved
    return {
        "is_approved": False,
        "review_feedback": response,
    }


def should_stop_looping(state: State):
    if state["is_approved"]:
        print("post has been approved\n")
        return END
    if state["attempt"] >= 5:
        print("reached max attempts")
        return END
    return "writer"


# ---------- GRAPH ----------
graph = StateGraph(State)

graph.add_node("writer", writer_node)
graph.add_node("human_review", human_review_node)

graph.add_edge(START, "writer")
graph.add_edge("writer", "human_review")
graph.add_conditional_edges("human_review", should_stop_looping)

checkpointer = MemorySaver()
app = graph.compile(checkpointer=checkpointer)

# ---------- RUN (CLI test) ----------
print("=" * 55)
print("Welcome to the LinkedIn Post Generator (Human-in-the-loop)")
print("=" * 55)
print("\nThis tool will draft a LinkedIn post, show it to you,")
print("and rewrite it based on your feedback until you approve.")
print("=" * 55)

topic = input("\nWhat topic do you want a LinkedIn post about?\n> ").strip()

if not topic:
    print("\nNo topic given. Exiting.")
else:
    print("\nStarting generation...\n")

    # BUG FIX: was "thread-id" (hyphen) — LangGraph requires exactly "thread_id"
    config = {"configurable": {"thread_id": "linkedin_session_id"}}

    initial_state = {
        "topic": topic,
        "draft": "",
        "review_feedback": "",
        "is_approved": False,
        "attempt": 0,
    }

    result = app.invoke(initial_state, config=config)

    # BUG FIX: was "_interrupt_" — the real key is "__interrupt__" (double underscore)
    while "__interrupt__" in result:
        interrupt_data = result["__interrupt__"][0].value

        print("\n" + "=" * 55)
        # BUG FIX: was printing the whole dict instead of the attempt number
        print(f"DRAFT FOR YOUR REVIEW (ATTEMPT {interrupt_data['attempt']})")
        print("=" * 55)
        print(interrupt_data["draft"])
        print("=" * 55)
        print(f"\n{interrupt_data['instruction']}")

        human_input = input("\nYour response: ").strip()

        result = app.invoke(Command(resume=human_input), config=config)

    print("=" * 55)
    print("FINAL LINKEDIN POST")
    print("=" * 55)
    print(result["draft"])
    print("=" * 55)
    print(f"Total attempts: {result['attempt']}")
    print(f"Approved: {result['is_approved']}")



# State — ek shared dict jo poore graph mein pass hota rehta hai: topic, draft, review_feedback, is_approved, attempt
# writer_agent — create_react_agent se bana hua self-contained agent jiske paas Tavily search tool hai; ye khud decide karta hai ki search karna hai ya seedha likhna hai
# writer_node — agent ko call karta hai. Pehli baar sirf topic deta hai, dusri baar (rejection ke baad) purana feedback bhi saath mein deta hai taaki agent usko fix kare
# human_review_node — interrupt() call karte hi graph pause ho jata hai aur draft + attempt number ko bahar bhej deta hai. Jab tak tu response nahi deta, aage nahi badhta
# should_stop_looping — decide karta hai: approve ho gaya → END, 5 attempts ho gaye → END, warna wapas "writer" node pe bhej do (loop)
# Graph wiring: START → writer → human_review → (loop back to writer YA end) — seedha linear flow, koi extra tool node nahi chahiye kyunki agent khud internally search handle karta hai
# checkpointer (MemorySaver) — graph ka pause/resume state yaad rakhta hai thread_id ke against, isi wajah se interrupt() ke baad Command(resume=...) se wahi se continue ho pata hai
# CLI loop (bottom wala part) — app.invoke() pehli baar chalata hai, agar result mein "__interrupt__" mile to draft dikhao, user se input lo, Command(resume=human_input) se wapas resume karo — jab tak "__interrupt__" na mile (matlab graph END tak pahunch gaya)