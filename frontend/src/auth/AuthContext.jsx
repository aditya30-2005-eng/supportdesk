import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  clearTokens,
  getRefreshToken,
  refreshAccessToken,
  setSessionExpiredHandler,
  setTokens,
} from '../api/client'
import { authApi } from '../api/endpoints'
import { AuthContext } from './useAuth'

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [isRestoring, setIsRestoring] = useState(Boolean(getRefreshToken()))

  useEffect(() => {
    setSessionExpiredHandler(() => setUser(null))
    if (!getRefreshToken()) return

    refreshAccessToken()
      .then(() => authApi.me())
      .then(setUser)
      .catch(() => clearTokens())
      .finally(() => setIsRestoring(false))
  }, [])

  const login = useCallback(async (username, password) => {
    const data = await authApi.login({ username, password })
    setTokens(data.access, data.refresh)
    setUser(data.user)
    return data.user
  }, [])

  const logout = useCallback(async () => {
    const refresh = getRefreshToken()
    clearTokens()
    setUser(null)
    if (refresh) await authApi.logout(refresh).catch(() => {})
  }, [])

  const value = useMemo(
    () => ({ user, isRestoring, login, logout }),
    [user, isRestoring, login, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
