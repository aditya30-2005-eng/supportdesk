import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'
const REFRESH_KEY = 'supportdesk.refresh'
const NO_RETRY_URLS = ['/auth/login/', '/auth/register/', '/auth/refresh/', '/auth/logout/']

// The access token lives only in memory so it is gone when the tab closes.
// The refresh token is kept in localStorage so a page reload can get a new access token.
let accessToken = null
let refreshPromise = null
let onSessionExpired = () => {}

export const api = axios.create({ baseURL: API_URL })

export function setTokens(access, refresh) {
  accessToken = access
  if (refresh) localStorage.setItem(REFRESH_KEY, refresh)
}

export function clearTokens() {
  accessToken = null
  localStorage.removeItem(REFRESH_KEY)
}

export function getRefreshToken() {
  return localStorage.getItem(REFRESH_KEY)
}

export function setSessionExpiredHandler(handler) {
  onSessionExpired = handler
}

// Several requests can fail with 401 at the same time. They all wait for one
// refresh call, because a rotated refresh token can only be used once.
export function refreshAccessToken() {
  if (!refreshPromise) {
    const refresh = getRefreshToken()
    refreshPromise = axios
      .post(`${API_URL}/auth/refresh/`, { refresh })
      .then(({ data }) => {
        setTokens(data.access, data.refresh)
        return data.access
      })
      .finally(() => {
        refreshPromise = null
      })
  }
  return refreshPromise
}

api.interceptors.request.use((config) => {
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    const canRetry =
      error.response?.status === 401 &&
      original &&
      !original._retried &&
      !NO_RETRY_URLS.includes(original.url) &&
      getRefreshToken()

    if (!canRetry) return Promise.reject(error)

    original._retried = true
    try {
      await refreshAccessToken()
      return api(original)
    } catch (refreshError) {
      clearTokens()
      onSessionExpired()
      return Promise.reject(refreshError)
    }
  },
)
