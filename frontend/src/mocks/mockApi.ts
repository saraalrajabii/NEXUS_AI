// Sample data for working on the layout before the backend exists (VITE_USE_MOCKS=true).
// Clearly fake on purpose: names come from a "Demo" company and the UI shows a "Sample data" badge.
import type { Conversation, DashboardSummary, Message, ReadinessResponse } from '../types/api'

const minutesAgo = (m: number) => new Date(Date.now() - m * 60_000).toISOString()

const conversations: Conversation[] = [
  {
    id: 'demo-1',
    channel: 'api',
    contact: { name: 'Lina Haddad', email: 'lina@demo.example' },
    status: 'open',
    last_message_preview: 'Hi! My order #4821 still shows as processing.',
    last_activity_at: minutesAgo(2),
  },
  {
    id: 'demo-2',
    channel: 'api',
    contact: { name: 'Omar Khalil', email: 'omar@demo.example' },
    status: 'open',
    last_message_preview: 'Can I change the delivery address?',
    last_activity_at: minutesAgo(18),
  },
  {
    id: 'demo-3',
    channel: 'web',
    contact: { name: null, email: 'visitor-3912@demo.example' },
    status: 'pending',
    last_message_preview: 'Do you ship to Jordan?',
    last_activity_at: minutesAgo(64),
  },
  {
    id: 'demo-4',
    channel: 'api',
    contact: { name: 'Noor Aziz', email: 'noor@demo.example' },
    status: 'resolved',
    last_message_preview: 'Perfect, thank you!',
    last_activity_at: minutesAgo(60 * 26),
  },
]

const messages: Record<string, Message[]> = {
  'demo-1': [
    {
      id: 'm1',
      direction: 'inbound',
      author_name: 'Lina Haddad',
      body: 'Hi! My order #4821 still shows as processing.',
      created_at: minutesAgo(3),
      delivery_status: 'delivered',
    },
    {
      id: 'm2',
      direction: 'inbound',
      author_name: 'Lina Haddad',
      body: 'It has been 4 days. Is something wrong?',
      created_at: minutesAgo(2),
      delivery_status: 'delivered',
    },
  ],
  'demo-2': [
    {
      id: 'm3',
      direction: 'inbound',
      author_name: 'Omar Khalil',
      body: 'Can I change the delivery address?',
      created_at: minutesAgo(20),
      delivery_status: 'delivered',
    },
    {
      id: 'm4',
      direction: 'outbound',
      author_name: 'Support',
      body: 'Of course — what is the new address?',
      created_at: minutesAgo(18),
      delivery_status: 'sent',
    },
  ],
  'demo-3': [
    {
      id: 'm5',
      direction: 'inbound',
      author_name: null,
      body: 'Do you ship to Jordan?',
      created_at: minutesAgo(64),
      delivery_status: 'delivered',
    },
  ],
  'demo-4': [
    {
      id: 'm6',
      direction: 'inbound',
      author_name: 'Noor Aziz',
      body: 'Perfect, thank you!',
      created_at: minutesAgo(60 * 26),
      delivery_status: 'delivered',
    },
  ],
}

const delay = <T,>(value: T) => new Promise<T>((r) => setTimeout(() => r(structuredClone(value)), 250))

export const mockApi = {
  readiness: () =>
    delay<ReadinessResponse>({ status: 'ok', checks: { database: 'ok', chatwoot: 'ok' } }),
  dashboardSummary: () =>
    delay<DashboardSummary>({
      open_conversations: conversations.filter((c) => c.status === 'open').length,
      events_today: 27,
      last_event_at: minutesAgo(2),
      integration_status: 'ok',
    }),
  listConversations: (status?: string) =>
    delay(status ? conversations.filter((c) => c.status === status) : conversations),
  getConversation: (id: string) => delay(conversations.find((c) => c.id === id)!),
  listMessages: (id: string) => delay(messages[id] ?? []),
  sendReply: (id: string, body: string) => {
    const msg: Message = {
      id: `local-${Date.now()}`,
      direction: 'outbound',
      author_name: 'You',
      body,
      created_at: new Date().toISOString(),
      delivery_status: 'sent',
    }
    ;(messages[id] ??= []).push(msg)
    const conv = conversations.find((c) => c.id === id)
    if (conv) {
      conv.last_message_preview = body
      conv.last_activity_at = msg.created_at
    }
    return delay(msg)
  },
}
