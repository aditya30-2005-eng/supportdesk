import { useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'
import { errorMessage } from '../utils/format'

export default function LoginPage() {
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [form, setForm] = useState({ username: '', password: '' })
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (user) return <Navigate to="/tickets" replace />

  function update(event) {
    setForm({ ...form, [event.target.name]: event.target.value })
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      await login(form.username.trim(), form.password)
      navigate(location.state?.from?.pathname || '/tickets', { replace: true })
    } catch (err) {
      setError(
        err.response?.status === 401
          ? 'Wrong username or password.'
          : errorMessage(err, 'Could not log in.'),
      )
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="auth-page">
      <form className="card auth-card" onSubmit={handleSubmit} noValidate>
        <h1>SupportDesk</h1>
        <p className="muted">Log in to raise and track support tickets.</p>
        {error && <div className="alert alert-error">{error}</div>}
        <label className="field">
          <span>Username</span>
          <input
            name="username"
            value={form.username}
            onChange={update}
            autoComplete="username"
            required
          />
        </label>
        <label className="field">
          <span>Password</span>
          <input
            name="password"
            type="password"
            value={form.password}
            onChange={update}
            autoComplete="current-password"
            required
          />
        </label>
        <button
          className="btn btn-primary btn-block"
          disabled={submitting || !form.username || !form.password}
        >
          {submitting ? 'Logging in...' : 'Log in'}
        </button>
        <p className="muted center">
          New here? <Link to="/register">Create an account</Link>
        </p>
      </form>
    </div>
  )
}
