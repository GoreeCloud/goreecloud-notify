import { useCallback, useEffect, useRef, useState } from 'react'
import type { RealtimeDelivery } from './useInboxStream'

export type BrowserNotificationPermission = NotificationPermission | 'unsupported'

const preferenceKey = 'goreecloud-notify-system-alerts'
const privateTitle = 'GoreeCloud Notify'
const privateBody = 'A new notification is available. Open Notify to view details.'

function isSupported(): boolean {
  return typeof window !== 'undefined' && 'Notification' in window
}

function savedOptIn(): boolean {
  return window.localStorage.getItem(preferenceKey) === 'enabled'
}

export default function useBrowserNotifications() {
  const [permission, setPermission] = useState<BrowserNotificationPermission>(() => (
    isSupported() ? Notification.permission : 'unsupported'
  ))
  const [enabled, setEnabled] = useState(() => (
    isSupported() && Notification.permission === 'granted' && savedOptIn()
  ))
  const [busy, setBusy] = useState(false)
  const baselineRef = useRef<number | null>(null)

  const synchronizePermission = useCallback(() => {
    if (!isSupported()) {
      setPermission('unsupported')
      setEnabled(false)
      window.localStorage.removeItem(preferenceKey)
      return
    }

    const nextPermission = Notification.permission
    setPermission(nextPermission)
    if (nextPermission !== 'granted') {
      setEnabled(false)
      window.localStorage.removeItem(preferenceKey)
      return
    }
    setEnabled(savedOptIn())
  }, [])

  useEffect(() => {
    synchronizePermission()
    window.addEventListener('focus', synchronizePermission)
    document.addEventListener('visibilitychange', synchronizePermission)
    return () => {
      window.removeEventListener('focus', synchronizePermission)
      document.removeEventListener('visibilitychange', synchronizePermission)
    }
  }, [synchronizePermission])

  const enable = useCallback(async () => {
    if (!isSupported()) return
    setBusy(true)
    try {
      const nextPermission = Notification.permission === 'default'
        ? await Notification.requestPermission()
        : Notification.permission
      setPermission(nextPermission)
      if (nextPermission === 'granted') {
        window.localStorage.setItem(preferenceKey, 'enabled')
        setEnabled(true)
      } else {
        window.localStorage.removeItem(preferenceKey)
        setEnabled(false)
      }
    } finally {
      setBusy(false)
    }
  }, [])

  const disable = useCallback(() => {
    window.localStorage.removeItem(preferenceKey)
    setEnabled(false)
    synchronizePermission()
  }, [synchronizePermission])

  const synchronizeRealtimeBaseline = useCallback((latestDeliveryId: number) => {
    baselineRef.current = latestDeliveryId
  }, [])

  const notifyDelivery = useCallback((delivery: RealtimeDelivery) => {
    const previousBaseline = baselineRef.current
    const isNew = previousBaseline !== null && delivery.id > previousBaseline
    baselineRef.current = Math.max(previousBaseline ?? delivery.id, delivery.id)

    if (!isNew) return
    if (!isSupported() || !enabled || Notification.permission !== 'granted') {
      synchronizePermission()
      return
    }
    if (document.visibilityState !== 'hidden') return

    try {
      const notification = new Notification(privateTitle, { body: privateBody })
      notification.onclick = () => {
        window.focus()
        notification.close()
      }
    } catch {
      synchronizePermission()
    }
  }, [enabled, synchronizePermission])

  return {
    permission,
    enabled,
    busy,
    enable,
    disable,
    synchronizeRealtimeBaseline,
    notifyDelivery,
  }
}
