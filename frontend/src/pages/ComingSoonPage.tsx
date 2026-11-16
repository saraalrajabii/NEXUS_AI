import { Sparkles } from 'lucide-react'
import { Link } from 'react-router'
import { Badge, PageHeader } from '../components/ui'
import type { NavItem } from '../components/layout/navigation'

/** Placeholder for sections planned in later lessons — visible, but clearly not built yet. */
export function ComingSoonPage({ item }: { item: NavItem }) {
  const Icon = item.icon
  return (
    <>
      <PageHeader title={item.label} actions={<Badge>Upcoming</Badge>} />
      <div className="flex flex-1 items-center justify-center p-6">
        <div className="flex max-w-sm flex-col items-center gap-4 text-center">
          <span className="flex size-12 items-center justify-center rounded-2xl border border-line bg-surface text-muted">
            <Icon className="size-5" strokeWidth={1.75} />
          </span>
          <div>
            <p className="flex items-center justify-center gap-1.5 text-[15px] font-semibold">
              {item.label} is coming soon <Sparkles className="size-4 text-accent" />
            </p>
            <p className="mt-1.5 text-[13px] leading-relaxed text-muted">{item.upcoming?.description}</p>
            <p className="mt-3 text-[12px] text-faint">Planned for {item.upcoming?.lesson.toLowerCase()}.</p>
          </div>
          <Link to="/inbox" className="rounded-lg border border-line bg-surface px-3 py-1.5 text-[13px] font-medium hover:bg-surface-2">
            Go to Inbox
          </Link>
        </div>
      </div>
    </>
  )
}
