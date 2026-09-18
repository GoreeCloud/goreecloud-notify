import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import { BrowserNotificationsProvider } from './BrowserNotificationsContext'
import './styles.css'
import './glaze-contract.css'
import './glaze-resilience.css'

// Repository-local V1.3 source mapping. This is deliberately not a conformance claim.
document.documentElement.dataset.glazeUi = '1.3.0'
document.documentElement.dataset.glazeUiTarget = '1.3.0'
document.documentElement.dataset.glazeUiStatus = 'migration-candidate'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserNotificationsProvider>
      <App />
    </BrowserNotificationsProvider>
  </StrictMode>,
)
