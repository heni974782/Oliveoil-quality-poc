export interface ConsignmentSummary {
  consignment_id: string
  quality_score: number | null
  temperature_c: number | null
  light_lux: number | null
  humidity_pct: number | null
  latest_time: string | null
  active_alerts: number
}

export interface TelemetryPoint {
  time: string
  temperature_c: number
  light_lux: number
  humidity_pct: number
  event: string | null
}

export interface QualityPoint {
  time: string
  quality_score: number
  degree_hours: number
  lux_hours: number
}

export interface Alert {
  id: number
  time: string
  consignment_id: string
  alert_type: string
  severity: 'warning' | 'critical'
  value: number | null
  threshold: number | null
  message: string
}

export interface LivePayload {
  consignments: ConsignmentSummary[]
  recent_alerts: Alert[]
}
