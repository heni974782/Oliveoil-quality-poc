import { getToken } from '../../shared/auth'

export interface PointPayload {
  consignment_id: string
  temperature_c: number
  light_lux: number
  humidity_pct: number
  event?: string | null
}

export interface ScenarioPayload extends PointPayload {
  duration_minutes: number
  points: number
}

// Injection endpoints are proxied by Nginx at /inject/* → manual-injector.
async function postInject<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`/inject${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${getToken()}`,
    },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(`Injection échouée (${res.status}): ${detail}`)
  }
  return res.json() as Promise<T>
}

export const injectPoint = (p: PointPayload) =>
  postInject<{ published: number; topic: string }>('/point', p)

export const injectScenario = (p: ScenarioPayload) =>
  postInject<{ published: number; duration_minutes: number; topic: string }>('/scenario', p)
