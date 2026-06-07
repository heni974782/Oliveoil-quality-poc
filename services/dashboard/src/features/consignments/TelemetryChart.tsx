import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import type { TelemetryPoint } from '../../shared/types'

interface Props {
  data: TelemetryPoint[]
}

// Show "DD MMM HH:MM" if data spans multiple days, "HH:MM" if same day.
function buildFormatter(points: TelemetryPoint[]) {
  if (points.length < 2) return (iso: string) => iso

  const first = new Date(points[0].time)
  const last  = new Date(points[points.length - 1].time)
  const multiDay = first.toDateString() !== last.toDateString()

  return (iso: string) => {
    const d = new Date(iso)
    if (multiDay) {
      return d.toLocaleString('fr-CA', {
        month: 'short',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      })
    }
    return d.toLocaleTimeString('fr-CA', { hour: '2-digit', minute: '2-digit' })
  }
}

// Show ~6 evenly spaced ticks regardless of dataset size.
function tickInterval(count: number): number {
  return Math.max(1, Math.floor(count / 6))
}

const tooltipStyle = {
  contentStyle: { backgroundColor: '#1E293B', border: '1px solid #334155', borderRadius: '8px', fontSize: '12px' },
  labelStyle: { color: '#CBD5E1' },
}

const axisProps = {
  stroke: '#64748B',
  tick: { fontSize: 10 },
}

interface MiniChartProps {
  chartData: { t: string; full: string; value: number }[]
  label: string
  unit: string
  color: string
  interval: number
  domain?: [number | 'auto', number | 'auto']
}

function MiniChart({ chartData, label, unit, color, interval, domain }: MiniChartProps) {
  return (
    <div>
      <p className="text-xs font-medium text-slate-400 mb-1 ml-1">
        {label} <span className="text-slate-500">({unit})</span>
      </p>
      <ResponsiveContainer width="100%" height={160}>
        <LineChart data={chartData} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="t" {...axisProps} interval={interval} />
          <YAxis {...axisProps} width={52} domain={domain ?? (['auto', 'auto'] as ['auto', 'auto'])}
            tickFormatter={(v) => String(v)} />
          <Tooltip
            {...tooltipStyle}
            // Tooltip shows the full timestamp for precision.
            labelFormatter={(_, payload) => payload?.[0]?.payload?.full ?? ''}
            formatter={(v: number) => [`${v} ${unit}`, label] as [string, string]}
          />
          <Line type="monotone" dataKey="value" stroke={color} dot={false} strokeWidth={2} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

export default function TelemetryChart({ data }: Props) {
  const fmt      = buildFormatter(data)
  const interval = tickInterval(data.length)

  // t = short label for axis ticks, full = precise label for tooltip
  const base = data.map((p) => ({
    t:    fmt(p.time),
    full: new Date(p.time).toLocaleString('fr-CA', {
            month: 'short', day: '2-digit',
            hour: '2-digit', minute: '2-digit', second: '2-digit',
          }),
    temp: p.temperature_c,
    lux:  p.light_lux,
    hum:  p.humidity_pct,
  }))

  const tempData = base.map(({ t, full, temp }) => ({ t, full, value: Number(temp.toFixed(1)) }))
  const luxData  = base.map(({ t, full, lux })  => ({ t, full, value: Number(lux.toFixed(0)) }))
  const humData  = base.map(({ t, full, hum })  => ({ t, full, value: Number(hum.toFixed(1)) }))

  return (
    <div className="flex flex-col gap-6">
      <MiniChart chartData={tempData} label="Température" unit="°C"  color="#FB923C" interval={interval} />
      <MiniChart chartData={luxData}  label="Luminosité"  unit="lux" color="#FBBF24" interval={interval} />
      <MiniChart chartData={humData}  label="Humidité"    unit="%"   color="#60A5FA" interval={interval} domain={[0, 100]} />
    </div>
  )
}
