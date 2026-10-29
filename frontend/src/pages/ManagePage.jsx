import { useCallback, useState } from 'react'
import { categoryApi, userApi } from '../api/endpoints'
import { useAuth } from '../auth/useAuth'
import Pagination from '../components/Pagination'
import { ErrorMessage, Loading } from '../components/StateMessage'
import { ROLE_OPTIONS, errorMessage, fieldErrors } from '../utils/format'
import { useFetch } from '../utils/useFetch'

const PAGE_SIZE = 10

export default function ManagePage() {
  return (
    <section>
      <div className="page-header">
        <h1>Manage</h1>
      </div>
      <div className="manage-grid">
        <Categories />
        <Users />
      </div>
    </section>
  )
}

function Categories() {
  const { data: categories, error, reload } = useFetch(categoryApi.list)
  const [form, setForm] = useState({ name: '', description: '' })
  const [formErrors, setFormErrors] = useState({})
  const [saving, setSaving] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    if (!form.name.trim()) {
      setFormErrors({ name: 'Name is required.' })
      return
    }
    setSaving(true)
    setFormErrors({})
    try {
      await categoryApi.create({ name: form.name.trim(), description: form.description.trim() })
      setForm({ name: '', description: '' })
      reload()
    } catch (err) {
      setFormErrors(fieldErrors(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="card">
      <h2>Categories</h2>
      {error && <ErrorMessage message={errorMessage(error)} onRetry={reload} />}
      {!error && !categories && <Loading />}
      {categories && (
        <ul className="simple-list">
          {categories.map((c) => (
            <li key={c.id}>
              <strong>{c.name}</strong>
              {c.description && <span className="muted"> - {c.description}</span>}
            </li>
          ))}
        </ul>
      )}
      <form onSubmit={handleSubmit} className="inline-form" noValidate>
        <label className="field">
          <span>New category</span>
          <input
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="Name"
            aria-invalid={Boolean(formErrors.name)}
          />
          {formErrors.name && <small className="field-error">{formErrors.name}</small>}
        </label>
        <label className="field">
          <span>Description</span>
          <input
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            placeholder="Optional"
          />
        </label>
        <button className="btn btn-primary" disabled={saving}>
          {saving ? 'Adding...' : 'Add category'}
        </button>
      </form>
    </div>
  )
}

function Users() {
  const { user: me } = useAuth()
  const [page, setPage] = useState(1)
  const fetchUsers = useCallback(() => userApi.list({ page }), [page])
  const { data, error, reload, setData } = useFetch(fetchUsers)
  const [rowError, setRowError] = useState('')

  async function change(user, payload) {
    setRowError('')
    try {
      const updated = await userApi.update(user.id, payload)
      setData((current) => ({
        ...current,
        results: current.results.map((u) => (u.id === updated.id ? updated : u)),
      }))
    } catch (err) {
      setRowError(errorMessage(err))
    }
  }

  return (
    <div className="card table-wrap">
      <h2>Users</h2>
      {rowError && <div className="alert alert-error">{rowError}</div>}
      {error && <ErrorMessage message={errorMessage(error)} onRetry={reload} />}
      {!error && !data && <Loading />}
      {data && (
        <>
          <table className="table">
            <thead>
              <tr>
                <th>User</th>
                <th>Email</th>
                <th>Role</th>
                <th>Active</th>
              </tr>
            </thead>
            <tbody>
              {data.results.map((u) => (
                <tr key={u.id}>
                  <td>
                    {u.full_name}
                    <div className="muted small">{u.username}</div>
                  </td>
                  <td>{u.email}</td>
                  <td>
                    <select
                      value={u.role}
                      disabled={u.id === me.id}
                      onChange={(e) => change(u, { role: e.target.value })}
                      aria-label={`Role of ${u.username}`}
                    >
                      {ROLE_OPTIONS.map((o) => (
                        <option key={o.value} value={o.value}>
                          {o.label}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <input
                      type="checkbox"
                      checked={u.is_active}
                      disabled={u.id === me.id}
                      onChange={(e) => change(u, { is_active: e.target.checked })}
                      aria-label={`${u.username} is active`}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <Pagination page={page} pageSize={PAGE_SIZE} count={data.count} onChange={setPage} />
        </>
      )}
    </div>
  )
}
