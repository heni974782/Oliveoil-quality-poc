import { useEffect, useRef, useState } from 'react'
import { WS_TOKEN } from './apiClient'
import type { LivePayload } from './types'

// WebSocket URL: same host, /api/ws/live (proxied by Nginx / Vite dev server)
function buildWsUrl(): string {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const host = window.location.host
  return `${proto}://${host}/api/ws/live?token=${encodeURIComponent(WS_TOKEN)}`
}

export interface LiveDataState {
  data: LivePayload | null
  connected: boolean
}

export function useLiveData(): LiveDataState {
  const [state, setState] = useState<LiveDataState>({ data: null, connected: false })
  const wsRef = useRef<WebSocket | null>(null)
  const retryRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    let unmounted = false

    function connect() {
      if (unmounted) return
      const ws = new WebSocket(buildWsUrl())
      wsRef.current = ws

      ws.onopen = () => {
        if (!unmounted) setState((s) => ({ ...s, connected: true }))
      }

      ws.onmessage = (evt) => {
        try {
          const payload: LivePayload = JSON.parse(evt.data)
          if (!unmounted) setState({ data: payload, connected: true })
        } catch {
          // malformed frame — ignore
        }
      }

      ws.onerror = () => {
        ws.close()
      }

      ws.onclose = () => {
        if (!unmounted) {
          setState((s) => ({ ...s, connected: false }))
          // Reconnect after 5 s
          retryRef.current = setTimeout(connect, 5_000)
        }
      }
    }

    connect()

    return () => {
      unmounted = true
      if (retryRef.current) clearTimeout(retryRef.current)
      wsRef.current?.close()
    }
  }, [])

  return state
}
