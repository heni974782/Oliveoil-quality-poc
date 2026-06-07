import StatusBadge from '../../shared/components/StatusBadge'
import type { Alert } from '../../shared/types'

interface Props {
  alerts: Alert[]
}

interface AlertGroup {
  key: string
  first: Alert
  last: Alert
  count: number
}

function groupConsecutive(alerts: Alert[]): AlertGroup[] {
  if (alerts.length === 0) return []

  const groups: AlertGroup[] = []
  let cur: AlertGroup = {
    key: `${alerts[0].consignment_id}-${alerts[0].alert_type}`,
    first: alerts[0],
    last: alerts[0],
    count: 1,
  }

  for (let i = 1; i < alerts.length; i++) {
    const a = alerts[i]
    const key = `${a.consignment_id}-${a.alert_type}`
    if (key === cur.key) {
      cur.last = a
      cur.count++
    } else {
      groups.push(cur)
      cur = { key, first: a, last: a, count: 1 }
    }
  }
  groups.push(cur)
  return groups
}

const fmtDateTime = (iso: string) =>
  new Date(iso).toLocaleString('fr-CA', {
    month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })

export default function AlertsTable({ alerts }: Props) {
  if (alerts.length === 0) {
    return <p className="text-slate-500 text-sm">Aucune alerte.</p>
  }

  const groups = groupConsecutive(alerts)

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-slate-500 text-xs uppercase border-b border-slate-700">
            <th className="pb-2 pr-4">Période</th>
            <th className="pb-2 pr-4">Consignation</th>
            <th className="pb-2 pr-4">Type</th>
            <th className="pb-2 pr-4">Sévérité</th>
            <th className="pb-2 pr-4">Valeur</th>
            <th className="pb-2">Message</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-700/50">
          {groups.map((g) => (
            <tr key={`${g.key}-${g.first.id}`} className="hover:bg-slate-700/30 transition-colors">
              <td className="py-2 pr-4 text-slate-400 whitespace-nowrap">
                <span>{fmtDateTime(g.first.time)}</span>
                {g.count > 1 && (
                  <span className="block text-xs text-slate-600">
                    → {fmtDateTime(g.last.time)}
                    <span className="ml-1 bg-slate-700 text-slate-400 rounded px-1">×{g.count}</span>
                  </span>
                )}
              </td>
              <td className="py-2 pr-4 text-slate-300 font-medium">{g.first.consignment_id}</td>
              <td className="py-2 pr-4 text-slate-400 font-mono text-xs">{g.first.alert_type}</td>
              <td className="py-2 pr-4">
                <StatusBadge severity={g.first.severity} />
              </td>
              <td className="py-2 pr-4 text-slate-300">
                {g.last.value !== null ? g.last.value.toFixed(1) : '—'}
                {g.last.threshold !== null && (
                  <span className="text-slate-600 ml-1">/ {g.last.threshold}</span>
                )}
              </td>
              <td className="py-2 text-slate-400 text-xs">{g.last.message}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
