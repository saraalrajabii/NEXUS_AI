// Small shared building blocks used across pages.
import type { ReactNode } from 'react'
import { AlertTriangle, Database, PlugZap, WifiOff } from 'lucide-react'
import { ApiError } from '../lib/api'
import type { CheckState } from '../types/api'
import { initials } from '../lib/format'

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <header className="flex items-center justify-between gap-4 border-b border-line px-6 py-4">
      <div className="min-w-0">
        <h1 className="text-[15px] font-semibold tracking-[-0.01em]">{title}</h1>
        {subtitle && <p className="mt-0.5 truncate text-[13px] text-muted">{subtitle}</p>}
      </div>
      {actions}
    </header>
  )
}

const dotColor: Record<CheckState | 'loading', string> = {
  ok: 'bg-ok',
  not_configured: 'bg-warn',
  unreachable: 'bg-bad',
  error: 'bg-bad',
  loading: 'bg-faint animate-pulse',
}

export function StatusDot({ state }: { state: CheckState | 'loading' }) {
  return <span aria-hidden className={`inline-block size-2 shrink-0 rounded-full ${dotColor[state]}`} />
}

export function Avatar({ name, size = 'md' }: { name: string | null | undefined; size?: 'sm' | 'md' }) {
  const s = size === 'sm' ? 'size-6 text-[10px]' : 'size-8 text-[11px]'
  return (
    <span
      aria-hidden
      className={`${s} inline-flex shrink-0 items-center justify-center rounded-full bg-accent-soft font-semibold text-accent-ink`}
    >
      {initials(name)}
    </span>
  )
}

export function Badge({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'neutral' | 'accent' | 'warn' }) {
  const tones = {
    neutral: 'border-line text-muted',
    accent: 'border-transparent bg-accent-soft text-accent-ink',
    warn: 'border-transparent bg-warn/15 text-warn',
  }
  return (
    <span className={`inline-flex items-center rounded-md border px-1.5 py-px text-[11px] font-medium ${tones[tone]}`}>
      {children}
    </span>
  )
}

export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`animate-pulse rounded-md bg-surface-2 ${className}`} />
}

/** Turns any API error into a clear, beginner-friendly explanation with a next step. */
export function ErrorState({ error, compact = false }: { error: unknown; compact?: boolean }) {
  const code = error instanceof ApiError ? error.code : 'UNKNOWN'
  const content =
    code === 'BACKEND_UNREACHABLE'
      ? {
          icon: WifiOff,
          title: 'Backend not reachable',
          text: 'The NEXUS backend is not running yet. Start it with docker compose (Milestone 3), or set VITE_USE_MOCKS=true to preview with sample data.',
        }
      : code === 'DATABASE_UNAVAILABLE'
        ? {
            icon: Database,
            title: 'Database not reachable',
            text: 'The backend is running but cannot reach the NEXUS database. Check it with: docker compose ps',
          }
        : code === 'CHATWOOT_NOT_CONFIGURED'
        ? {
            icon: PlugZap,
            title: 'Chatwoot is not connected',
            text: 'Add the Chatwoot URL, account ID and access token to the backend .env file, then restart the backend.',
          }
        : {
            icon: AlertTriangle,
            title: 'Something went wrong',
            text: error instanceof Error ? error.message : 'Unexpected error.',
          }
  const Icon = content.icon
  return (
    <div className={`flex flex-col items-center text-center ${compact ? 'gap-2 p-6' : 'gap-3 p-10'}`}>
      <span className="flex size-9 items-center justify-center rounded-lg border border-line bg-surface text-muted">
        <Icon className="size-4" />
      </span>
      <div>
        <p className="font-medium">{content.title}</p>
        <p className="mx-auto mt-1 max-w-sm text-[13px] leading-relaxed text-muted">{content.text}</p>
        {code !== 'UNKNOWN' && <p className="mt-2 font-mono text-[11px] text-faint">{code}</p>}
      </div>
    </div>
  )
}
