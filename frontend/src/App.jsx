import { Link, Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import RequireAuth from './components/RequireAuth'
import CreateTicketPage from './pages/CreateTicketPage'
import DashboardPage from './pages/DashboardPage'
import LoginPage from './pages/LoginPage'
import ManagePage from './pages/ManagePage'
import RegisterPage from './pages/RegisterPage'
import TicketDetailPage from './pages/TicketDetailPage'
import TicketListPage from './pages/TicketListPage'

function NotFound() {
  return (
    <div className="state">
      <p className="state-title">Page not found.</p>
      <Link to="/tickets">Go to tickets</Link>
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route index element={<Navigate to="/tickets" replace />} />
        <Route path="tickets" element={<TicketListPage />} />
        <Route
          path="tickets/new"
          element={
            <RequireAuth roles={['customer']}>
              <CreateTicketPage />
            </RequireAuth>
          }
        />
        <Route path="tickets/:id" element={<TicketDetailPage />} />
        <Route
          path="dashboard"
          element={
            <RequireAuth roles={['admin']}>
              <DashboardPage />
            </RequireAuth>
          }
        />
        <Route
          path="manage"
          element={
            <RequireAuth roles={['admin']}>
              <ManagePage />
            </RequireAuth>
          }
        />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}
