import { ArrowUp } from 'lucide-react'
import { useState, type FormEvent, type KeyboardEvent } from 'react'
import { ApiError } from '../../lib/api'
import { useSendReply } from '../../lib/queries'

export function ReplyBox({ conversationId }: { conversationId: string }) {
  const [text, setText] = useState('')
  const send = useSendReply(conversationId)
  const canSend = text.trim().length > 0 && !send.isPending

  function submit(e?: FormEvent) {
    e?.preventDefault()
    if (!canSend) return
    send.mutate(text.trim(), { onSuccess: () => setText('') })
  }

  // Enter sends, Shift+Enter adds a new line.
  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault()
      submit()
    }
  }

  return (
    <form onSubmit={submit} className="border-t border-line bg-surface p-3">
      {send.isError && (
        <p role="alert" className="mb-2 rounded-md bg-bad/10 px-3 py-2 text-[12px] text-bad">
          Reply not sent: {send.error instanceof ApiError ? send.error.message : 'unexpected error'}. Your text is kept — try again.
        </p>
      )}
      <div className="flex items-end gap-2 rounded-xl border border-line-strong bg-canvas px-3 py-2 focus-within:border-accent">
        <label htmlFor="reply" className="sr-only">
          Reply
        </label>
        <textarea
          id="reply"
          rows={2}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Write a reply…  (Enter to send, Shift+Enter for a new line)"
          className="max-h-40 min-h-10 flex-1 resize-none bg-transparent text-[13.5px] outline-none placeholder:text-faint focus-visible:outline-none"
        />
        <button
          type="submit"
          disabled={!canSend}
          aria-label="Send reply"
          className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-accent text-white transition-opacity disabled:opacity-35"
        >
          <ArrowUp className={`size-4 ${send.isPending ? 'animate-pulse' : ''}`} />
        </button>
      </div>
    </form>
  )
}
