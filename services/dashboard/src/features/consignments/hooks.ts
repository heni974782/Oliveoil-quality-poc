import { useQuery } from '@tanstack/react-query'
import { fetchConsignments, fetchTelemetry, fetchQuality } from './api'

export function useConsignments() {
  return useQuery({
    queryKey: ['consignments'],
    queryFn: fetchConsignments,
  })
}

// hours is part of the queryKey: changing the window triggers a refetch.
export function useConsignmentDetail(id: string, hours: number) {
  const telemetry = useQuery({
    queryKey: ['telemetry', id, hours],
    queryFn: () => fetchTelemetry(id, hours),
    enabled: !!id,
  })

  const quality = useQuery({
    queryKey: ['quality', id, hours],
    queryFn: () => fetchQuality(id, hours),
    enabled: !!id,
  })

  return { telemetry, quality }
}
