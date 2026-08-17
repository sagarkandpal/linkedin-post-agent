import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const navigate = useNavigate()

  const handleSubmit = async () => {
    setError('')

    if (!email.trim() || !password.trim()) {
      setError('Please enter your email and password.')
      return
    }

    setLoading(true)

    try {
      const res = await fetch('http://localhost:8000/api/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email,
          password,
        }),
      })

      if (!res.ok) {
        const data = await res.json()
        setError(data.detail || 'Login failed')
        setLoading(false)
        return
      }

      const data = await res.json()

      localStorage.setItem('token', data.access_token)

      navigate('/dashboard')
    } catch (err) {
      setError('Unable to connect to the server. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">

      {/* Background decoration */}
      <div className="auth-glow auth-glow-one"></div>
      <div className="auth-glow auth-glow-two"></div>

      {/* Brand */}
      <div className="auth-brand">
        <div className="brand-icon">✦</div>

        <span>
          Post<span>AI</span>
        </span>
      </div>


      {/* Login Card */}
      <main className="auth-card">

        <div className="auth-header">

          <div className="auth-icon">
            ✦
          </div>

          <span className="auth-eyebrow">
            WELCOME BACK
          </span>

          <h1>
            Welcome back.
          </h1>

          <p>
            Turn your ideas into posts people want to read.
          </p>

        </div>


        <div className="auth-form">

          {/* Email */}
          <div className="form-field">

            <label htmlFor="email">
              Email address
            </label>

            <div className="input-wrapper">

              <span className="input-icon">
                @
              </span>

              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value)
                  setError('')
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleSubmit()
                }}
                placeholder="you@example.com"
                autoComplete="email"
              />

            </div>

          </div>


          {/* Password */}
          <div className="form-field">

            <div className="password-label">
              <label htmlFor="password">
                Password
              </label>

              <span>
                Keep it secure
              </span>
            </div>

            <div className="input-wrapper">

              <span className="input-icon">
                •••
              </span>

              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value)
                  setError('')
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleSubmit()
                }}
                placeholder="Enter your password"
                autoComplete="current-password"
              />

            </div>

          </div>


          {/* Error */}
          {error && (
            <div className="auth-error">

              <div className="error-icon">
                !
              </div>

              <span>
                {error}
              </span>

            </div>
          )}


          {/* Login */}
          <button
            className="auth-submit"
            onClick={handleSubmit}
            disabled={loading}
          >

            {loading ? (
              <>
                <span className="button-spinner"></span>
                Signing you in...
              </>
            ) : (
              <>
                Sign in
                <span>→</span>
              </>
            )}

          </button>

        </div>


        {/* Bottom info */}
        <div className="auth-divider">
          <span></span>
          <small>POST BETTER. EVERY DAY.</small>
          <span></span>
        </div>

      </main>


      <p className="auth-footer">
        AI-powered writing for your professional presence.
      </p>

    </div>
  )
}

export default Login