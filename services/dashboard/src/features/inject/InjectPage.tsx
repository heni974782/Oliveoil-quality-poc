import { useState } from 'react'
import { useConsignments } from '../consignments/hooks'
import { useLiveData } from '../../shared/useLiveData'
import StatusBadge from '../../shared/components/StatusBadge'
import { injectPoint, injectScenario } from './api'
import type { ScenarioPayload } from './api'

type Status = { kind: 'idle' } | { kind: 'ok'; msg: string } | { kind: 'err'; msg: string }

interface ScenarioPreset {
  label: string
  description: string
  values: Omit<ScenarioPayload, 'consignment_id'>
}

const PRESETS: ScenarioPreset[] = [
  {
    label: 'Canicule 2h',
    description: '38°C soutenu sur 2h — fait chuter le score (exposition thermique)',
    values: { temperature_c: 38, light_lux: 200, humidity_pct: 50, duration_minutes: 120, points: 24 },
  },
  {
    label: 'Exposition lumière 1h',
    description: '30 000 lux sur 1h — dégradation lumineuse',
    values: { temperature_c: 22, light_lux: 30000, humidity_pct: 45, duration_minutes: 60, points: 12 },
  },
  {
    label: 'Humidité élevée 3h',
    description: '85% sur 3h — déclenche high_humidity, impact score faible',
    values: { temperature_c: 20, light_lux: 50, humidity_pct: 85, duration_minutes: 180, points: 18 },
  },
]

const inputClass =
  'bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 ' +
  'focus:outline-none focus:border-emerald-500 transition-colors w-full'

const labelClass = 'text-xs font-medium text-slate-400 uppercase tracking-wider mb-1 block'

function scoreColor(s: number | null) {
  if (s === null) return 'text-slate-400'
  if (s >= 70) return 'text-emerald-400'
  if (s >= 50) return 'text-amber-400'
  return 'text-red-400'
}

const fmtMetric = (v: number | null, unit: string, digits = 1) =>
  v === null ? '—' : `${v.toFixed(digits)} ${unit}`

export default function InjectPage() {
  const { data: consignments } = useConsignments()
  const { data: live, connected } = useLiveData()
  const ids = consignments?.map((c) => c.consignment_id) ?? []

  const [cid, setCid] = useState('')
  const [temp, setTemp] = useState('35')
  const [lux, setLux] = useState('8000')
  const [hum, setHum] = useState('75')
  const [status, setStatus] = useState<Status>({ kind: 'idle' })
  const [busy, setBusy] = useState(false)

  // Default consignment once list loads
  const activeCid = cid || ids[0] || ''

  // Live state of the targeted consignment, pushed every 10s over WebSocket.
  const liveCons = live?.consignments.find((c) => c.consignment_id === activeCid) ?? null
  const liveAlerts = (live?.recent_alerts ?? [])
    .filter((a) => a.consignment_id === activeCid)
    .slice(0, 5)

  async function handlePoint(e: React.FormEvent) {
    e.preventDefault()
    if (!activeCid) return
    setBusy(true)
    setStatus({ kind: 'idle' })
    try {
      const r = await injectPoint({
        consignment_id: activeCid,
        temperature_c: Number(temp),
        light_lux: Number(lux),
        humidity_pct: Number(hum),
        event: 'manual',
      })
      setStatus({ kind: 'ok', msg: `Point publié sur ${r.topic}. Visible après validation ingestion.` })
    } catch (err) {
      setStatus({ kind: 'err', msg: err instanceof Error ? err.message : String(err) })
    } finally {
      setBusy(false)
    }
  }

  async function handleScenario(preset: ScenarioPreset) {
    if (!activeCid) return
    setBusy(true)
    setStatus({ kind: 'idle' })
    try {
      const r = await injectScenario({ consignment_id: activeCid, ...preset.values })
      setStatus({
        kind: 'ok',
        msg: `${r.published} points publiés sur ${r.duration_minutes} min. Le score se met à jour au prochain cycle (≤30s).`,
      })
    } catch (err) {
      setStatus({ kind: 'err', msg: err instanceof Error ? err.message : String(err) })
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="max-w-3xl mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Injection manuelle</h1>
        <p className="text-slate-500 text-sm mt-1">
          Publie de la télémétrie via MQTT — validée par l'ingestion comme tout autre émetteur.
          Aucune écriture directe en base.
        </p>
      </div>

      {/* Consignment selector */}
      <div>
        <label className={labelClass}>Consignation cible</label>
        <select
          value={activeCid}
          onChange={(e) => setCid(e.target.value)}
          className={inputClass}
        >
          {ids.length === 0 && <option value="">Aucune consignation</option>}
          {ids.map((id) => (
            <option key={id} value={id}>{id}</option>
          ))}
        </select>
      </div>

      {status.kind !== 'idle' && (
        <div
          className={`rounded-lg px-4 py-3 text-sm border ${
            status.kind === 'ok'
              ? 'bg-emerald-950/40 border-emerald-700 text-emerald-300'
              : 'bg-red-950/40 border-red-700 text-red-300'
          }`}
        >
          {status.msg}
        </div>
      )}

      {/* Live state of the targeted consignment — updates after injection */}
      <section className="bg-slate-800 border border-slate-700 rounded-xl p-5">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-slate-300 font-semibold text-sm uppercase tracking-wide">
            État en direct — {activeCid || '—'}
          </h2>
          <div className="flex items-center gap-2 text-xs">
            <span className={`w-2 h-2 rounded-full ${connected ? 'bg-emerald-400 animate-pulse' : 'bg-slate-500'}`} />
            <span className={connected ? 'text-emerald-400' : 'text-slate-500'}>
              {connected ? 'LIVE' : 'RECONNEXION...'}
            </span>
          </div>
        </div>

        {liveCons ? (
          <>
            <div className="flex items-baseline gap-6 mb-4">
              <div>
                <span className="text-xs text-slate-500 block">Score</span>
                <span className={`text-4xl font-bold ${scoreColor(liveCons.quality_score)}`}>
                  {liveCons.quality_score !== null ? liveCons.quality_score.toFixed(1) : '—'}
                  <span className="text-slate-500 text-base ml-1">/100</span>
                </span>
              </div>
              <div className="grid grid-cols-3 gap-x-6 gap-y-1 text-sm">
                <div>
                  <span className="text-xs text-slate-500 block">Température</span>
                  <span className="text-orange-300 font-medium">{fmtMetric(liveCons.temperature_c, '°C')}</span>
                </div>
                <div>
                  <span className="text-xs text-slate-500 block">Lumière</span>
                  <span className="text-yellow-300 font-medium">{fmtMetric(liveCons.light_lux, 'lux', 0)}</span>
                </div>
                <div>
                  <span className="text-xs text-slate-500 block">Humidité</span>
                  <span className="text-blue-300 font-medium">{fmtMetric(liveCons.humidity_pct, '%')}</span>
                </div>
              </div>
            </div>

            <div>
              <span className="text-xs text-slate-500 uppercase tracking-wide">Alertes récentes</span>
              {liveAlerts.length === 0 ? (
                <p className="text-slate-600 text-xs mt-1">Aucune.</p>
              ) : (
                <ul className="mt-2 space-y-1">
                  {liveAlerts.map((a) => (
                    <li key={a.id} className="flex items-center gap-2 text-xs">
                      <StatusBadge severity={a.severity} />
                      <span className="text-slate-400 font-mono">{a.alert_type}</span>
                      <span className="text-slate-500 truncate">{a.message}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <p className="text-slate-600 text-xs mt-4">
              Push WebSocket toutes les 10 s. Après injection, le score se recalcule au prochain
              cycle moteur (≤ 30 s) puis remonte ici automatiquement.
            </p>
          </>
        ) : (
          <p className="text-slate-500 text-sm">En attente de données live...</p>
        )}
      </section>

      {/* Single point */}
      <section className="bg-slate-800 border border-slate-700 rounded-xl p-5">
        <h2 className="text-slate-300 font-semibold mb-1 text-sm uppercase tracking-wide">
          Point unique
        </h2>
        <p className="text-slate-500 text-xs mb-4">
          Une mesure instantanée. Déclenche les alertes instantanées (temp / lux / humidité).
          Impact sur le score cumulé : négligeable.
        </p>
        <form onSubmit={handlePoint} className="grid grid-cols-3 gap-3 items-end">
          <div>
            <label className={labelClass}>Température (°C)</label>
            <input className={inputClass} type="number" step="0.1" value={temp} onChange={(e) => setTemp(e.target.value)} />
          </div>
          <div>
            <label className={labelClass}>Lumière (lux)</label>
            <input className={inputClass} type="number" step="1" value={lux} onChange={(e) => setLux(e.target.value)} />
          </div>
          <div>
            <label className={labelClass}>Humidité (%)</label>
            <input className={inputClass} type="number" step="0.1" value={hum} onChange={(e) => setHum(e.target.value)} />
          </div>
          <div className="col-span-3">
            <button
              type="submit"
              disabled={busy || !activeCid}
              className="bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-700 disabled:text-slate-500
                         text-white font-medium rounded-lg py-2 px-4 text-sm transition-colors"
            >
              {busy ? 'Publication...' : 'Publier le point'}
            </button>
          </div>
        </form>
      </section>

      {/* Scenarios */}
      <section className="bg-slate-800 border border-slate-700 rounded-xl p-5">
        <h2 className="text-slate-300 font-semibold mb-1 text-sm uppercase tracking-wide">
          Scénario soutenu
        </h2>
        <p className="text-slate-500 text-xs mb-4">
          Injecte une rafale de points horodatés dans le passé pour simuler une exposition
          prolongée — c'est ce qui fait réellement bouger le score qualité.
        </p>
        <div className="grid gap-3">
          {PRESETS.map((p) => (
            <button
              key={p.label}
              onClick={() => handleScenario(p)}
              disabled={busy || !activeCid}
              className="text-left bg-slate-900 border border-slate-600 hover:border-emerald-500
                         disabled:opacity-50 rounded-lg px-4 py-3 transition-colors"
            >
              <span className="text-slate-200 font-medium text-sm">{p.label}</span>
              <span className="block text-slate-500 text-xs mt-0.5">{p.description}</span>
            </button>
          ))}
        </div>
      </section>
    </main>
  )
}
