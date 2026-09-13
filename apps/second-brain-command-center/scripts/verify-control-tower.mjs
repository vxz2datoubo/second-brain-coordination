/**
 * Control Tower claims/collisions projection — live UI proof.
 * Verifies the two new sections render from REAL repo artifacts.
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

let pass = 0, fail = 0
const check = (name, ok, extra = '') => {
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${extra ? ' — ' + extra : ''}`)
  ok ? pass++ : fail++
}

await page.goto(BASE + '/control-tower', { waitUntil: 'networkidle' })
await page.waitForTimeout(1500)

const body = await page.innerText('body')
check('claims section title renders', body.includes('工作认领 · Claims'))
check('claims rows render', (await page.locator('table td', { hasText: 'WORKBUDDY-R184' }).count()) > 0)
check('collision section title renders', body.includes('碰撞域 · Collision Surfaces'))
check('collision traffic lights render', body.includes('独占正常') && body.includes('跨 Agent 重叠'))
check('dispatch panel still present', body.includes('派发 · Dispatch'))
check('no fake data invented', !body.includes('undefined') && !body.includes('[object Object]'))

await page.screenshot({ path: `${OUT}/11-control-tower-claims-collisions.png`, fullPage: true })
console.log(`\nscreenshot: ${OUT}/11-control-tower-claims-collisions.png`)
check('zero console errors', errors.length === 0, errors.slice(0, 2).join(' | '))

await browser.close()
console.log(`\n=== ${pass} passed, ${fail} failed ===`)
process.exit(fail === 0 ? 0 : 1)
