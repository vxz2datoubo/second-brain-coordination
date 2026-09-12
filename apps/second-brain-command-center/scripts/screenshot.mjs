/**
 * Evidence screenshot runner — captures real browser proof for each page.
 * Usage: node scripts/screenshot.mjs
 * Requires the dev server (5173) + BFF (8788) to be running.
 */
import { chromium } from 'playwright-core'
import { mkdirSync } from 'node:fs'

const OUT = 'evidence/screenshots'
mkdirSync(OUT, { recursive: true })

const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe'
const BASE = 'http://127.0.0.1:5173'

const shots = [
  { path: '/', name: '01-home', wait: 2600 },
  { path: '/projects/TRADING_SYSTEM', name: '02-project-trading', wait: 2200 },
  { path: '/projects/SECOND_BRAIN', name: '03-project-second-brain', wait: 2000 },
  { path: '/control-tower', name: '04-control-tower', wait: 2000 },
  { path: '/tasks', name: '05-tasks', wait: 2000 },
  { path: '/agents', name: '06-agents', wait: 1800 },
  { path: '/health', name: '07-health', wait: 1800 },
]

const browser = await chromium.launch({ executablePath: CHROME, headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })

const errors = []
page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()) })
page.on('pageerror', (e) => errors.push(`pageerror: ${e.message}`))

for (const s of shots) {
  await page.goto(BASE + s.path, { waitUntil: 'networkidle' })
  await page.waitForTimeout(s.wait)
  await page.screenshot({ path: `${OUT}/${s.name}.png`, fullPage: true })
  console.log(`captured ${s.name} (${s.path})`)
}

// mobile viewport proof
const mobile = await browser.newPage({ viewport: { width: 390, height: 844 } })
await mobile.goto(BASE + '/', { waitUntil: 'networkidle' })
await mobile.waitForTimeout(2000)
await mobile.screenshot({ path: `${OUT}/08-mobile-home.png`, fullPage: true })
console.log('captured 08-mobile-home (390px)')

await browser.close()
console.log('\nCONSOLE ERRORS:', errors.length)
errors.slice(0, 20).forEach((e) => console.log('  -', e))
