export const STATUS_OPTIONS = [
  { value: 'open', label: 'Open' },
  { value: 'in_progress', label: 'In progress' },
  { value: 'resolved', label: 'Resolved' },
  { value: 'closed', label: 'Closed' },
]

export const PRIORITY_OPTIONS = [
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
  { value: 'urgent', label: 'Urgent' },
]

export const ROLE_OPTIONS = [
  { value: 'customer', label: 'Customer' },
  { value: 'agent', label: 'Agent' },
  { value: 'admin', label: 'Admin' },
]

const LABELS = Object.fromEntries(
  [...STATUS_OPTIONS, ...PRIORITY_OPTIONS, ...ROLE_OPTIONS].map((o) => [o.value, o.label]),
)

export function label(value) {
  return LABELS[value] ?? value
}

export function formatDate(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

// DRF returns errors as {detail: "..."}, {field: ["..."]} or ["..."].
export function errorMessage(error, fallback = 'Something went wrong. Please try again.') {
  const data = error?.response?.data
  if (!error?.response) return 'Cannot reach the server. Is the backend running?'
  if (typeof data === 'string' || !data) return fallback
  if (data.detail) return data.detail
  if (Array.isArray(data)) return data.join(' ')
  if (data.non_field_errors) return data.non_field_errors.join(' ')
  return fallback
}

export function fieldErrors(error) {
  const data = error?.response?.data
  if (!data || typeof data !== 'object' || Array.isArray(data)) return {}
  return Object.fromEntries(
    Object.entries(data)
      .filter(([key]) => key !== 'detail' && key !== 'non_field_errors')
      .map(([key, value]) => [key, Array.isArray(value) ? value.join(' ') : String(value)]),
  )
}
