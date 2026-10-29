import { Link } from 'react-router-dom'
import { dashboardApi } from '../api/endpoints'
import { ErrorMessage, Loading } from '../components/StateMessage'
import { PRIORITY_OPTIONS, STATUS_OPTIONS, errorMessage } from '../utils/format'
import { useFetch } from '../utils/useFetch'

function StatCard({ title, value, hint, to }) {
  const body = (
    <>
      <span className="stat-title">{title}</span>
      <span className="stat-value">{value}</span>
      {hint && <span className="muted">{hint}</span>}
    </>
  )
  return to ? (
    <Link to={to} className="card stat-card">
      {body}
    </Link>
  ) : (
    <div className="card stat-card">{body}</div>
  )
}

function BreakdownBars({ title, counts, options, kind, total }) {
  return (
    <div className="card">
      <h2>{title}</h2>
      <ul className="bars">
        {options.map((option) => {
          const count = counts[option.value] ?? 0
          const width = total ? Math.round((count / total) * 100) : 0
          return (
            <li key={option.value}>
              <span className="bar-label">{option.label}</span>
              <span className="bar-track">
                <span
                  className={`bar-fill bar-${kind}-${option.value}`}
                  style={{ width: `${width}%` }}
                />
              </span>
              <span className="bar-count">{count}</span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

export default function DashboardPage() {
  const { data: stats, error, reload } = useFetch(dashboardApi.stats)

  if (error) return <ErrorMessage message={errorMessage(error)} onRetry={reload} />
  if (!stats) return <Loading text="Loading dashboard..." />

  const { by_status: byStatus } = stats
  const avg = stats.average_resolution_hours

  return (
    <section>
      <div className="page-header">
        <h1>Dashboard</h1>
      </div>
      <div className="stats-grid">
        <StatCard title="Total tickets" value={stats.total} to="/tickets" />
        <StatCard title="Open" value={byStatus.open} to="/tickets?status=open" />
        <StatCard
          title="In progress"
          value={byStatus.in_progress}
          to="/tickets?status=in_progress"
        />
        <StatCard title="Resolved or closed" value={byStatus.resolved + byStatus.closed} />
        <StatCard title="Unassigned" value={stats.unassigned} to="/tickets?unassigned=true" />
        <StatCard
          title="Avg. resolution time"
          value={avg === null ? '-' : `${avg} h`}
          hint={avg === null ? 'No resolved tickets yet' : 'From creation to resolved'}
        />
      </div>

      <div className="two-col">
        <BreakdownBars
          title="Tickets by status"
          counts={byStatus}
          options={STATUS_OPTIONS}
          kind="status"
          total={stats.total}
        />
        <BreakdownBars
          title="Tickets by priority"
          counts={stats.by_priority}
          options={PRIORITY_OPTIONS}
          kind="priority"
          total={stats.total}
        />
      </div>

      <div className="card table-wrap">
        <h2>Agent workload</h2>
        {stats.agents.length === 0 ? (
          <p className="muted">There are no active agents.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Agent</th>
                <th>Open or in progress</th>
                <th>Resolved or closed</th>
              </tr>
            </thead>
            <tbody>
              {stats.agents.map((agent) => (
                <tr key={agent.id}>
                  <td>{agent.full_name}</td>
                  <td>{agent.open_tickets}</td>
                  <td>{agent.done_tickets}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  )
}
