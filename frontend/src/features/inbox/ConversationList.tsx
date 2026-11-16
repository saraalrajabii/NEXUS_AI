import { NavLink } from 'react-router'
import { Avatar, ErrorState, Skeleton } from '../../components/ui'
import { contactLabel, timeAgo } from '../../lib/format'
import { useConversations } from '../../lib/queries'
import type { InboxFilter } from './filters'

export function ConversationList({ filter }: { filter: InboxFilter }) {
  const { data, isPending, isError, error } = useConversations(filter === 'all' ? undefined : filter)

  if (isPending)
    return (
      <div className="space-y-2 p-3">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-14" />
        ))}
      </div>
    )
  if (isError) return <ErrorState error={error} compact />
  if (data.length === 0)
    return <p className="p-6 text-center text-[13px] text-muted">No {filter === 'all' ? '' : filter} conversations.</p>

  return (
    <ul className="flex flex-col gap-px p-2">
      {data.map((c) => (
        <li key={c.id}>
          <NavLink
            to={`/inbox/${c.id}`}
            className={({ isActive }) =>
              `flex gap-3 rounded-lg px-3 py-2.5 transition-colors ${isActive ? 'bg-accent-soft' : 'hover:bg-surface-2'}`
            }
          >
            <Avatar name={contactLabel(c.contact)} />
            <div className="min-w-0 flex-1">
              <div className="flex items-baseline gap-2">
                <p className="flex-1 truncate text-[13px] font-medium">{contactLabel(c.contact)}</p>
                <span className="shrink-0 text-[11px] text-faint">{timeAgo(c.last_activity_at)}</span>
              </div>
              <p className="mt-0.5 truncate text-[12px] text-muted">{c.last_message_preview ?? 'No messages yet'}</p>
            </div>
          </NavLink>
        </li>
      ))}
    </ul>
  )
}
