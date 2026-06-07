import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import type { TelemetryPoint } from '../../shared/types'

interface Props {
  data: TelemetryPoint[]
}

const fmtTime = (iso: string) =>
  new Date(iso).toLocaleTimeString('fr-CA', { hour: '2-digit', minute: '2-digit' })

export default function TelemetryChart({ data }: Props) {
  const chartData = data.map((p) => ({
    t: fmtTime(p.time),
    temp: Number(p.temperature_c.toFixed(2)),
    lux: Number(p.light_lux.toFixed(1)),
    hum: Number(p.humidity_pct.toFixed(2)),
  }))

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={chartData} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
        <XAxis dataKey="t" stroke="#64748B" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
        <YAxis stroke="#64748B" tick={{ fontSize: 10 }} width={36} />
        <Tooltip
          contentStyle={{ backgroundColor: '#1E293B', border: '1px solid #334155', borderRadius: '8px', fontSize: '12px' }}
          labelStyle={{ color: '#CBD5E1' }}
        />
        <Legend wrapperStyle={{ fontSize: '12px' }} />
        <Line type="monotone" dataKey="temp" name="Temp (°C)" stroke="#FB923C" dot={false} strokeWidth={2} />
        <Line type="monotone" dataKey="lux"  name="Lumière (lx)" stroke="#FBBF24" dot={false} strokeWidth={2} />
        <Line type="monotone" dataKey="hum"  name="Humidité (%)" stroke="#60A5FA" dot={false} strokeWidth={2} />
      </LineChart>
    </ResponsiveContainer>
  )
}
