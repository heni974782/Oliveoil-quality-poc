import { Link } from 'react-router-dom'
import type { ConsignmentSummary } from '../../shared/types'

function scoreColor(score: number | null) {
  if (score === null) return 'text-slate-400'
  if (score >= 70) return 'text-emerald-400'
  if (score >= 50) return 'text-amber-400'
  return 'text-red-400'
}

function scoreBg(score: number | null) {
  if (score === null) return ''
  if (score >= 70) return 'border-emerald-800'
  if (score >= 50) return 'border-amber-800'
  return 'border-red-800'
}

interface Props {
  consignment: ConsignmentSummary
}

export default function ConsignmentCard({ consignment: c }: Props) {
  return (
    <Link to={`/consignments/${c.consignment_id}`}>
      <div
        className={`bg-slate-800 border rounded-xl p-5 hover:bg-slate-750 transition-colors cursor-pointer ${scoreBg(c.quality_score)}`}
      >
        <div className="flex justify-between items-start mb-3">
          <span className="text-slate-300 font-semibold text-sm tracking-wide uppercase">
            {c.consignment_id}
          </span>
          {c.active_alerts > 0 && (
            <span className="bg-amber-900/40 text-amber-400 border border-amber-800 text-xs px-2 py-0.5 rounded-full">
              {c.active_alerts} alerte{c.active_alerts > 1 ? 's' : ''}
            </span>
          )}
        </div>

        {/* Quality score — prominent for control room readability */}
        <div className={`text-6xl font-bold mb-1 ${scoreColor(c.quality_score)}`}>
          {c.quality_score !== null ? c.quality_score.toFixed(1) : '—'}
        </div>
        <div className="text-slate-500 text-xs mb-4">score qualité / 100</div>

        {/* Live metrics */}
        <div className="grid grid-cols-3 gap-3 text-sm border-t border-slate-700 pt-3">
          <div>
            <div className="text-slate-500 text-xs mb-0.5">Temp</div>
            <div className="text-orange-400 font-semibold">
              {c.temperature_c !== null ? `${c.temperature_c.toFixed(1)}°C` : '—'}
            </div>
          </div>
          <div>
            <div className="text-slate-500 text-xs mb-0.5">Lumière</div>
            <div className="text-yellow-400 font-semibold">
              {c.light_lux !== null ? `${c.light_lux.toFixed(0)} lx` : '—'}
            </div>
          </div>
          <div>
            <div className="text-slate-500 text-xs mb-0.5">Humidité</div>
            <div className="text-blue-400 font-semibold">
              {c.humidity_pct !== null ? `${c.humidity_pct.toFixed(1)}%` : '—'}
            </div>
          </div>
        </div>

        {c.latest_time && (
          <div className="mt-3 text-xs text-slate-600">
            {new Date(c.latest_time).toLocaleTimeString('fr-CA', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
          </div>
        )}
      </div>
    </Link>
  )
}
