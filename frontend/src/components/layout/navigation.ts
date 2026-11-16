import { ChartColumn, Inbox, LayoutDashboard, Settings, Users, Workflow, type LucideIcon } from 'lucide-react'

export interface NavItem {
  to: string
  label: string
  icon: LucideIcon
  /** Upcoming features are visible but clearly marked. */
  upcoming?: { lesson: string; description: string }
}

export const navItems: NavItem[] = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/inbox', label: 'Inbox', icon: Inbox },
  {
    to: '/contacts',
    label: 'Contacts',
    icon: Users,
    upcoming: { lesson: 'A future lesson', description: 'A unified view of every customer and their history across channels.' },
  },
  {
    to: '/automations',
    label: 'Automations',
    icon: Workflow,
    upcoming: { lesson: 'A future lesson', description: 'Rules and workflows that route, tag and answer conversations automatically.' },
  },
  {
    to: '/reports',
    label: 'Reports',
    icon: ChartColumn,
    upcoming: { lesson: 'A future lesson', description: 'Response times, volume and team performance over time.' },
  },
  {
    to: '/settings',
    label: 'Settings',
    icon: Settings,
    upcoming: { lesson: 'A future lesson', description: 'Workspace, team members, integrations and preferences.' },
  },
]
