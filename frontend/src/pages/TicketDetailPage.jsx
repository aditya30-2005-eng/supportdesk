import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ticketApi, userApi } from '../api/endpoints'
import { useAuth } from '../auth/useAuth'
import Badge from '../components/Badge'
import { ErrorMessage, Loading } from '../components/StateMessage'
import { STATUS_OPTIONS, errorMessage, formatDate } from '../utils/format'
import { useFetch } from '../utils/useFetch'

export default function TicketDetailPage() {
  const { id } = useParams()
  const { user } = useAuth()
  const fetchTicket = useCallback(() => ticketApi.get(id), [id])
  const { data: ticket, error, reload, setData: setTicket } = useFetch(fetchTicket)

  if (error) {
    const message =
      error.response?.status === 404
        ? 'This ticket does not exist or you do not have access to it.'
        : errorMessage(error)
    return <ErrorMessage message={message} onRetry={reload} />
  }
  if (!ticket) return <Loading text="Loading ticket..." />

  const canChangeStatus = user.role === 'agent' || user.role === 'admin'

  return (
    <section>
      <Link to="/tickets" className="back-link">
        &larr; Back to tickets
      </Link>
      <div className="page-header">
        <div>
          <h1>
            <span className="muted">#{ticket.id}</span> {ticket.title}
          </h1>
          <div className="badges">
            <Badge kind="status" value={ticket.status} />
            <Badge kind="priority" value={ticket.priority} />
            <span className="muted">{ticket.category_name}</span>
          </div>
        </div>
      </div>

      <div className="detail-grid">
        <div className="detail-main">
          <article className="card">
            <h2>Description</h2>
            <p className="description">{ticket.description}</p>
          </article>
          <Comments ticket={ticket} onAdded={reload} />
        </div>

        <aside className="detail-side">
          <div className="card">
            <h2>Details</h2>
            <dl className="meta">
              <dt>Raised by</dt>
              <dd>{ticket.created_by.full_name}</dd>
              <dt>Assigned to</dt>
              <dd>{ticket.assigned_to?.full_name || 'Not assigned yet'}</dd>
              <dt>Created</dt>
              <dd>{formatDate(ticket.created_at)}</dd>
              <dt>Last updated</dt>
              <dd>{formatDate(ticket.updated_at)}</dd>
              {ticket.resolved_at && (
                <>
                  <dt>Resolved</dt>
                  <dd>{formatDate(ticket.resolved_at)}</dd>
                </>
              )}
            </dl>
          </div>
          {canChangeStatus && <StatusForm ticket={ticket} onSaved={setTicket} />}
          {user.role === 'admin' && <AssignForm ticket={ticket} onSaved={setTicket} />}
          {user.role === 'admin' && <DeleteTicket ticket={ticket} />}
        </aside>
      </div>
    </section>
  )
}

function StatusForm({ ticket, onSaved }) {
  const [status, setStatus] = useState(ticket.status)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState(null)

  async function handleSubmit(event) {
    event.preventDefault()
    setSaving(true)
    setMessage(null)
    try {
      const updated = await ticketApi.update(ticket.id, { status })
      onSaved((current) => ({ ...current, ...updated }))
      setMessage({ type: 'success', text: 'Status updated. The customer will get an email.' })
    } catch (err) {
      setMessage({ type: 'error', text: errorMessage(err) })
    } finally {
      setSaving(false)
    }
  }

  return (
    <form className="card" onSubmit={handleSubmit}>
      <h2>Change status</h2>
      {message && <div className={`alert alert-${message.type}`}>{message.text}</div>}
      <select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status">
        {STATUS_OPTIONS.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      <button className="btn btn-primary btn-block" disabled={saving || status === ticket.status}>
        {saving ? 'Saving...' : 'Update status'}
      </button>
    </form>
  )
}

function AssignForm({ ticket, onSaved }) {
  const [agents, setAgents] = useState(null)
  const [agentId, setAgentId] = useState(
    ticket.assigned_to?.id ? String(ticket.assigned_to.id) : '',
  )
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState(null)

  useEffect(() => {
    userApi
      .list({ role: 'agent', is_active: true, page_size: 100 })
      .then((data) => setAgents(data.results))
      .catch((err) => setMessage({ type: 'error', text: errorMessage(err) }))
  }, [])

  async function handleSubmit(event) {
    event.preventDefault()
    setSaving(true)
    setMessage(null)
    try {
      const updated = await ticketApi.assign(ticket.id, Number(agentId))
      onSaved((current) => ({ ...current, ...updated }))
      setMessage({ type: 'success', text: 'Ticket assigned. The agent will get an email.' })
    } catch (err) {
      setMessage({ type: 'error', text: errorMessage(err) })
    } finally {
      setSaving(false)
    }
  }

  return (
    <form className="card" onSubmit={handleSubmit}>
      <h2>Assign agent</h2>
      {message && <div className={`alert alert-${message.type}`}>{message.text}</div>}
      <select
        value={agentId}
        onChange={(e) => setAgentId(e.target.value)}
        disabled={!agents}
        aria-label="Agent"
      >
        <option value="">{agents ? 'Choose an agent' : 'Loading agents...'}</option>
        {agents?.map((agent) => (
          <option key={agent.id} value={agent.id}>
            {agent.full_name}
          </option>
        ))}
      </select>
      <button
        className="btn btn-primary btn-block"
        disabled={saving || !agentId || Number(agentId) === ticket.assigned_to?.id}
      >
        {saving ? 'Assigning...' : 'Assign'}
      </button>
    </form>
  )
}

function DeleteTicket({ ticket }) {
  const navigate = useNavigate()
  const [error, setError] = useState('')

  async function handleDelete() {
    if (!window.confirm(`Delete ticket #${ticket.id}? This cannot be undone.`)) return
    try {
      await ticketApi.remove(ticket.id)
      navigate('/tickets', { replace: true })
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  return (
    <div className="card">
      {error && <div className="alert alert-error">{error}</div>}
      <button type="button" className="btn btn-danger btn-full" onClick={handleDelete}>
        Delete ticket
      </button>
    </div>
  )
}

function Comments({ ticket, onAdded }) {
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [sending, setSending] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    if (!message.trim()) {
      setError('Write a message first.')
      return
    }
    setSending(true)
    setError('')
    try {
      await ticketApi.addComment(ticket.id, message.trim())
      setMessage('')
      onAdded()
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="card">
      <h2>Comments ({ticket.comments.length})</h2>
      {ticket.comments.length === 0 && <p className="muted">No comments yet.</p>}
      <ul className="comments">
        {ticket.comments.map((comment) => (
          <li key={comment.id} className="comment">
            <div className="comment-head">
              <strong>{comment.author.full_name}</strong>
              <span className="role-tag">{comment.author.role}</span>
              <span className="muted">{formatDate(comment.created_at)}</span>
            </div>
            <p>{comment.message}</p>
          </li>
        ))}
      </ul>
      <form onSubmit={handleSubmit} className="comment-form">
        {error && <div className="alert alert-error">{error}</div>}
        <textarea
          rows={3}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Write a comment"
          aria-label="New comment"
        />
        <button className="btn btn-primary" disabled={sending}>
          {sending ? 'Posting...' : 'Post comment'}
        </button>
      </form>
    </div>
  )
}
