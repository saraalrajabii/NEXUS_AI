import { NavLink } from 'react-router'
import { USE_MOCKS } from '../../lib/api'
import { useReadiness } from '../../lib/queries'
import { Badge, StatusDot } from '../ui'
import { navItems } from './navigation'

export function Logo() {
  return (
    <span className="flex size-7 items-center justify-center rounded-lg bg-ink">
      <svg viewBox="0 0 32 32" className="size-4" aria-hidden>
        <path
          d="M9 23V9l14 14V9"
          fill="none"
          stroke="var(--accent)"
          strokeWidth="3.4"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </span>
  )
}

function SystemStatus() {
  const { data, isPending, isError } = useReadiness()
  const state = isPending
    ? 'loading'
    : isError || data.checks.database !== 'ok'
      ? 'unreachable'
      : data.status === 'ok'
        ? 'ok'
        : 'not_configured'
  const label = isPending
    ? 'Checking…'
    : isError
      ? 'Backend offline'
      : data.checks.database !== 'ok'
        ? 'Database unavailable'
        : data.checks.chatwoot === 'not_configured'
          ? 'Chatwoot not connected'
          : data.checks.chatwoot !== 'ok'
            ? 'Chatwoot unreachable'
            : 'All systems normal'
  return (
    <div className="flex flex-col gap-1.5 px-2.5 py-2">
      {USE_MOCKS && (
        <span title="VITE_USE_MOCKS=true — not connected to the backend">
          <Badge tone="warn">Sample data mode</Badge>
        </span>
      )}
      <div className="flex items-center gap-2 text-[12px] text-muted">
        <StatusDot state={state} />
        <span className="truncate">{label}</span>
      </div>
    </div>
  )
}

export function Sidebar() {
  return (
    <aside className="hidden w-60 shrink-0 flex-col border-r border-line bg-sidebar md:flex">
      <div className="flex items-center gap-2.5 px-4 py-4">
        <Logo />
        <div className="leading-tight">
          <p className="text-[13px] font-semibold tracking-[0.08em]">NEXUS</p>
          <p className="text-[11px] text-faint">Support workspace</p>
        </div>
      </div>

      <nav aria-label="Main" className="flex flex-1 flex-col gap-0.5 px-2 py-2">
        {navItems.map(({ to, label, icon: Icon, upcoming }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `group flex items-center gap-2.5 rounded-md px-2.5 py-1.5 text-[13px] transition-colors ${
                isActive
                  ? 'bg-surface font-medium text-ink shadow-[0_0_0_1px_var(--line)]'
                  : 'text-muted hover:bg-surface-2 hover:text-ink'
              }`
            }
          >
            <Icon className="size-4 shrink-0" strokeWidth={1.75} />
            <span className="flex-1">{label}</span>
            {upcoming && <span className="text-[10px] font-medium uppercase tracking-wider text-faint">Soon</span>}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-line p-2">
        <SystemStatus />
      </div>
    </aside>
  )
}

/** Compact navigation for narrow screens (the full sidebar is hidden below 768px). */
export function MobileNav() {
  return (
    <nav aria-label="Main" className="flex items-center gap-1 overflow-x-auto border-b border-line bg-sidebar px-3 py-2 md:hidden">
      <Logo />
      {navItems.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/'}
          aria-label={label}
          className={({ isActive }) =>
            `flex shrink-0 items-center gap-1.5 rounded-md px-2.5 py-1.5 text-[13px] ${
              isActive ? 'bg-surface font-medium text-ink shadow-[0_0_0_1px_var(--line)]' : 'text-muted'
            }`
          }
        >
          <Icon className="size-4" strokeWidth={1.75} />
          <span className="max-[480px]:hidden">{label}</span>
        </NavLink>
      ))}
    </nav>
  )
}
