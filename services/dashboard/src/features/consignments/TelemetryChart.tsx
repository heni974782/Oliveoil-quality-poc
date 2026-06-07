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

const fmtTime = (iso: string) =>
  new Date(iso).toLocaleTimeString('fr-CA', { hour: '2-digit', minute: '2-digit' })

const tooltipStyle = {
  contentStyle: { backgroundColor: '#1E293B', border: '1px solid #334155', borderRadius: '8px', fontSize: '12px' },
  labelStyle: { color: '#CBD5E1' },
}

const axisProps = {
  stroke: '#64748B',
  tick: { fontSize: 10 },
}

interface MiniChartProps {
  chartData: { t: string; value: number }[]
  label: string
  unit: string
  color: string
  domain?: [number | 'auto', number | 'auto']
}

function MiniChart({ chartData, label, unit, color, domain }: MiniChartProps) {
  return (
    <div>
      <p className="text-xs font-medium text-slate-400 mb-1 ml-1">
        {label} <span className="text-slate-500">({unit})</span>
      </p>
      <ResponsiveContainer width="100%" height={160}>
        <LineChart data={chartData} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="t" {...axisProps} interval="preserveStartEnd" />
          <YAxis {...axisProps} width={48} domain={domain ?? (['auto', 'auto'] as ['auto', 'auto'])}
            tickFormatter={(v) => String(v)} />
          <Tooltip {...tooltipStyle} formatter={(v: number) => [`${v} ${unit}`, label] as [string, string]} />
          <Line type="monotone" dataKey="value" stroke={color} dot={false} strokeWidth={2} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

export default function TelemetryChart({ data }: Props) {
  const base = data.map((p) => ({ t: fmtTime(p.time), temp: p.temperature_c, lux: p.light_lux, hum: p.humidity_pct }))

  const tempData = base.map(({ t, temp }) => ({ t, value: Number(temp.toFixed(1)) }))
  const luxData  = base.map(({ t, lux })  => ({ t, value: Number(lux.toFixed(0)) }))
  const humData  = base.map(({ t, hum })  => ({ t, value: Number(hum.toFixed(1)) }))

  return (
    <div className="flex flex-col gap-6">
      <MiniChart chartData={tempData} label="Température" unit="°C"  color="#FB923C" />
      <MiniChart chartData={luxData}  label="Luminosité"  unit="lux" color="#FBBF24" />
      <MiniChart chartData={humData}  label="Humidité"    unit="%"   color="#60A5FA" domain={[0, 100]} />
    </div>
  )
}
