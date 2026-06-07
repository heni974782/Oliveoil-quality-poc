import StatusBadge from '../../shared/components/StatusBadge'
import type { Alert } from '../../shared/types'

interface Props {
  alerts: Alert[]
}

const fmtDateTime = (iso: string) =>
  new Date(iso).toLocaleString('fr-CA', {
    month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  })

export default function AlertsTable({ alerts }: Props) {
  if (alerts.length === 0) {
    return <p className="text-slate-500 text-sm">Aucune alerte.</p>
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-slate-500 text-xs uppercase border-b border-slate-700">
            <th className="pb-2 pr-4">Horodatage</th>
            <th className="pb-2 pr-4">Consignation</th>
            <th className="pb-2 pr-4">Type</th>
            <th className="pb-2 pr-4">Sévérité</th>
            <th className="pb-2 pr-4">Valeur</th>
            <th className="pb-2">Message</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-700/50">
          {alerts.map((a) => (
            <tr key={a.id} className="hover:bg-slate-700/30 transition-colors">
              <td className="py-2 pr-4 text-slate-400 whitespace-nowrap">{fmtDateTime(a.time)}</td>
              <td className="py-2 pr-4 text-slate-300 font-medium">{a.consignment_id}</td>
              <td className="py-2 pr-4 text-slate-400 font-mono text-xs">{a.alert_type}</td>
              <td className="py-2 pr-4">
                <StatusBadge severity={a.severity} />
              </td>
              <td className="py-2 pr-4 text-slate-300">
                {a.value !== null ? a.value.toFixed(1) : '—'}
                {a.threshold !== null && (
                  <span className="text-slate-600 ml-1">/ {a.threshold}</span>
                )}
              </td>
              <td className="py-2 text-slate-400 text-xs">{a.message}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
