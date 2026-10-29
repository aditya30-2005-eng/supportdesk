import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { categoryApi, ticketApi } from '../api/endpoints'
import { ErrorMessage, Loading } from '../components/StateMessage'
import { PRIORITY_OPTIONS, errorMessage, fieldErrors } from '../utils/format'
import { useFetch } from '../utils/useFetch'

const EMPTY_FORM = { title: '', description: '', category: '', priority: 'medium' }

function validate(form) {
  const errors = {}
  const title = form.title.trim()
  if (title.length < 5) errors.title = 'Title must be at least 5 characters.'
  if (title.length > 200) errors.title = 'Title can be at most 200 characters.'
  if (form.description.trim().length < 10) {
    errors.description = 'Please describe the problem in at least 10 characters.'
  }
  if (!form.category) errors.category = 'Choose a category.'
  return errors
}

export default function CreateTicketPage() {
  const navigate = useNavigate()
  const { data: categories, error: loadError, reload } = useFetch(categoryApi.list)
  const [form, setForm] = useState(EMPTY_FORM)
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  function update(event) {
    const { name, value } = event.target
    setForm({ ...form, [name]: value })
    if (errors[name]) setErrors({ ...errors, [name]: undefined })
  }

  async function handleSubmit(event) {
    event.preventDefault()
    const clientErrors = validate(form)
    setErrors(clientErrors)
    setFormError('')
    if (Object.keys(clientErrors).length) return

    setSubmitting(true)
    try {
      const ticket = await ticketApi.create({
        ...form,
        title: form.title.trim(),
        description: form.description.trim(),
        category: Number(form.category),
      })
      navigate(`/tickets/${ticket.id}`, { replace: true })
    } catch (err) {
      setErrors(fieldErrors(err))
      setFormError(errorMessage(err, 'Please fix the errors below.'))
      setSubmitting(false)
    }
  }

  if (loadError) return <ErrorMessage message={errorMessage(loadError)} onRetry={reload} />
  if (!categories) return <Loading />

  return (
    <section className="narrow">
      <Link to="/tickets" className="back-link">
        &larr; Back to tickets
      </Link>
      <h1>Raise a new ticket</h1>
      <form className="card form" onSubmit={handleSubmit} noValidate>
        {formError && <div className="alert alert-error">{formError}</div>}
        <label className="field">
          <span>Title</span>
          <input
            name="title"
            value={form.title}
            onChange={update}
            maxLength={200}
            placeholder="Short summary of the problem"
            aria-invalid={Boolean(errors.title)}
          />
          {errors.title && <small className="field-error">{errors.title}</small>}
        </label>
        <label className="field">
          <span>Description</span>
          <textarea
            name="description"
            rows={6}
            value={form.description}
            onChange={update}
            placeholder="What happened? What did you expect to happen?"
            aria-invalid={Boolean(errors.description)}
          />
          {errors.description && <small className="field-error">{errors.description}</small>}
        </label>
        <div className="row">
          <label className="field">
            <span>Category</span>
            <select
              name="category"
              value={form.category}
              onChange={update}
              aria-invalid={Boolean(errors.category)}
            >
              <option value="">Choose a category</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
            {errors.category && <small className="field-error">{errors.category}</small>}
          </label>
          <label className="field">
            <span>Priority</span>
            <select name="priority" value={form.priority} onChange={update}>
              {PRIORITY_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="form-actions">
          <Link to="/tickets" className="btn btn-secondary">
            Cancel
          </Link>
          <button className="btn btn-primary" disabled={submitting}>
            {submitting ? 'Submitting...' : 'Submit ticket'}
          </button>
        </div>
      </form>
    </section>
  )
}
