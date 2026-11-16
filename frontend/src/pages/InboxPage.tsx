import { ArrowLeft, MessagesSquare } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router'
import { Avatar, Badge, PageHeader } from '../components/ui'
import { ConversationList } from '../features/inbox/ConversationList'
import { filters, type InboxFilter } from '../features/inbox/filters'
import { MessageThread } from '../features/inbox/MessageThread'
import { ReplyBox } from '../features/inbox/ReplyBox'
import { contactLabel } from '../lib/format'
import { useConversation } from '../lib/queries'

function ConversationHeader({ conversationId }: { conversationId: string }) {
  const { data: c } = useConversation(conversationId)
  return (
    <div className="flex items-center gap-3 border-b border-line bg-surface px-4 py-3">
      <Link to="/inbox" className="rounded-md p-1 text-muted hover:bg-surface-2 lg:hidden" aria-label="Back to conversations">
        <ArrowLeft className="size-4" />
      </Link>
      <Avatar name={c ? contactLabel(c.contact) : null} />
      <div className="min-w-0 flex-1">
        <p className="truncate text-[13px] font-medium">{c ? contactLabel(c.contact) : 'Conversation'}</p>
        {c?.contact.email && <p className="truncate text-[12px] text-faint">{c.contact.email}</p>}
      </div>
      {c && <Badge tone={c.status === 'open' ? 'accent' : 'neutral'}>{c.status}</Badge>}
    </div>
  )
}

export function InboxPage() {
  const { conversationId } = useParams()
  const [filter, setFilter] = useState<InboxFilter>('open')

  return (
    <>
      <PageHeader title="Inbox" subtitle="Conversations from every connected channel" />
      <div className="flex min-h-0 flex-1">
        {/* Left: conversation list (hidden on small screens while a conversation is open) */}
        <section
          aria-label="Conversations"
          className={`${conversationId ? 'hidden lg:flex' : 'flex'} w-full flex-col border-r border-line bg-surface lg:w-80 lg:shrink-0`}
        >
          <div role="tablist" aria-label="Filter conversations" className="flex gap-1 border-b border-line p-2">
            {filters.map((f) => (
              <button
                key={f.value}
                role="tab"
                aria-selected={filter === f.value}
                onClick={() => setFilter(f.value)}
                className={`rounded-md px-2.5 py-1 text-[12px] font-medium transition-colors ${
                  filter === f.value ? 'bg-surface-2 text-ink' : 'text-muted hover:text-ink'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto">
            <ConversationList filter={filter} />
          </div>
        </section>

        {/* Right: the selected conversation */}
        <section aria-label="Conversation" className={`${conversationId ? 'flex' : 'hidden lg:flex'} min-w-0 flex-1 flex-col`}>
          {conversationId ? (
            <>
              <ConversationHeader conversationId={conversationId} />
              <div className="min-h-0 flex-1 overflow-y-auto">
                <MessageThread conversationId={conversationId} />
              </div>
              <ReplyBox key={conversationId} conversationId={conversationId} />
            </>
          ) : (
            <div className="flex flex-1 flex-col items-center justify-center gap-3 p-10 text-center">
              <span className="flex size-10 items-center justify-center rounded-xl border border-line bg-surface text-muted">
                <MessagesSquare className="size-5" />
              </span>
              <p className="font-medium">Select a conversation</p>
              <p className="max-w-xs text-[13px] text-muted">
                Customer messages from Chatwoot appear on the left within a few seconds.
              </p>
            </div>
          )}
        </section>
      </div>
    </>
  )
}
