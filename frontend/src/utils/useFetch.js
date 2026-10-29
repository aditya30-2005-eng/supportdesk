import { useCallback, useEffect, useState } from 'react'

// Runs `fetcher` when it changes and keeps the latest result.
// `fetcher` must be wrapped in useCallback by the caller.
export function useFetch(fetcher) {
  const [state, setState] = useState({ data: null, error: null })
  const [version, setVersion] = useState(0)

  useEffect(() => {
    let ignore = false
    fetcher()
      .then((data) => !ignore && setState({ data, error: null }))
      .catch((error) => !ignore && setState((s) => ({ data: s.data, error })))
    return () => {
      ignore = true
    }
  }, [fetcher, version])

  const reload = useCallback(() => setVersion((v) => v + 1), [])

  const setData = useCallback((update) => {
    setState((s) => ({ ...s, data: typeof update === 'function' ? update(s.data) : update }))
  }, [])

  return { data: state.data, error: state.error, reload, setData }
}
