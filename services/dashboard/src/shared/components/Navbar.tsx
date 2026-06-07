import { Link, useNavigate } from 'react-router-dom'
import { useLiveData } from '../useLiveData'
import { clearToken } from '../auth'

export default function Navbar() {
  const { connected } = useLiveData()
  const navigate = useNavigate()

  function handleLogout() {
    clearToken()
    navigate('/login', { replace: true })
  }

  return (
    <nav className="bg-slate-800 border-b border-slate-700 px-6 py-3 flex items-center gap-4">
      <Link to="/" className="text-emerald-400 font-bold text-lg tracking-tight">
        Olive Oil Monitor
      </Link>
      <span className="text-slate-500 text-sm">Surveillance qualité huile d'olive</span>
      <div className="ml-auto flex items-center gap-4">
        <div className="flex items-center gap-2 text-xs">
          <span
            className={`w-2 h-2 rounded-full ${
              connected ? 'bg-emerald-400 animate-pulse' : 'bg-slate-500'
            }`}
          />
          <span className={connected ? 'text-emerald-400' : 'text-slate-500'}>
            {connected ? 'LIVE' : 'RECONNEXION...'}
          </span>
        </div>
        <button
          onClick={handleLogout}
          className="text-xs text-slate-400 hover:text-slate-200 border border-slate-600
                     hover:border-slate-400 rounded-md px-3 py-1 transition-colors"
        >
          Déconnexion
        </button>
      </div>
    </nav>
  )
}
