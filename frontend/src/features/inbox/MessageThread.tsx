import { useEffect, useRef } from 'react'
import { ErrorState, Skeleton } from '../../components/ui'
import { clockTime } from '../../lib/format'
import { useMessages } from '../../lib/queries'

export function MessageThread({ conversationId }: { conversationId: string }) {
  const { data, isPending, isError, error } = useMessages(conversationId)
  const bottom = useRef<HTMLDivElement>(null)

  // Keep the newest message in view when messages arrive.
  useEffect(() => {
    bottom.current?.scrollIntoView({ block: 'end' })
  }, [data?.length, conversationId])

  if (isPending)
    return (
      <div className="space-y-3 p-6">
        <Skeleton className="h-10 w-2/3" />
        <Skeleton className="ml-auto h-10 w-1/2" />
        <Skeleton className="h-10 w-3/5" />
      </div>
    )
  if (isError) return <ErrorState error={error} />
  if (data.length === 0) return <p className="p-10 text-center text-[13px] text-muted">No messages yet.</p>

  return (
    <div className="flex flex-col gap-3 px-4 py-6 sm:px-6">
      {data.map((m) => {
        const out = m.direction === 'outbound'
        return (
          <div key={m.id} className={`flex flex-col ${out ? 'items-end' : 'items-start'}`}>
            <div
              className={`max-w-[min(34rem,85%)] whitespace-pre-wrap break-words rounded-2xl px-3.5 py-2 text-[13.5px] leading-relaxed ${
                out ? 'rounded-br-md bg-bubble-out text-white' : 'rounded-bl-md bg-bubble-in'
              }`}
            >
              {m.body}
            </div>
            <p className="mt-1 px-1 text-[11px] text-faint">
              {m.author_name ?? (out ? 'Agent' : 'Customer')} · {clockTime(m.created_at)}
              {m.delivery_status === 'failed' && <span className="text-bad"> · Failed to send</span>}
            </p>
          </div>
        )
      })}
      <div ref={bottom} />
    </div>
  )
}
