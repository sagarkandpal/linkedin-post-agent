import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'

function Register() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(false)

  const navigate = useNavigate()

  const handleSubmit = async () => {
    setError('')
    setSuccess('')

    if (!email.trim() || !password.trim()) {
      setError('Please enter your email and password.')
      return
    }

    if (password.length < 6) {
      setError('Password should be at least 6 characters.')
      return
    }

    setLoading(true)

    try {
      const res = await fetch('http://localhost:8000/api/signup', {
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
        setError(data.detail || 'Signup failed')
        return
      }

      setSuccess('Account created! Redirecting to login...')

      setTimeout(() => {
        navigate('/login')
      }, 1200)

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

        <div className="brand-icon">
          ✦
        </div>

        <span>
          Post<span>AI</span>
        </span>

      </div>


      {/* Register Card */}
      <main className="auth-card register-card">

        <div className="auth-header">

          <div className="auth-icon register-icon">
            +
          </div>

          <span className="auth-eyebrow">
            GET STARTED
          </span>

          <h1>
            Create your account.
          </h1>

          <p>
            Start turning your ideas into posts people want to read.
          </p>

        </div>


        <div className="auth-form">

          {/* Email */}
          <div className="form-field">

            <label htmlFor="register-email">
              Email address
            </label>

            <div className="input-wrapper">

              <span className="input-icon">
                @
              </span>

              <input
                id="register-email"
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

              <label htmlFor="register-password">
                Password
              </label>

              <span>
                Minimum 6 characters
              </span>

            </div>

            <div className="input-wrapper">

              <span className="input-icon">
                •••
              </span>

              <input
                id="register-password"
                type="password"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value)
                  setError('')
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleSubmit()
                }}
                placeholder="Create a password"
                autoComplete="new-password"
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


          {/* Success */}
          {success && (
            <div className="auth-success">

              <div className="success-small-icon">
                ✓
              </div>

              <span>
                {success}
              </span>

            </div>
          )}


          {/* Register */}
          <button
            className="auth-submit"
            onClick={handleSubmit}
            disabled={loading || !!success}
          >

            {loading ? (
              <>
                <span className="button-spinner"></span>
                Creating account...
              </>
            ) : (
              <>
                Create account
                <span>→</span>
              </>
            )}

          </button>

        </div>


        {/* Login link */}
        <div className="auth-switch">

          <span>
            Already have an account?
          </span>

          <Link to="/login">
            Sign in →
          </Link>

        </div>


        {/* Divider */}
        <div className="auth-divider">

          <span></span>

          <small>
            POST BETTER. EVERY DAY.
          </small>

          <span></span>

        </div>

      </main>


      <p className="auth-footer">
        AI-powered writing for your professional presence.
      </p>

    </div>
  )
}

export default Register