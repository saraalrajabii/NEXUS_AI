export type InboxFilter = 'open' | 'pending' | 'resolved' | 'all'

export const filters: { value: InboxFilter; label: string }[] = [
  { value: 'open', label: 'Open' },
  { value: 'pending', label: 'Pending' },
  { value: 'resolved', label: 'Resolved' },
  { value: 'all', label: 'All' },
]
