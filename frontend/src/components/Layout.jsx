import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'
import { label } from '../utils/format'

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar-inner">
          <NavLink to="/tickets" className="brand">
            SupportDesk
          </NavLink>
          <nav className="nav">
            <NavLink to="/tickets" end>
              Tickets
            </NavLink>
            {user.role === 'customer' && <NavLink to="/tickets/new">New ticket</NavLink>}
            {user.role === 'admin' && <NavLink to="/dashboard">Dashboard</NavLink>}
            {user.role === 'admin' && <NavLink to="/manage">Manage</NavLink>}
          </nav>
          <div className="user-menu">
            <span className="user-name">
              {user.full_name} <span className="role-tag">{label(user.role)}</span>
            </span>
            <button type="button" className="btn btn-link" onClick={handleLogout}>
              Log out
            </button>
          </div>
        </div>
      </header>
      <main className="container">
        <Outlet />
      </main>
    </div>
  )
}
