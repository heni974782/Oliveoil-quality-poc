import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useConsignmentDetail } from './hooks'
import { useAlerts } from '../alerts/hooks'
import TelemetryChart from './TelemetryChart'
import QualityChart from './QualityChart'
import TimeWindowSelector from './TimeWindowSelector'
import AlertsTable from '../alerts/AlertsTable'

export default function ConsignmentDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [hours, setHours] = useState(24)
  const { telemetry, quality } = useConsignmentDetail(id ?? '', hours)
  const alerts = useAlerts(id)

  const latestScore = quality.data?.at(-1)?.quality_score ?? null

  function scoreColor(s: number | null) {
    if (s === null) return 'text-slate-400'
    if (s >= 70) return 'text-emerald-400'
    if (s >= 50) return 'text-amber-400'
    return 'text-red-400'
  }

  return (
    <main className="max-w-7xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link to="/" className="text-slate-400 hover:text-slate-200 text-sm">
          &larr; Retour
        </Link>
        <h1 className="text-2xl font-bold text-slate-100">{id}</h1>
        {latestScore !== null && (
          <span className={`text-3xl font-bold ${scoreColor(latestScore)}`}>
            {latestScore.toFixed(1)}<span className="text-slate-500 text-base ml-1">/100</span>
          </span>
        )}
        <div className="ml-auto flex items-center gap-2">
          <span className="text-xs text-slate-500 uppercase tracking-wide">Fenêtre</span>
          <TimeWindowSelector value={hours} onChange={setHours} />
        </div>
      </div>

      {/* Quality score over time */}
      <section className="bg-slate-800 border border-slate-700 rounded-xl p-5">
        <h2 className="text-slate-300 font-semibold mb-3 text-sm uppercase tracking-wide">
          Évolution du score qualité
        </h2>
        {quality.isLoading ? (
          <p className="text-slate-500 text-sm">Chargement...</p>
        ) : quality.data && quality.data.length > 0 ? (
          <QualityChart data={quality.data} />
        ) : (
          <p className="text-slate-500 text-sm">Pas de données.</p>
        )}
      </section>

      {/* Telemetry charts */}
      <section className="bg-slate-800 border border-slate-700 rounded-xl p-5">
        <h2 className="text-slate-300 font-semibold mb-3 text-sm uppercase tracking-wide">
          Télémétrie (temp / lumière / humidité)
        </h2>
        {telemetry.isLoading ? (
          <p className="text-slate-500 text-sm">Chargement...</p>
        ) : telemetry.data && telemetry.data.length > 0 ? (
          <TelemetryChart data={telemetry.data} />
        ) : (
          <p className="text-slate-500 text-sm">Pas de données.</p>
        )}
      </section>

      {/* Alerts */}
      <section className="bg-slate-800 border border-slate-700 rounded-xl p-5">
        <h2 className="text-slate-300 font-semibold mb-3 text-sm uppercase tracking-wide">
          Alertes
        </h2>
        {alerts.isLoading ? (
          <p className="text-slate-500 text-sm">Chargement...</p>
        ) : (
          <AlertsTable alerts={alerts.data ?? []} />
        )}
      </section>
    </main>
  )
}
