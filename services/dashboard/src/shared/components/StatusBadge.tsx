interface Props {
  severity: 'warning' | 'critical' | string
  label?: string
}

export default function StatusBadge({ severity, label }: Props) {
  const styles =
    severity === 'critical'
      ? 'bg-red-900/40 text-red-400 border border-red-800'
      : 'bg-amber-900/40 text-amber-400 border border-amber-800'

  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${styles}`}>
      {label ?? severity}
    </span>
  )
}
