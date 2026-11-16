// The ONLY module that talks to the network. Every request goes to the NEXUS Backend
// (via the Vite proxy) — never to Chatwoot.
import { mockApi } from '../mocks/mockApi'
import type {
  ApiErrorBody,
  Conversation,
  DashboardSummary,
  Message,
  ReadinessResponse,
} from '../types/api'

export const USE_MOCKS = import.meta.env.VITE_USE_MOCKS === 'true'

/** A failed request, with the backend's error code when it sent one. */
export class ApiError extends Error {
  readonly code: string
  readonly status: number

  constructor(code: string, message: string, status: number) {
    super(message)
    this.code = code
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(path, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...init?.headers },
    })
  } catch {
    throw new ApiError('BACKEND_UNREACHABLE', 'Cannot reach the NEXUS backend.', 0)
  }

  if (!res.ok) {
    // The backend always answers errors as {"error": {code, message}}.
    // If something else answers (e.g. the proxy, with the backend down), fall back to a generic code.
    const body = (await res.json().catch(() => null)) as ApiErrorBody | null
    if (body?.error) throw new ApiError(body.error.code, body.error.message, res.status)
    const code = res.status === 502 || res.status === 504 ? 'BACKEND_UNREACHABLE' : 'HTTP_ERROR'
    throw new ApiError(code, `Request failed with status ${res.status}.`, res.status)
  }
  return (await res.json()) as T
}

/** /health/ready answers 503 (with a normal body) when the database is down — that is data, not an error. */
async function readiness(): Promise<ReadinessResponse> {
  let res: Response
  try {
    res = await fetch('/health/ready')
  } catch {
    throw new ApiError('BACKEND_UNREACHABLE', 'Cannot reach the NEXUS backend.', 0)
  }
  const body = (await res.json().catch(() => null)) as ReadinessResponse | null
  if (body?.checks) return body
  throw new ApiError('BACKEND_UNREACHABLE', `Health check failed with status ${res.status}.`, res.status)
}

const httpApi = {
  readiness,
  dashboardSummary: () => request<DashboardSummary>('/api/dashboard/summary'),
  listConversations: (status?: string) =>
    request<Conversation[]>(`/api/conversations${status ? `?status=${encodeURIComponent(status)}` : ''}`),
  getConversation: (id: string) => request<Conversation>(`/api/conversations/${id}`),
  listMessages: (id: string) => request<Message[]>(`/api/conversations/${id}/messages`),
  sendReply: (id: string, body: string) =>
    request<Message>(`/api/conversations/${id}/messages`, {
      method: 'POST',
      body: JSON.stringify({ body }),
    }),
}

export type NexusApi = typeof httpApi

export const api: NexusApi = USE_MOCKS ? mockApi : httpApi
