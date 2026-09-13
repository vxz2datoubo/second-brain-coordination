/**
 * Phase 2A Dispatch Intent — live UI proof.
 *
 * Verifies, against the running dev server + BFF:
 *   1. The 派发 button exists and composes a READ-ONLY intent.
 *   2. The plain-language answer renders (not raw JSON only).
 *   3. The authorization checklist renders one row per required input.
 *   4. No process is started (starts_any_process === false).
 *   5. Zero console errors.
 *
 * Usage: node scripts/verify-dispatch.mjs
 */
import { chromium } from 'playwright-core'
import { mkdirSync } from 'node:fs'

const OUT = 'evidence/screenshots'
mkdirSync(OUT, { recursive: true })

const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe'
const BASE = 'http://127.0.0.1:5173'

const browser = await chromium.launch({ executablePath: CHROME, headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } })

const errors = []
page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()) })
page.on('pageerror', (e) => errors.push(`pageerror: ${e.message}`))

// Count any /commands/ request the panel makes.
const commandCalls = []
page.on('request', (r) => {
  if (r.url().includes('/api/commands/')) commandCalls.push(`${r.method()} ${r.url()}`)
})

let pass = 0
let fail = 0
const check = (name, ok, extra = '') => {
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${extra ? ' — ' + extra : ''}`)
  ok ? pass++ : fail++
}

await page.goto(BASE + '/control-tower', { waitUntil: 'networkidle' })
await page.waitForTimeout(1500)

// 1. Panel + button exist
const card = page.locator('.card', { has: page.getByText('派发 · Dispatch') }).first()
check('dispatch panel renders', await card.count() > 0)

const button = page.locator('button.btn.btn-primary', { hasText: /^派发$/ }).first()
check('dispatch button renders', await button.count() > 0)

// 2. Select a task, then press 派发
const select = card.locator('select').first()
const optionCount = await select.locator('option').count()
check('task selector populated', optionCount > 1, `${optionCount - 1} tasks`)

await select.selectOption({ index: 1 })
await page.waitForTimeout(300)
await button.click()
await page.waitForTimeout(2000)

// 3. Plain-language answer present
const plain = card.locator('.plain-answer').first()
check('plain-language answer renders', await plain.count() > 0)
if (await plain.count()) {
  const txt = (await plain.innerText()).trim()
  check('plain answer is human-readable', txt.length > 8, txt.slice(0, 60))
}

// 4. Authorization checklist present
const rows = card.locator('.auth-row')
const rowCount = await rows.count()
check('authorization checklist renders', rowCount >= 9, `${rowCount} rows`)
check('checklist marks missing inputs', await card.locator('.auth-row.auth-miss').count() > 0,
  `${await card.locator('.auth-row.auth-miss').count()} missing`)

// 5. The "no process started" guarantee is visible
const body = await card.innerText()
check('UI states no process launched', body.includes('未启动任何进程'))

// 6. Every command call went to dispatch-intent only (never /start)
check('only dispatch-intent was called', commandCalls.every((c) => c.includes('dispatch-intent')),
  commandCalls.join(' | ') || 'none')
check('start endpoint never called', !commandCalls.some((c) => c.includes('/api/commands/start')))

// 7. Console clean
check('zero console errors', errors.length === 0, errors.slice(0, 2).join(' | '))

await page.screenshot({ path: `${OUT}/10-dispatch-intent.png`, fullPage: true })
console.log(`\nscreenshot: ${OUT}/10-dispatch-intent.png`)

// Also prove the start endpoint still fails closed (HTTP 501).
const startStatus = await page.evaluate(async () => {
  const r = await fetch('/api/commands/start', { method: 'POST' })
  return r.status
})
check('start endpoint still 501 fail-closed', startStatus === 501, `HTTP ${startStatus}`)

await browser.close()

console.log(`\n=== ${pass} passed, ${fail} failed ===`)
process.exit(fail === 0 ? 0 : 1)
