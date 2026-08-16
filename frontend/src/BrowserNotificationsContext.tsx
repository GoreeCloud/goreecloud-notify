import { createContext, type ReactNode, useContext } from 'react'
import useBrowserNotifications from './useBrowserNotifications'

type BrowserNotificationsValue = ReturnType<typeof useBrowserNotifications>

const BrowserNotificationsContext = createContext<BrowserNotificationsValue | null>(null)

export function BrowserNotificationsProvider({ children }: { children: ReactNode }) {
  const value = useBrowserNotifications()
  return (
    <BrowserNotificationsContext.Provider value={value}>
      {children}
    </BrowserNotificationsContext.Provider>
  )
}

export function useBrowserNotificationsContext(): BrowserNotificationsValue {
  const value = useContext(BrowserNotificationsContext)
  if (!value) throw new Error('BrowserNotificationsProvider is required')
  return value
}
