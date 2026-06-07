// Base URL proxied through Nginx in production, through Vite dev server locally.
const BASE = '/api'
const TOKEN = import.meta.env.VITE_API_TOKEN ?? ''

export const WS_TOKEN = TOKEN

async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { Authorization: `Bearer ${TOKEN}` },
  })
  if (!res.ok) throw new Error(`API error ${res.status} on ${path}`)
  return res.json() as Promise<T>
}

export default apiFetch
