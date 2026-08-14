import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import { BrowserNotificationsProvider } from './BrowserNotificationsContext'
import './styles.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserNotificationsProvider>
      <App />
    </BrowserNotificationsProvider>
  </StrictMode>,
)
