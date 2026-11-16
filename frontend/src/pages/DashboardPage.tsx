import { ArrowRight } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { Avatar, ErrorState, PageHeader, Skeleton, StatusDot } from '../components/ui'
import { contactLabel, timeAgo } from '../lib/format'
import { checkLabel } from '../lib/status'
import { useConversations, useDashboardSummary, useReadiness } from '../lib/queries'
import type { CheckState } from '../types/api'

function Card({ title, children, action }: { title: string; children: ReactNode; action?: ReactNode }) {
  return (
    <section className="rounded-xl border border-line bg-surface">
      <div className="flex items-center justify-between border-b border-line px-4 py-3">
        <h2 className="text-[13px] font-medium">{title}</h2>
        {action}
      </div>
      {children}
    </section>
  )
}

function Stat({ label, value, hint, loading }: { label: string; value: ReactNode; hint?: string; loading: boolean }) {
  return (
    <div className="rounded-xl border border-line bg-surface px-4 py-3.5">
      <p className="text-[12px] text-muted">{label}</p>
      {loading ? (
        <Skeleton className="mt-2 h-7 w-16" />
      ) : (
        <p className="mt-1 text-[24px] font-semibold tracking-[-0.02em] tabular-nums">{value}</p>
      )}
      {hint && <p className="mt-0.5 text-[12px] text-faint">{hint}</p>}
    </div>
  )
}

function Stats() {
  const { data, isPending, isError, error } = useDashboardSummary()
  if (isError)
    return (
      <div className="rounded-xl border border-line bg-surface">
        <ErrorState error={error} compact />
      </div>
    )
  const integration: CheckState = data?.integration_status ?? 'not_configured'
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <Stat label="Open conversations" value={data?.open_conversations} loading={isPending} />
      <Stat label="Webhook events today" value={data?.events_today} loading={isPending} />
      <Stat label="Last event" value={timeAgo(data?.last_event_at)} loading={isPending} />
      <Stat
        label="Chatwoot"
        loading={isPending}
        value={
          <span className="flex items-center gap-2 text-[16px]">
            <StatusDot state={integration} />
            {checkLabel[integration]}
          </span>
        }
      />
    </div>
  )
}

function RecentConversations() {
  const { data, isPending, isError, error } = useConversations('open')
  return (
    <Card
      title="Open conversations"
      action={
        <Link to="/inbox" className="flex items-center gap-1 text-[12px] text-muted hover:text-ink">
          Open inbox <ArrowRight className="size-3.5" />
        </Link>
      }
    >
      {isPending ? (
        <div className="space-y-3 p-4">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-9" />
          ))}
        </div>
      ) : isError ? (
        <ErrorState error={error} compact />
      ) : data.length === 0 ? (
        <p className="p-6 text-center text-[13px] text-muted">No open conversations. Nice work.</p>
      ) : (
        <ul className="divide-y divide-line">
          {data.slice(0, 5).map((c) => (
            <li key={c.id}>
              <Link to={`/inbox/${c.id}`} className="flex items-center gap-3 px-4 py-2.5 hover:bg-surface-2">
                <Avatar name={contactLabel(c.contact)} size="sm" />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-[13px] font-medium">{contactLabel(c.contact)}</p>
                  <p className="truncate text-[12px] text-muted">{c.last_message_preview ?? 'No messages yet'}</p>
                </div>
                <span className="shrink-0 text-[12px] text-faint">{timeAgo(c.last_activity_at)}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}

function SystemHealth() {
  const { data, isPending, isError } = useReadiness()
  const rows: { name: string; detail: string; state: CheckState | 'loading' }[] = [
    {
      name: 'NEXUS backend',
      detail: 'FastAPI · /health/ready',
      state: isPending ? 'loading' : isError ? 'unreachable' : 'ok',
    },
    {
      name: 'NEXUS database',
      detail: 'PostgreSQL',
      state: isPending ? 'loading' : isError ? 'unreachable' : data.checks.database,
    },
    {
      name: 'Chatwoot',
      detail: 'REST API + webhooks',
      state: isPending ? 'loading' : isError ? 'unreachable' : data.checks.chatwoot,
    },
  ]
  return (
    <Card title="System health">
      <ul className="divide-y divide-line">
        {rows.map((r) => (
          <li key={r.name} className="flex items-center gap-3 px-4 py-2.5">
            <StatusDot state={r.state} />
            <div className="min-w-0 flex-1">
              <p className="text-[13px] font-medium">{r.name}</p>
              <p className="text-[12px] text-faint">{r.detail}</p>
            </div>
            <span className="text-[12px] text-muted">{r.state === 'loading' ? 'Checking…' : checkLabel[r.state]}</span>
          </li>
        ))}
      </ul>
    </Card>
  )
}

const flow = ['Customer', 'Chatwoot', 'NEXUS Backend', 'NEXUS Inbox', 'Agent reply', 'Chatwoot']

function MessageFlow() {
  return (
    <Card title="How a message flows">
      <ol className="flex flex-wrap items-center gap-x-1.5 gap-y-2 px-4 py-4 text-[12px]">
        {flow.map((step, i) => (
          <li key={i} className="flex items-center gap-1.5">
            <span
              className={`rounded-md border px-2 py-1 ${
                step.startsWith('NEXUS') ? 'border-transparent bg-accent-soft text-accent-ink' : 'border-line text-muted'
              }`}
            >
              {step}
            </span>
            {i < flow.length - 1 && <ArrowRight className="size-3 text-faint" />}
          </li>
        ))}
      </ol>
    </Card>
  )
}

export function DashboardPage() {
  return (
    <>
      <PageHeader title="Dashboard" subtitle="An overview of your support workspace" />
      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto flex max-w-5xl flex-col gap-4 p-4 sm:p-6">
          <Stats />
          <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
            <RecentConversations />
            <div className="flex flex-col gap-4">
              <SystemHealth />
              <MessageFlow />
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
