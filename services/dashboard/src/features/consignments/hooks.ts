import { useQuery } from '@tanstack/react-query'
import { fetchConsignments, fetchTelemetry, fetchQuality } from './api'

export function useConsignments() {
  return useQuery({
    queryKey: ['consignments'],
    queryFn: fetchConsignments,
  })
}

export function useConsignmentDetail(id: string) {
  const telemetry = useQuery({
    queryKey: ['telemetry', id],
    queryFn: () => fetchTelemetry(id),
    enabled: !!id,
  })

  const quality = useQuery({
    queryKey: ['quality', id],
    queryFn: () => fetchQuality(id),
    enabled: !!id,
  })

  return { telemetry, quality }
}
