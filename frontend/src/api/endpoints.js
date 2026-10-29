import { api } from './client'

export const authApi = {
  login: (credentials) => api.post('/auth/login/', credentials).then((r) => r.data),
  register: (payload) => api.post('/auth/register/', payload).then((r) => r.data),
  logout: (refresh) => api.post('/auth/logout/', { refresh }),
  me: () => api.get('/auth/me/').then((r) => r.data),
}

export const ticketApi = {
  list: (params) => api.get('/tickets/', { params }).then((r) => r.data),
  get: (id) => api.get(`/tickets/${id}/`).then((r) => r.data),
  create: (payload) => api.post('/tickets/', payload).then((r) => r.data),
  update: (id, payload) => api.patch(`/tickets/${id}/`, payload).then((r) => r.data),
  remove: (id) => api.delete(`/tickets/${id}/`),
  assign: (id, agentId) =>
    api.post(`/tickets/${id}/assign/`, { agent: agentId }).then((r) => r.data),
  addComment: (id, message) =>
    api.post(`/tickets/${id}/comments/`, { message }).then((r) => r.data),
}

export const categoryApi = {
  list: () => api.get('/categories/').then((r) => r.data),
  create: (payload) => api.post('/categories/', payload).then((r) => r.data),
}

export const userApi = {
  list: (params) => api.get('/users/', { params }).then((r) => r.data),
  update: (id, payload) => api.patch(`/users/${id}/`, payload).then((r) => r.data),
}

export const dashboardApi = {
  stats: () => api.get('/dashboard/stats/').then((r) => r.data),
}
