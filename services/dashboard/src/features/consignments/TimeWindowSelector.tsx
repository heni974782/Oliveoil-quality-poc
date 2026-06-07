export interface TimeWindow {
  label: string
  hours: number
}

export const TIME_WINDOWS: TimeWindow[] = [
  { label: '1h', hours: 1 },
  { label: '6h', hours: 6 },
  { label: '24h', hours: 24 },
  { label: '7j', hours: 168 },
]

interface Props {
  value: number
  onChange: (hours: number) => void
}

export default function TimeWindowSelector({ value, onChange }: Props) {
  return (
    <div className="inline-flex rounded-lg border border-slate-700 overflow-hidden">
      {TIME_WINDOWS.map((w) => (
        <button
          key={w.hours}
          onClick={() => onChange(w.hours)}
          className={`px-3 py-1 text-xs font-medium transition-colors ${
            value === w.hours
              ? 'bg-emerald-600 text-white'
              : 'bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200'
          }`}
        >
          {w.label}
        </button>
      ))}
    </div>
  )
}
