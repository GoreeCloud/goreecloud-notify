import type { BrowserNotificationPermission } from './useBrowserNotifications'
import './browser-notifications.css'

type BrowserNotificationSettingsProps = {
  permission: BrowserNotificationPermission
  enabled: boolean
  busy: boolean
  onEnable: () => Promise<void>
  onDisable: () => void
}

function permissionCopy(permission: BrowserNotificationPermission, enabled: boolean): string {
  if (permission === 'unsupported') {
    return 'System alerts are unavailable in this browser. The protected Notify inbox remains fully available.'
  }
  if (permission === 'denied') {
    return 'This browser has blocked system alerts for Notify. Change the site permission in your browser before enabling them here.'
  }
  if (enabled) {
    return 'Enabled for this browser. System alerts use generic redacted text and appear only while Notify is open in a hidden tab or window.'
  }
  if (permission === 'granted') {
    return 'Browser permission is granted, but GoreeCloud system alerts are off for this browser.'
  }
  return 'Off by default. Notify will ask for browser permission only after you choose to enable system alerts.'
}

function permissionSummary(permission: BrowserNotificationPermission, enabled: boolean): string {
  if (permission === 'unsupported') return 'Unavailable in this browser'
  if (permission === 'denied') return 'Blocked by browser'
  if (enabled) return 'Enabled with privacy-preserving content'
  if (permission === 'granted') return 'Browser permission granted · alerts off'
  return 'Off by default'
}

export default function BrowserNotificationSettings({
  permission,
  enabled,
  busy,
  onEnable,
  onDisable,
}: BrowserNotificationSettingsProps) {
  const unavailable = permission === 'unsupported' || permission === 'denied'

  return (
    <details className="browser-notification-panel">
      <summary>
        <span>
          <strong>System alerts</strong>
          <small>{permissionSummary(permission, enabled)}</small>
        </span>
        <span className="browser-notification-summary-action">Manage</span>
      </summary>

      <div className="browser-notification-content">
        <p>{permissionCopy(permission, enabled)}</p>
        <div className="browser-notification-privacy-note">
          <strong>Privacy default</strong>
          <span>
            Operating-system alerts do not include the notification title, body, source, channel, account name, or other Delivery details. Open the authenticated Notify inbox to view the event.
          </span>
        </div>

        <div className="browser-notification-actions">
          {enabled ? (
            <button type="button" className="secondary-button" onClick={onDisable} disabled={busy}>
              Disable system alerts
            </button>
          ) : (
            <button
              type="button"
              className="secondary-button"
              onClick={() => void onEnable()}
              disabled={busy || unavailable}
            >
              {busy ? 'Requesting permission…' : 'Enable system alerts'}
            </button>
          )}
          <span className="browser-notification-state" role="status" aria-live="polite">
            {permission === 'unsupported'
              ? 'Unsupported'
              : permission === 'denied'
                ? 'Permission blocked'
                : enabled
                  ? 'Enabled locally'
                  : permission === 'granted' ? 'Permission granted · app alerts off' : 'Permission not requested'}
          </span>
        </div>
      </div>
    </details>
  )
}
