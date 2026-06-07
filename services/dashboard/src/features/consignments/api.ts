import apiFetch from '../../shared/apiClient'
import type { ConsignmentSummary, TelemetryPoint, QualityPoint } from '../../shared/types'

export const fetchConsignments = () =>
  apiFetch<ConsignmentSummary[]>('/consignments/')

export const fetchTelemetry = (id: string, limit = 200) =>
  apiFetch<TelemetryPoint[]>(`/consignments/${encodeURIComponent(id)}/telemetry?limit=${limit}`)

export const fetchQuality = (id: string, limit = 200) =>
  apiFetch<QualityPoint[]>(`/consignments/${encodeURIComponent(id)}/quality?limit=${limit}`)
