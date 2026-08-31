import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import { BrowserNotificationsProvider } from './BrowserNotificationsContext'
import './styles.css'
import './glaze-contract.css'
import './glaze-resilience.css'

// Source-level consumer metadata. Adoption Candidate is deliberately distinct
// from application-specific rendered/native acceptance and production conformance.
document.documentElement.dataset.glazeUi = '2.1.0'
document.documentElement.dataset.glazeUiTarget = '2.1.0'
document.documentElement.dataset.glazeUiStatus = 'adoption-candidate'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserNotificationsProvider>
      <App />
    </BrowserNotificationsProvider>
  </StrictMode>,
)
