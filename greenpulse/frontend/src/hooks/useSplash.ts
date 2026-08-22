/**
 * useSplash — controls the #gp-splash element injected in index.html.
 *
 * Strategy:
 *   1. Show splash instantly (already rendered in HTML before JS loads).
 *   2. Ping /health to confirm the backend is up.
 *   3. Enforce a minimum display duration (1 800 ms) so the animation
 *      completes even if the backend responds in < 100 ms.
 *   4. Update the status text while waiting.
 *   5. Add the fade-out CSS class, then remove the element from the DOM
 *      after the transition ends.
 */
import { useEffect } from 'react'

const MIN_MS = 2000   // minimum time splash is visible
const HEALTH_URL = '/health'

const PHASES = [
  { at: 0,    text: 'Initialising systems…' },
  { at: 400,  text: 'Loading asset registry…' },
  { at: 900,  text: 'Connecting to IBM watsonx.ai…' },
  { at: 1400, text: 'Starting simulation engine…' },
  { at: 1750, text: 'Ready.' },
]

function setStatus(text: string) {
  const el = document.getElementById('gp-splash-status')
  if (el) el.textContent = text
}

function dismiss() {
  const splash = document.getElementById('gp-splash')
  if (!splash) return
  splash.classList.add('gp-fade-out')
  splash.addEventListener('transitionend', () => splash.remove(), { once: true })
  // Safety net: remove after 600 ms regardless of transitionend
  setTimeout(() => splash.remove(), 600)
}

export function useSplash() {
  useEffect(() => {
    // Schedule status text changes
    const timers: ReturnType<typeof setTimeout>[] = []
    PHASES.forEach(({ at, text }) => {
      timers.push(setTimeout(() => setStatus(text), at))
    })

    // Ping backend health endpoint
    const healthCheck = fetch(HEALTH_URL, { signal: AbortSignal.timeout(5000) })
      .then(() => true)
      .catch(() => false)

    // Wait for both: minimum duration AND health check
    Promise.all([
      healthCheck,
      new Promise<void>(resolve => setTimeout(resolve, MIN_MS)),
    ]).then(() => {
      timers.forEach(clearTimeout)
      setStatus('Ready.')
      // Small pause so "Ready." is visible before fade
      setTimeout(dismiss, 220)
    })

    return () => {
      timers.forEach(clearTimeout)
    }
  }, [])   // runs once on mount
}
