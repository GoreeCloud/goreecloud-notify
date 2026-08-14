import { useEffect, useRef, useState } from 'react'

export type RealtimeDelivery = {
  id: number
  notification_id: number
  source: string
  channel: string
  title: string
  body: string
  severity: 'info' | 'normal' | 'warning' | 'error' | 'critical'
  notification_created_at: string
  delivered_at: string
  expires_at: string | null
  read_at: string | null
  acknowledged_at: string | null
}

export type InboxStreamState = 'idle' | 'connecting' | 'live' | 'reconnecting'

type InboxStreamOptions = {
  enabled: boolean
  onReady: () => void
  onDelivery: (delivery: RealtimeDelivery) => void
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? ''

function parseDelivery(event: MessageEvent<string>): RealtimeDelivery | null {
  try {
    const value = JSON.parse(event.data) as Partial<RealtimeDelivery>
    if (
      typeof value.id !== 'number'
      || typeof value.notification_id !== 'number'
      || typeof value.source !== 'string'
      || typeof value.channel !== 'string'
      || typeof value.title !== 'string'
      || typeof value.body !== 'string'
      || typeof value.severity !== 'string'
      || typeof value.notification_created_at !== 'string'
      || typeof value.delivered_at !== 'string'
    ) {
      return null
    }
    return value as RealtimeDelivery
  } catch {
    return null
  }
}

export default function useInboxStream({ enabled, onReady, onDelivery }: InboxStreamOptions): InboxStreamState {
  const [state, setState] = useState<InboxStreamState>('idle')
  const onReadyRef = useRef(onReady)
  const onDeliveryRef = useRef(onDelivery)

  useEffect(() => {
    onReadyRef.current = onReady
  }, [onReady])

  useEffect(() => {
    onDeliveryRef.current = onDelivery
  }, [onDelivery])

  useEffect(() => {
    if (!enabled) {
      setState('idle')
      return
    }

    let closed = false
    setState('connecting')
    const source = new EventSource(`${apiBaseUrl}/api/v1/inbox/stream`, { withCredentials: true })

    const handleReady = () => {
      if (closed) return
      setState('live')
      onReadyRef.current()
    }

    const handleDelivery = (event: Event) => {
      if (closed || !(event instanceof MessageEvent)) return
      const delivery = parseDelivery(event as MessageEvent<string>)
      if (!delivery) return
      setState('live')
      onDeliveryRef.current(delivery)
    }

    source.addEventListener('ready', handleReady)
    source.addEventListener('inbox', handleDelivery)
    source.onerror = () => {
      if (!closed) setState('reconnecting')
    }

    return () => {
      closed = true
      source.close()
    }
  }, [enabled])

  return state
}
