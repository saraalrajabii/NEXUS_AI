import type { CheckState } from '../types/api'

export const checkLabel: Record<CheckState, string> = {
  ok: 'Connected',
  not_configured: 'Not configured',
  unreachable: 'Unreachable',
  error: 'Error',
}
