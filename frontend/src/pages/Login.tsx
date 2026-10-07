import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiLogin } from '../lib/api'

export default function Login() {
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(false)
  const nav = useNavigate()
  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setErr('')
    setLoading(true)
    try {
      await apiLogin(username, password)
      nav('/')
    } catch {
      setErr('Identifiants invalides — vérifiez le nom et le mot de passe.')
    } finally {
      setLoading(false)
    }
  }
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-6">
          <div className="text-5xl mb-2">🖥️</div>
          <h1 className="text-2xl font-bold">InfraOS</h1>
          <p className="text-sm text-slate-400">Infrastructure Server OS — administration</p>
        </div>
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Connexion</h2>
          <form onSubmit={submit} className="flex flex-col gap-3">
            <label className="flex flex-col gap-1 text-xs text-slate-400">
              Utilisateur
              <input
                className="px-3 py-2 rounded bg-slate-800 text-sm text-slate-100"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                autoFocus
              />
            </label>
            <label className="flex flex-col gap-1 text-xs text-slate-400">
              Mot de passe
              <input
                className="px-3 py-2 rounded bg-slate-800 text-sm text-slate-100"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
              />
            </label>
            {err && <p className="text-red-400 text-sm">{err}</p>}
            <button className="btn w-full py-2" type="submit" disabled={loading}>
              {loading ? 'Connexion…' : 'Se connecter'}
            </button>
          </form>
        </div>
        <p className="text-center text-xs text-slate-500 mt-4">
          Debian 13 · FastAPI · 100 % open source (GPLv3)
        </p>
      </div>
    </div>
  )
}
