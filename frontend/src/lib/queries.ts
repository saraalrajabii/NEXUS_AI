// Data hooks. TanStack Query handles caching, loading/error state and polling,
// so components just ask "give me the conversations" and re-render when they change.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './api'

const INBOX_POLL_MS = 3_000 // real-time push arrives in a later lesson

export const useReadiness = () =>
  useQuery({ queryKey: ['readiness'], queryFn: api.readiness, refetchInterval: 10_000 })

export const useDashboardSummary = () =>
  useQuery({ queryKey: ['dashboard'], queryFn: api.dashboardSummary, refetchInterval: 10_000 })

export const useConversations = (status?: string) =>
  useQuery({
    queryKey: ['conversations', status ?? 'all'],
    queryFn: () => api.listConversations(status),
    refetchInterval: INBOX_POLL_MS,
  })

export const useConversation = (conversationId: string | undefined) =>
  useQuery({
    queryKey: ['conversation', conversationId],
    queryFn: () => api.getConversation(conversationId!),
    enabled: Boolean(conversationId),
    refetchInterval: INBOX_POLL_MS,
  })

export const useMessages =(conversationId: string | undefined) =>
  useQuery({
    queryKey: ['messages', conversationId],
    queryFn: () => api.listMessages(conversationId!),
    enabled: Boolean(conversationId),
    refetchInterval: INBOX_POLL_MS,
  })

export const useSendReply = (conversationId: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: string) => api.sendReply(conversationId, body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['messages', conversationId] })
      void qc.invalidateQueries({ queryKey: ['conversations'] })
      void qc.invalidateQueries({ queryKey: ['conversation', conversationId] })
    },
  })
}
