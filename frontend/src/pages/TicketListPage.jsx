import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { categoryApi, ticketApi } from '../api/endpoints'
import { useAuth } from '../auth/useAuth'
import Badge from '../components/Badge'
import Pagination from '../components/Pagination'
import { EmptyState, ErrorMessage, Loading } from '../components/StateMessage'
import { PRIORITY_OPTIONS, STATUS_OPTIONS, errorMessage, formatDate } from '../utils/format'
import { useFetch } from '../utils/useFetch'

const PAGE_SIZE = 10
const FILTER_KEYS = ['status', 'priority', 'category', 'unassigned']
const ORDERING_OPTIONS = [
  { value: '-created_at', label: 'Newest first' },
  { value: 'created_at', label: 'Oldest first' },
  { value: '-priority_rank', label: 'Highest priority' },
  { value: '-updated_at', label: 'Recently updated' },
]

const PAGE_TITLES = {
  customer: 'My tickets',
  agent: 'Tickets assigned to me',
  admin: 'All tickets',
}

export default function TicketListPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const [searchText, setSearchText] = useState(params.get('search') || '')
  const searchTimer = useRef(null)

  const page = Number(params.get('page') || 1)
  const queryString = params.toString()
  const fetchTickets = useCallback(
    () =>
      ticketApi.list({
        ordering: '-created_at',
        ...Object.fromEntries(new URLSearchParams(queryString)),
      }),
    [queryString],
  )
  const { data, error, reload } = useFetch(fetchTickets)
  const { data: categories } = useFetch(categoryApi.list)

  useEffect(() => () => clearTimeout(searchTimer.current), [])

  function updateParam(key, value) {
    setParams((current) => {
      const next = new URLSearchParams(current)
      if (value) next.set(key, value)
      else next.delete(key)
      if (key !== 'page') next.delete('page')
      return next
    })
  }

  // Wait until the user stops typing before searching.
  function handleSearchChange(value) {
    setSearchText(value)
    clearTimeout(searchTimer.current)
    searchTimer.current = setTimeout(() => updateParam('search', value.trim()), 400)
  }

  function clearFilters() {
    clearTimeout(searchTimer.current)
    setSearchText('')
    setParams({})
  }

  const hasFilters = FILTER_KEYS.some((key) => params.get(key)) || params.get('search')

  return (
    <section>
      <div className="page-header">
        <div>
          <h1>{PAGE_TITLES[user.role]}</h1>
          {data && <p className="muted">{data.count} tickets</p>}
        </div>
        {user.role === 'customer' && (
          <Link to="/tickets/new" className="btn btn-primary">
            New ticket
          </Link>
        )}
      </div>

      <div className="card filters">
        <input
          type="search"
          placeholder="Search title or description"
          value={searchText}
          onChange={(e) => handleSearchChange(e.target.value)}
          aria-label="Search tickets"
        />
        <select
          value={params.get('status') || ''}
          onChange={(e) => updateParam('status', e.target.value)}
          aria-label="Filter by status"
        >
          <option value="">All statuses</option>
          {STATUS_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <select
          value={params.get('priority') || ''}
          onChange={(e) => updateParam('priority', e.target.value)}
          aria-label="Filter by priority"
        >
          <option value="">All priorities</option>
          {PRIORITY_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <select
          value={params.get('category') || ''}
          onChange={(e) => updateParam('category', e.target.value)}
          aria-label="Filter by category"
        >
          <option value="">All categories</option>
          {categories?.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <select
          value={params.get('ordering') || '-created_at'}
          onChange={(e) => updateParam('ordering', e.target.value)}
          aria-label="Sort tickets"
        >
          {ORDERING_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        {user.role === 'admin' && (
          <label className="checkbox">
            <input
              type="checkbox"
              checked={params.get('unassigned') === 'true'}
              onChange={(e) => updateParam('unassigned', e.target.checked ? 'true' : '')}
            />
            Unassigned only
          </label>
        )}
        {hasFilters && (
          <button type="button" className="btn btn-link" onClick={clearFilters}>
            Clear filters
          </button>
        )}
      </div>

      {error && <ErrorMessage message={errorMessage(error)} onRetry={reload} />}
      {!error && !data && <Loading text="Loading tickets..." />}
      {!error && data && data.results.length === 0 && (
        <EmptyState title={hasFilters ? 'No tickets match these filters.' : 'No tickets yet.'}>
          {user.role === 'customer' && !hasFilters && (
            <Link to="/tickets/new" className="btn btn-primary">
              Raise your first ticket
            </Link>
          )}
        </EmptyState>
      )}
      {!error && data && data.results.length > 0 && (
        <>
          <div className="card table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Title</th>
                  <th>Category</th>
                  <th>Priority</th>
                  <th>Status</th>
                  {user.role !== 'customer' && <th>Customer</th>}
                  {user.role !== 'agent' && <th>Assigned to</th>}
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((ticket) => (
                  <tr
                    key={ticket.id}
                    className="clickable"
                    onClick={() => navigate(`/tickets/${ticket.id}`)}
                  >
                    <td className="muted">{ticket.id}</td>
                    <td>
                      <Link to={`/tickets/${ticket.id}`} onClick={(e) => e.stopPropagation()}>
                        {ticket.title}
                      </Link>
                      {ticket.comment_count > 0 && (
                        <span className="comment-count">
                          {ticket.comment_count}{' '}
                          {ticket.comment_count === 1 ? 'comment' : 'comments'}
                        </span>
                      )}
                    </td>
                    <td>{ticket.category_name}</td>
                    <td>
                      <Badge kind="priority" value={ticket.priority} />
                    </td>
                    <td>
                      <Badge kind="status" value={ticket.status} />
                    </td>
                    {user.role !== 'customer' && <td>{ticket.created_by.full_name}</td>}
                    {user.role !== 'agent' && (
                      <td>
                        {ticket.assigned_to?.full_name || <span className="muted">Unassigned</span>}
                      </td>
                    )}
                    <td className="nowrap">{formatDate(ticket.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination
            page={page}
            pageSize={PAGE_SIZE}
            count={data.count}
            onChange={(next) => updateParam('page', String(next))}
          />
        </>
      )}
    </section>
  )
}
