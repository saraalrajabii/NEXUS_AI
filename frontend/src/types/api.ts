// NEXUS API types. These mirror the backend's own schemas (docs/architecture.md §6).
// They are deliberately NOT Chatwoot's shapes — the backend converts Chatwoot data first.

export type ConversationStatus = 'open' | 'pending' | 'resolved' | 'snoozed'

export interface Contact {
  name: string | null
  email: string | null
}

export interface Conversation {
  id: string
  channel: string
  contact: Contact
  status: ConversationStatus
  last_message_preview: string | null
  last_activity_at: string
}

export type MessageDirection = 'inbound' | 'outbound'
export type DeliveryStatus = 'sent' | 'delivered' | 'failed' | 'pending'

export interface Message {
  id: string
  direction: MessageDirection
  author_name: string | null
  body: string
  created_at: string
  delivery_status: DeliveryStatus
}

export type CheckState = 'ok' | 'not_configured' | 'unreachable' | 'error'

export interface ReadinessResponse {
  status: 'ok' | 'degraded'
  checks: { database: CheckState; chatwoot: CheckState }
}

export interface DashboardSummary {
  open_conversations: number
  events_today: number
  last_event_at: string | null
  integration_status: CheckState
}

export interface ApiErrorBody {
  error: { code: string; message: string }
}
