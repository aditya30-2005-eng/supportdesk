import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'
import { Loading } from './StateMessage'

export default function RequireAuth({ roles, children }) {
  const { user, isRestoring } = useAuth()
  const location = useLocation()

  if (isRestoring) return <Loading text="Checking your session..." />
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />
  if (roles && !roles.includes(user.role)) return <Navigate to="/tickets" replace />
  return children
}
