import apiFetch from '../../shared/apiClient'
import type { Alert } from '../../shared/types'

export const fetchAlerts = (consignmentId?: string, limit = 50) => {
  const params = new URLSearchParams({ limit: String(limit) })
  if (consignmentId) params.set('consignment_id', consignmentId)
  return apiFetch<Alert[]>(`/alerts/?${params}`)
}
