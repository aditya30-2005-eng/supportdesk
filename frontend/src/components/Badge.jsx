import { label } from '../utils/format'

export default function Badge({ kind, value }) {
  return <span className={`badge badge-${kind}-${value}`}>{label(value)}</span>
}
