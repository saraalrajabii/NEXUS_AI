import { Link } from 'react-router'
import { PageHeader } from '../components/ui'

export function NotFoundPage() {
  return (
    <>
      <PageHeader title="Page not found" />
      <div className="flex flex-1 flex-col items-center justify-center gap-3 p-6 text-center">
        <p className="text-[13px] text-muted">This page doesn’t exist.</p>
        <Link to="/" className="text-[13px] font-medium text-accent-ink hover:underline">
          Back to Dashboard
        </Link>
      </div>
    </>
  )
}
