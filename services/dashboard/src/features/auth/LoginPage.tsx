import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { setToken } from '../../shared/auth'

export default function LoginPage() {
  const [token, setTokenInput] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const res = await fetch('/api/consignments/', {
        headers: { Authorization: `Bearer ${token.trim()}` },
      })
      if (res.ok) {
        setToken(token.trim())
        navigate('/', { replace: true })
      } else if (res.status === 401 || res.status === 403) {
        setError('Token invalide.')
      } else {
        setError(`Erreur inattendue (${res.status}).`)
      }
    } catch {
      setError('Service API inaccessible.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-emerald-400 tracking-tight">Olive Oil Monitor</h1>
          <p className="text-slate-500 text-sm mt-1">Surveillance qualité huile d'olive</p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="bg-slate-800 border border-slate-700 rounded-xl p-6 flex flex-col gap-4"
        >
          <div className="flex flex-col gap-1">
            <label htmlFor="token" className="text-xs font-medium text-slate-400 uppercase tracking-wider">
              Token API
            </label>
            <input
              id="token"
              type="password"
              value={token}
              onChange={(e) => setTokenInput(e.target.value)}
              placeholder="Entrer le token d'accès"
              autoFocus
              required
              className="bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100
                         placeholder-slate-600 focus:outline-none focus:border-emerald-500 transition-colors"
            />
          </div>

          {error && (
            <p className="text-red-400 text-xs">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading || token.trim() === ''}
            className="bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-700 disabled:text-slate-500
                       text-white font-medium rounded-lg py-2 text-sm transition-colors"
          >
            {loading ? 'Connexion...' : 'Connexion'}
          </button>
        </form>
      </div>
    </div>
  )
}
