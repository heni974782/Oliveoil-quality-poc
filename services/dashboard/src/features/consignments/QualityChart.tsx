import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from 'recharts'
import type { QualityPoint } from '../../shared/types'

interface Props {
  data: QualityPoint[]
}

function buildFormatter(points: QualityPoint[]) {
  if (points.length < 2) return (iso: string) => iso
  const first = new Date(points[0].time)
  const last  = new Date(points[points.length - 1].time)
  const multiDay = first.toDateString() !== last.toDateString()

  return (iso: string) => {
    const d = new Date(iso)
    if (multiDay) {
      return d.toLocaleString('fr-CA', { month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit' })
    }
    return d.toLocaleTimeString('fr-CA', { hour: '2-digit', minute: '2-digit' })
  }
}

function tickInterval(count: number): number {
  return Math.max(1, Math.floor(count / 6))
}

export default function QualityChart({ data }: Props) {
  const fmt      = buildFormatter(data)
  const interval = tickInterval(data.length)

  const chartData = data.map((p) => ({
    t:     fmt(p.time),
    full:  new Date(p.time).toLocaleString('fr-CA', {
             month: 'short', day: '2-digit',
             hour: '2-digit', minute: '2-digit', second: '2-digit',
           }),
    score: Number(p.quality_score.toFixed(1)),
  }))

  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={chartData} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
        <XAxis dataKey="t" stroke="#64748B" tick={{ fontSize: 10 }} interval={interval} />
        <YAxis domain={[0, 100]} stroke="#64748B" tick={{ fontSize: 10 }} width={36} />
        <Tooltip
          contentStyle={{ backgroundColor: '#1E293B', border: '1px solid #334155', borderRadius: '8px', fontSize: '12px' }}
          labelStyle={{ color: '#CBD5E1' }}
          labelFormatter={(_, payload) => payload?.[0]?.payload?.full ?? ''}
          formatter={(v: number) => [`${v} / 100`, 'Score qualité'] as [string, string]}
        />
        <ReferenceLine y={70} stroke="#F59E0B" strokeDasharray="4 2" label={{ value: 'Warning', fill: '#F59E0B', fontSize: 10 }} />
        <ReferenceLine y={50} stroke="#EF4444" strokeDasharray="4 2" label={{ value: 'Critical', fill: '#EF4444', fontSize: 10 }} />
        <Line type="monotone" dataKey="score" name="Score" stroke="#34D399" dot={false} strokeWidth={2} />
      </LineChart>
    </ResponsiveContainer>
  )
}
