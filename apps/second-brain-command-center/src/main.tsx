import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './styles/tokens.css'
import './styles/app.css'

// Persisted theme choice (no secrets, safe in localStorage).
const saved = localStorage.getItem('sbc_theme')
if (saved === 'light' || saved === 'dark') {
  document.documentElement.setAttribute('data-theme', saved)
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
)
