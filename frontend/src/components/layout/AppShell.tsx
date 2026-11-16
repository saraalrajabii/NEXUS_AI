import { Outlet } from 'react-router'
import { MobileNav, Sidebar } from './Sidebar'

/** The frame around every page: sidebar on the left, the current page on the right. */
export function AppShell() {
  return (
    <div className="flex h-full flex-col md:flex-row">
      <Sidebar />
      <MobileNav />
      <main className="flex min-h-0 min-w-0 flex-1 flex-col bg-canvas">
        <Outlet />
      </main>
    </div>
  )
}
