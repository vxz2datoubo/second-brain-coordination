/**
 * Inline SVG icons — NO emoji, NO external icon lib (per project iron rule).
 * All icons are 24x24 viewBox, currentColor stroke.
 */
import type { SVGProps } from 'react'

type P = SVGProps<SVGSVGElement> & { size?: number }

function base({ size = 20, ...rest }: P) {
  return {
    width: size, height: size, viewBox: '0 0 24 24', fill: 'none',
    stroke: 'currentColor', strokeWidth: 1.7, strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const, 'aria-hidden': true as const, ...rest,
  }
}

export const IconBrain = (p: P) => (
  <svg {...base(p)}>
    <path d="M9 3a3 3 0 0 0-3 3 3 3 0 0 0-2 5.2A3 3 0 0 0 6 17a3 3 0 0 0 3 3h1V3H9Z" />
    <path d="M15 3a3 3 0 0 1 3 3 3 3 0 0 1 2 5.2A3 3 0 0 1 18 17a3 3 0 0 1-3 3h-1V3h1Z" />
  </svg>
)
export const IconChart = (p: P) => (
  <svg {...base(p)}>
    <path d="M3 3v18h18" /><path d="m7 14 3-4 3 3 4-6" />
  </svg>
)
export const IconFilm = (p: P) => (
  <svg {...base(p)}>
    <rect x="3" y="4" width="18" height="16" rx="2" />
    <path d="M7 4v16M17 4v16M3 9h4M3 15h4M17 9h4M17 15h4" />
  </svg>
)
export const IconCamera = (p: P) => (
  <svg {...base(p)}>
    <path d="M3 7h4l2-2h6l2 2h4v12H3z" /><circle cx="12" cy="13" r="3.5" />
  </svg>
)
export const IconHome = (p: P) => (
  <svg {...base(p)}><path d="M3 10 12 3l9 7v11h-6v-7H9v7H3z" /></svg>
)
export const IconGrid = (p: P) => (
  <svg {...base(p)}><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></svg>
)
export const IconTower = (p: P) => (
  <svg {...base(p)}><path d="M12 3v18M6 21h12M5 7h14l-3 10H8L5 7Z" /><circle cx="12" cy="4" r="1" /></svg>
)
export const IconTask = (p: P) => (
  <svg {...base(p)}><path d="M9 11l3 3L22 4" /><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" /></svg>
)
export const IconAgent = (p: P) => (
  <svg {...base(p)}><circle cx="12" cy="8" r="4" /><path d="M4 21a8 8 0 0 1 16 0" /></svg>
)
export const IconHealth = (p: P) => (
  <svg {...base(p)}><path d="M3 12h4l2-5 4 10 2-5h6" /></svg>
)
export const IconRefresh = (p: P) => (
  <svg {...base(p)}><path d="M21 12a9 9 0 1 1-3-6.7L21 8" /><path d="M21 3v5h-5" /></svg>
)
export const IconSource = (p: P) => (
  <svg {...base(p)}><path d="M14 3v5h5" /><path d="M6 3h8l5 5v13H6z" /><path d="M9 13h6M9 17h4" /></svg>
)
export const IconWarn = (p: P) => (
  <svg {...base(p)}><path d="M12 3 2 20h20L12 3Z" /><path d="M12 9v5M12 17.5v.5" /></svg>
)
export const IconShield = (p: P) => (
  <svg {...base(p)}><path d="M12 3 5 6v5c0 5 3 8 7 10 4-2 7-5 7-10V6l-7-3Z" /></svg>
)
export const IconChevron = (p: P) => (
  <svg {...base(p)}><path d="m9 6 6 6-6 6" /></svg>
)
export const IconDot = (p: P) => (
  <svg {...base(p)}><circle cx="12" cy="12" r="4" fill="currentColor" stroke="none" /></svg>
)
export const IconClock = (p: P) => (
  <svg {...base(p)}><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg>
)
export const IconGit = (p: P) => (
  <svg {...base(p)}><circle cx="6" cy="6" r="2.5" /><circle cx="6" cy="18" r="2.5" /><circle cx="18" cy="12" r="2.5" /><path d="M6 8.5v7M8.5 6h5a3 3 0 0 1 3 3v.5M8.5 18H13a3 3 0 0 0 3-3v-.5" /></svg>
)

export const ICONS: Record<string, (p: P) => JSX.Element> = {
  brain: IconBrain, chart: IconChart, film: IconFilm, camera: IconCamera,
}
