import { useLiveData } from '../../shared/useLiveData'
import { useConsignments } from './hooks'
import ConsignmentCard from './ConsignmentCard'
import type { ConsignmentSummary } from '../../shared/types'

export default function ConsignmentsPage() {
  const { data: queryData, isLoading, isError } = useConsignments()
  const { data: liveData } = useLiveData()

  // Live WS data takes priority over polled REST data
  const consignments: ConsignmentSummary[] = liveData?.consignments ?? queryData ?? []

  if (isLoading && !liveData) {
    return (
      <main className="max-w-7xl mx-auto p-6">
        <p className="text-slate-400">Chargement des consignations...</p>
      </main>
    )
  }

  if (isError && !liveData) {
    return (
      <main className="max-w-7xl mx-auto p-6">
        <p className="text-red-400">Erreur de connexion à l'API. Vérifier le service.</p>
      </main>
    )
  }

  return (
    <main className="max-w-7xl mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-slate-100">Consignations</h1>
        <span className="text-slate-500 text-sm">{consignments.length} lot(s) surveillé(s)</span>
      </div>

      {consignments.length === 0 ? (
        <p className="text-slate-500">Aucune donnée de télémétrie reçue.</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {consignments.map((c) => (
            <ConsignmentCard key={c.consignment_id} consignment={c} />
          ))}
        </div>
      )}
    </main>
  )
}
