import React from 'react'
import { apiGet } from './api'

/** Charge une route API avant affichage : { data, loading, error, reload }. */
export function useApi<T>(path: string | null, deps: any[] = []) {
  const [data, setData] = React.useState<T | null>(null)
  const [loading, setLoading] = React.useState(path != null)
  const [error, setError] = React.useState('')
  const reload = React.useCallback(() => {
    if (!path) return
    setLoading(true)
    setError('')
    apiGet<T>(path)
      .then((d) => { setData(d); setLoading(false) })
      .catch((e: any) => { setError(e.message || String(e)); setLoading(false) })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, ...deps])
  React.useEffect(() => { reload() }, [reload])
  return { data, loading, error, reload, setData }
}
