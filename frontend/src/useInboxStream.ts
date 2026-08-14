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

export type RealtimeInboxState = {
  latest_delivery_id: number
  total_count: number
  unread_count: number
  acknowledged_count: number
}

export type InboxStreamState = 'idle' | 'connecting' | 'live' | 'reconnecting'

type InboxStreamOptions = {
  enabled: boolean
  initialCursor: number | null
  onReady: (state: RealtimeInboxState) => void
  onState: (state: RealtimeInboxState) => void
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

function parseInboxState(event: Event): RealtimeInboxState | null {
  if (!(event instanceof MessageEvent)) return null
  try {
    const value = JSON.parse(event.data) as Partial<RealtimeInboxState>
    if (
      typeof value.latest_delivery_id !== 'number'
      || typeof value.total_count !== 'number'
      || typeof value.unread_count !== 'number'
      || typeof value.acknowledged_count !== 'number'
    ) {
      return null
    }
    if (
      value.latest_delivery_id < 0
      || value.total_count < 0
      || value.unread_count < 0
      || value.acknowledged_count < 0
      || value.unread_count > value.total_count
      || value.acknowledged_count > value.total_count
    ) {
      return null
    }
    return value as RealtimeInboxState
  } catch {
    return null
  }
}

export default function useInboxStream({
  enabled,
  initialCursor,
  onReady,
  onState,
  onDelivery,
}: InboxStreamOptions): InboxStreamState {
  const [state, setState] = useState<InboxStreamState>('idle')
  const onReadyRef = useRef(onReady)
  const onStateRef = useRef(onState)
  const onDeliveryRef = useRef(onDelivery)

  useEffect(() => {
    onReadyRef.current = onReady
  }, [onReady])

  useEffect(() => {
    onStateRef.current = onState
  }, [onState])

  useEffect(() => {
    onDeliveryRef.current = onDelivery
  }, [onDelivery])

  useEffect(() => {
    if (!enabled || initialCursor === null) {
      setState('idle')
      return
    }

    let closed = false
    let synchronized = false
    setState('connecting')
    const streamUrl = new URL(`${apiBaseUrl}/api/v1/inbox/stream`, window.location.origin)
    streamUrl.searchParams.set('after_id', String(initialCursor))
    const source = new EventSource(streamUrl.toString(), { withCredentials: true })

    const handleReady = (event: Event) => {
      if (closed) return
      const inboxState = parseInboxState(event)
      if (!inboxState) {
        synchronized = false
        setState('reconnecting')
        return
      }
      synchronized = true
      setState('live')
      onReadyRef.current(inboxState)
    }

    const handleState = (event: Event) => {
      if (closed || !synchronized) return
      const inboxState = parseInboxState(event)
      if (!inboxState) return
      setState('live')
      onStateRef.current(inboxState)
    }

    const handleDelivery = (event: Event) => {
      if (closed || !synchronized || !(event instanceof MessageEvent)) return
      const delivery = parseDelivery(event as MessageEvent<string>)
      if (!delivery) return
      setState('live')
      onDeliveryRef.current(delivery)
    }

    source.addEventListener('ready', handleReady)
    source.addEventListener('state', handleState)
    source.addEventListener('inbox', handleDelivery)
    source.onerror = () => {
      if (!closed) {
        synchronized = false
        setState('reconnecting')
      }
    }

    return () => {
      closed = true
      synchronized = false
      source.close()
    }
  }, [enabled, initialCursor])

  return state
}
