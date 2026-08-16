import { useCallback, useEffect, useRef, useState } from 'react'
import { readLocalPreference, removeLocalPreference, writeLocalPreference } from './browserStorage'
import type { RealtimeDelivery } from './useInboxStream'

export type BrowserNotificationPermission = NotificationPermission | 'unsupported'

const preferenceKey = 'goreecloud-notify-system-alerts'
const privateTitle = 'GoreeCloud Notify'
const privateBody = 'A new notification is available. Open Notify to view details.'

function isSupported(): boolean {
  return typeof window !== 'undefined' && 'Notification' in window
}

function savedOptIn(): boolean {
  return readLocalPreference(preferenceKey) === 'enabled'
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
  const enabledRef = useRef(enabled)
  const volatileOptInRef = useRef(false)

  const updateEnabled = useCallback((nextEnabled: boolean) => {
    enabledRef.current = nextEnabled
    setEnabled(nextEnabled)
  }, [])

  const synchronizePermission = useCallback(() => {
    if (!isSupported()) {
      setPermission('unsupported')
      updateEnabled(false)
      volatileOptInRef.current = false
      removeLocalPreference(preferenceKey)
      return
    }

    const nextPermission = Notification.permission
    setPermission(nextPermission)
    if (nextPermission !== 'granted') {
      updateEnabled(false)
      volatileOptInRef.current = false
      removeLocalPreference(preferenceKey)
      return
    }
    updateEnabled(volatileOptInRef.current || savedOptIn())
  }, [updateEnabled])

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
        const persisted = writeLocalPreference(preferenceKey, 'enabled')
        volatileOptInRef.current = !persisted
        updateEnabled(true)
      } else {
        volatileOptInRef.current = false
        removeLocalPreference(preferenceKey)
        updateEnabled(false)
      }
    } finally {
      setBusy(false)
    }
  }, [updateEnabled])

  const disable = useCallback(() => {
    volatileOptInRef.current = false
    removeLocalPreference(preferenceKey)
    updateEnabled(false)
    synchronizePermission()
  }, [synchronizePermission, updateEnabled])

  const synchronizeRealtimeBaseline = useCallback((latestDeliveryId: number) => {
    baselineRef.current = latestDeliveryId
  }, [])

  const notifyDelivery = useCallback((delivery: RealtimeDelivery) => {
    const previousBaseline = baselineRef.current
    const isNew = previousBaseline !== null && delivery.id > previousBaseline
    baselineRef.current = Math.max(previousBaseline ?? delivery.id, delivery.id)

    if (!isNew) return
    if (!isSupported() || !enabledRef.current || Notification.permission !== 'granted') {
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
  }, [synchronizePermission])

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
