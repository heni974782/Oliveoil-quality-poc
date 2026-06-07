import apiFetch from '../../shared/apiClient'
import type { ConsignmentSummary, TelemetryPoint, QualityPoint } from '../../shared/types'

export const fetchConsignments = () =>
  apiFetch<ConsignmentSummary[]>('/consignments/')

export const fetchTelemetry = (id: string, hours = 24) =>
  apiFetch<TelemetryPoint[]>(`/consignments/${encodeURIComponent(id)}/telemetry?hours=${hours}`)

export const fetchQuality = (id: string, hours = 24) =>
  apiFetch<QualityPoint[]>(`/consignments/${encodeURIComponent(id)}/quality?hours=${hours}`)
