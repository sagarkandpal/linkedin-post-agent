import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import '../App.css'

const BAD_WORDS = ['fuck', 'chutiya', 'madarchod', 'bhosdi', 'randi', 'gandu']

function Dashboard() {
  const navigate = useNavigate()

  const [topic, setTopic] = useState('')
  const [status, setStatus] = useState('')
  const [draft, setDraft] = useState('')
  const [threadId, setThreadId] = useState('')
  const [feedback, setFeedback] = useState('')
  const [finalPost, setFinalPost] = useState('')
  const [useEmojis, setUseEmojis] = useState(false)
  const [inputError, setInputError] = useState('')
  const [limitReached, setLimitReached] = useState(false)
  const [lastFeedbackUsed, setLastFeedbackUsed] = useState('')
  const [posts, setPosts] = useState([])
  const [showPosts, setShowPosts] = useState(false)
  const [expandedId, setExpandedId] = useState(null)

  const isValidTopic = (text) => {
    const trimmed = text.trim()

    if (trimmed.length < 3)
      return 'Topic thoda lamba likho (kam se kam 3 characters).'

    const validPattern = /^[a-zA-Z0-9\s.,!?'-]+$/

    if (!validPattern.test(trimmed))
      return 'Sirf normal letters/numbers use karo, special symbols nahi.'

    const lower = trimmed.toLowerCase()

    for (const word of BAD_WORDS) {
      if (lower.includes(word))
        return 'Ye topic allowed nahi hai, kuch aur likho.'
    }

    return ''
  }

  const streamEvents = async (res) => {
    if (res.status === 429) {
      setStatus('')
      setLimitReached(true)
      return
    }

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()

      if (done) break

      buffer += decoder.decode(value, { stream: true })

      const parts = buffer.split('\n\n')
      buffer = parts.pop()

      for (const part of parts) {
        if (!part.startsWith('data: ')) continue

        const json = JSON.parse(part.replace('data: ', ''))

        if (json.type === 'status') {
          setStatus(json.message)
        } else if (json.type === 'awaiting_review') {
          setStatus('')
          setDraft(json.draft)
          setThreadId(json.thread_id)
        } else if (json.type === 'done') {
          setStatus('')
          setDraft('')
          setFinalPost(json.draft)
        }
      }
    }
  }

  const handleGenerate = async () => {
    const errorMsg = isValidTopic(topic)

    if (errorMsg) {
      setInputError(errorMsg)
      return
    }

    setInputError('')
    setLimitReached(false)
    setDraft('')
    setFinalPost('')
    setLastFeedbackUsed('')
    setStatus('Generating your post...')

    const res = await fetch('http://localhost:8000/api/generate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer ' + localStorage.getItem('token'),
      },
      body: JSON.stringify({
        topic,
        use_emojis: useEmojis,
      }),
    })

    await streamEvents(res)
  }

  const handleApprove = async () => {
    setStatus('Saving your post...')

    const res = await fetch('http://localhost:8000/api/review', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer ' + localStorage.getItem('token'),
      },
      body: JSON.stringify({
        thread_id: threadId,
        response: 'approved',
      }),
    })

    await streamEvents(res)
  }

  const handleReject = async () => {
    if (!feedback.trim()) return

    setLastFeedbackUsed(feedback)
    setStatus('Rewriting based on your feedback...')

    const previousDraft = draft

    const res = await fetch('http://localhost:8000/api/review', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer ' + localStorage.getItem('token'),
      },
      body: JSON.stringify({
        thread_id: threadId,
        response: feedback,
      }),
    })

    setFeedback('')

    if (res.status === 429) {
      setStatus('')
      setLimitReached(true)
      setDraft(previousDraft)
      return
    }

    setDraft('')
    await streamEvents(res)
  }

  const handleViewPosts = async () => {
    if (showPosts) {
      setShowPosts(false)
      return
    }

    const res = await fetch('http://localhost:8000/api/posts', {
      headers: {
        Authorization: 'Bearer ' + localStorage.getItem('token'),
      },
    })

    const data = await res.json()
    setPosts(data)
    setShowPosts(true)
  }

  const toggleExpand = (id) => {
    setExpandedId(expandedId === id ? null : id)
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    navigate('/login')
  }

  const copyPost = async () => {
    await navigator.clipboard.writeText(finalPost)
  }

  return (
    <div className="dashboard-page">

      {/* NAVBAR */}
      <header className="dashboard-nav">
        <div className="brand">
          <div className="brand-icon">✦</div>
          <span>Post<span>AI</span></span>
        </div>

        <div className="nav-right">
          <div className="quota-badge">
            <span className="quota-dot"></span>
            5 Generate · 5 Reviews today
          </div>

          <button className="nav-posts-btn" onClick={handleViewPosts}>
            <span>▤</span>
            {showPosts ? 'Hide Posts' : 'My Posts'}
          </button>

          <button className="logout-btn" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </header>


      <main className="dashboard-container">

        {/* HERO */}
        <section className="hero-section">
          <div className="hero-badge">
            <span>✦</span>
            AI-POWERED LINKEDIN WRITER
          </div>

          <h1>
            Turn your ideas into
            <span> powerful posts.</span>
          </h1>

          <p>
            Give us a topic. Our AI will turn it into a professional,
            engaging LinkedIn post in seconds.
          </p>
        </section>


        {/* GENERATOR */}
        <section className="generator-card">

          <div className="section-label">
            <span className="label-number">01</span>
            WHAT DO YOU WANT TO TALK ABOUT?
          </div>

          <div className="generator-input-wrap">

            <input
              className="topic-input"
              type="text"
              value={topic}
              onChange={(e) => {
                setTopic(e.target.value)
                setInputError('')
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleGenerate()
              }}
              placeholder="e.g. What I learned building my first AI project..."
            />

            <button
              className="generate-btn"
              onClick={handleGenerate}
            >
              <span>Generate Post</span>
              <span className="arrow">→</span>
            </button>

          </div>

          <div className="generator-bottom">

            <label className="emoji-toggle">
              <input
                type="checkbox"
                checked={useEmojis}
                onChange={(e) => setUseEmojis(e.target.checked)}
              />

              <span className="toggle-slider"></span>

              <span className="emoji-text">
                <strong>Use emojis</strong>
                <small>Add a little personality to your post</small>
              </span>
            </label>

            <span className="enter-hint">
              Press <kbd>Enter</kbd> to generate
            </span>

          </div>

        </section>


        {/* ERROR */}
        {inputError && (
          <div className="alert alert-error">
            <span>!</span>
            {inputError}
          </div>
        )}

        {/* LIMIT */}
        {limitReached && (
          <div className="alert alert-warning">
            <span>⚠</span>
            <div>
              <strong>Daily quota reached</strong>
              <p>You've used all your attempts for today. Try again tomorrow.</p>
            </div>
          </div>
        )}

        {/* LOADING */}
        {status && (
          <div className="generating-state">
            <div className="loading-spinner"></div>
            <div>
              <strong>{status}</strong>
              <span>AI is working on your post...</span>
            </div>
          </div>
        )}


        {/* SAVED POSTS */}
        {showPosts && (
          <section className="saved-posts-section">

            <div className="section-heading">
              <div>
                <span className="mini-label">YOUR CONTENT</span>
                <h2>Saved Posts</h2>
              </div>

              <span className="post-count">
                {posts.length} {posts.length === 1 ? 'post' : 'posts'}
              </span>
            </div>

            {posts.length === 0 ? (
              <div className="empty-posts">
                <div className="empty-icon">✦</div>
                <h3>No posts yet</h3>
                <p>Generate your first LinkedIn post and it'll appear here.</p>
              </div>
            ) : (
              <div className="posts-list">

                {posts.map((post) => (
                  <div
                    className={`saved-post ${
                      expandedId === post._id ? 'expanded' : ''
                    }`}
                    key={post._id}
                  >

                    <div
                      className="saved-post-header"
                      onClick={() => toggleExpand(post._id)}
                    >
                      <div className="saved-post-info">
                        <span className="saved-post-icon">✦</span>
                        <strong>{post.topic}</strong>
                      </div>

                      <span className="expand-icon">
                        {expandedId === post._id ? '−' : '+'}
                      </span>
                    </div>

                    {expandedId === post._id && (
                      <div className="saved-post-content">
                        <p>{post.draft}</p>
                      </div>
                    )}

                  </div>
                ))}

              </div>
            )}

          </section>
        )}


        {/* DRAFT */}
        {draft && (
          <section className="post-editor-section">

            <div className="section-heading">
              <div>
                <span className="mini-label">AI GENERATED</span>
                <h2>Review your draft</h2>
              </div>

              <span className="draft-badge">
                <span></span>
                Draft
              </span>
            </div>


            <div className="draft-card">

              <div className="draft-card-top">
                <div className="ai-avatar">✦</div>

                <div>
                  <strong>PostAI</strong>
                  <span>AI Generated Draft</span>
                </div>
              </div>


              <div className="draft-content">
                <p>{draft}</p>
              </div>


              {lastFeedbackUsed && (
                <div className="feedback-used">
                  <span>↳</span>
                  <div>
                    <strong>Last feedback</strong>
                    <p>"{lastFeedbackUsed}"</p>
                  </div>
                </div>
              )}


              <div className="draft-actions">

                <button
                  className="approve-btn"
                  onClick={handleApprove}
                >
                  <span>✓</span>
                  Approve & Save
                </button>

              </div>


              <div className="rewrite-area">

                <div className="rewrite-divider">
                  <span>OR REWRITE WITH FEEDBACK</span>
                </div>

                <div className="feedback-row">

                  <input
                    className="feedback-input"
                    type="text"
                    value={feedback}
                    onChange={(e) => setFeedback(e.target.value)}
                    placeholder="Make it more casual, add a stronger hook..."
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleReject()
                    }}
                  />

                  <button
                    className="rewrite-btn"
                    onClick={handleReject}
                    disabled={!feedback.trim()}
                  >
                    Rewrite
                    <span>↗</span>
                  </button>

                </div>

              </div>

            </div>

          </section>
        )}


        {/* FINAL POST */}
        {finalPost && (
          <section className="post-editor-section final-section">

            <div className="section-heading">
              <div>
                <span className="mini-label success-label">COMPLETE</span>
                <h2>Your post is ready 🎉</h2>
              </div>

              <span className="approved-badge">
                ✓ Approved
              </span>
            </div>


            <div className="final-card">

              <div className="final-top">
                <div className="success-icon">✓</div>

                <div>
                  <strong>Post approved successfully</strong>
                  <span>Your LinkedIn post is ready to publish.</span>
                </div>
              </div>

              <div className="final-content">
                <p>{finalPost}</p>
              </div>

              <button
                className="copy-btn"
                onClick={copyPost}
              >
                <span>▣</span>
                Copy Post
              </button>

            </div>

          </section>
        )}

        {/* FOOTER */}
        <footer className="dashboard-footer">
          <span>✦ PostAI</span>
          <span>Built to help you post better.</span>
        </footer>

      </main>
    </div>
  )
}

export default Dashboard