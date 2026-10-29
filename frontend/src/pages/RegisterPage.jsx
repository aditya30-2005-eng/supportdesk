import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { authApi } from '../api/endpoints'
import { useAuth } from '../auth/useAuth'
import { errorMessage, fieldErrors } from '../utils/format'

const EMPTY_FORM = {
  username: '',
  email: '',
  first_name: '',
  last_name: '',
  password: '',
  confirm: '',
}

function validate(form) {
  const errors = {}
  if (!form.username.trim()) errors.username = 'Username is required.'
  if (!/^\S+@\S+\.\S+$/.test(form.email)) errors.email = 'Enter a valid email address.'
  if (form.password.length < 8) errors.password = 'Password must be at least 8 characters.'
  if (form.password !== form.confirm) errors.confirm = 'Passwords do not match.'
  return errors
}

export default function RegisterPage() {
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState(EMPTY_FORM)
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (user) return <Navigate to="/tickets" replace />

  function update(event) {
    setForm({ ...form, [event.target.name]: event.target.value })
  }

  async function handleSubmit(event) {
    event.preventDefault()
    const clientErrors = validate(form)
    setErrors(clientErrors)
    setFormError('')
    if (Object.keys(clientErrors).length) return

    setSubmitting(true)
    try {
      const { confirm: _confirm, ...payload } = form
      await authApi.register({ ...payload, username: payload.username.trim() })
      await login(payload.username.trim(), payload.password)
      navigate('/tickets', { replace: true })
    } catch (err) {
      setErrors(fieldErrors(err))
      setFormError(errorMessage(err, 'Please fix the errors below.'))
      setSubmitting(false)
    }
  }

  function field(name, text, props = {}) {
    return (
      <label className="field">
        <span>{text}</span>
        <input
          name={name}
          value={form[name]}
          onChange={update}
          aria-invalid={Boolean(errors[name])}
          {...props}
        />
        {errors[name] && <small className="field-error">{errors[name]}</small>}
      </label>
    )
  }

  return (
    <div className="auth-page">
      <form className="card auth-card" onSubmit={handleSubmit} noValidate>
        <h1>Create an account</h1>
        <p className="muted">Sign up as a customer to raise support tickets.</p>
        {formError && <div className="alert alert-error">{formError}</div>}
        <div className="row">
          {field('first_name', 'First name', { autoComplete: 'given-name' })}
          {field('last_name', 'Last name', { autoComplete: 'family-name' })}
        </div>
        {field('username', 'Username', { autoComplete: 'username' })}
        {field('email', 'Email', { type: 'email', autoComplete: 'email' })}
        {field('password', 'Password', { type: 'password', autoComplete: 'new-password' })}
        {field('confirm', 'Confirm password', { type: 'password', autoComplete: 'new-password' })}
        <button className="btn btn-primary btn-block" disabled={submitting}>
          {submitting ? 'Creating account...' : 'Sign up'}
        </button>
        <p className="muted center">
          Already have an account? <Link to="/login">Log in</Link>
        </p>
      </form>
    </div>
  )
}
