from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import create_react_agent
from langchain_groq import ChatGroq
from langchain_tavily import TavilySearch
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt

from app.config import GROQ_API_KEY, TAVILY_API_KEY  # env vars already loaded by config.py

# ---------- TOOLS ----------
search_tool = TavilySearch(max_results=3)

# ---------- LLMs ----------
writer_llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.7)

# ---------- STATE ----------
# Ye dict poore graph me pass hoti rehti hai, har node isko read/update karta hai.
class State(TypedDict):
    topic: str
    draft: str
    review_feedback: str
    is_approved: bool
    attempt: int
    use_emojis: bool


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

# create_react_agent apna khud ka tool-calling loop internally handle karta hai
# (LLM decide karta hai search karni hai ya nahi, khud call karta hai, khud result use karta hai)
writer_agent = create_react_agent(
    model=writer_llm,
    tools=[search_tool],
    prompt=WRITER_SYSTEM_PROMPT,
)


# ---------- NODES ----------
def writer_node(state: State) -> dict:
    """Writes (or rewrites) the LinkedIn post. Agent decides itself if it needs to search."""
    attempt = state.get("attempt", 0) + 1
    topic = state["topic"]
    previous_feedback = state.get("review_feedback", "")

    if attempt == 1:
        # Pehla attempt — sirf topic dena hai
        user_message = (
            f"Write a LinkedIn post on this topic: {topic}. "
            f"If you need current info, search the web first."
        )
    else:
        # Rejection ke baad — purana feedback bhi saath bhejna hai taaki fix ho
        user_message = (
            f"Your previous draft on '{topic}' was rejected.\n"
            f"Here is the reviewer's feedback:\n\n{previous_feedback}\n\n"
            f"Write a new, improved draft that fixes every issue mentioned. "
            f"Do not repeat the same mistake."
        )

    # emoji toggle — agar user ne on kiya hai to instruction add karo
    if state.get("use_emojis"):
        user_message += (
            "\n\nAdd relevant emojis naturally throughout the post "
            "(at line starts or after key phrases) to make it visually engaging. "
            "Do not overdo it — 1 emoji per line/point max."
        )

    result = writer_agent.invoke({"messages": [("human", user_message)]})
    draft = result["messages"][-1].content  # agent ka final text answer

    return {
        "draft": draft,
        "attempt": attempt,
    }


def human_review_node(state: State) -> dict:
    """Graph ko yahan PAUSE kar deta hai (interrupt) — jab tak FastAPI se
    /api/review call na aaye, aage nahi badhega. Ye hi human-in-the-loop hai."""
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
    return {
        "is_approved": False,
        "review_feedback": response,
    }


# ---------- ROUTER ----------
def should_stop_looping(state: State):
    """Reviewer ke baad decide karta hai: END karna hai ya wapas writer pe bhejna hai"""
    if state["is_approved"]:
        return END
    if state["attempt"] >= 5:  # safety limit — infinite loop na ho
        return END
    return "writer"


# ---------- GRAPH ----------
# Flow: START -> writer -> human_review -> (loop back to writer YA END)
graph = StateGraph(State)

graph.add_node("writer", writer_node)
graph.add_node("human_review", human_review_node)

graph.add_edge(START, "writer")
graph.add_edge("writer", "human_review")
graph.add_conditional_edges("human_review", should_stop_looping)

# checkpointer graph ki state ko thread_id ke against yaad rakhta hai —
# isi wajah se interrupt() ke baad Command(resume=...) se wahi se continue ho pata hai.
# NOTE: MemorySaver = RAM only, server restart pe khatam ho jayega.
checkpointer = MemorySaver()
compiled_graph = graph.compile(checkpointer=checkpointer)

# main.py isko import karega: from app.agent import compiled_graph