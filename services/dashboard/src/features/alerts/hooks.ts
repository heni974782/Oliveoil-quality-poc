import { useQuery } from '@tanstack/react-query'
import { fetchAlerts } from './api'

export function useAlerts(consignmentId?: string) {
  return useQuery({
    queryKey: ['alerts', consignmentId ?? 'all'],
    queryFn: () => fetchAlerts(consignmentId),
  })
}
