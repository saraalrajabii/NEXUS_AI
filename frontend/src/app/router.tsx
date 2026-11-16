import { createBrowserRouter } from 'react-router'
import { AppShell } from '../components/layout/AppShell'
import { navItems } from '../components/layout/navigation'
import { ComingSoonPage } from '../pages/ComingSoonPage'
import { DashboardPage } from '../pages/DashboardPage'
import { InboxPage } from '../pages/InboxPage'
import { NotFoundPage } from '../pages/NotFoundPage'

// Upcoming sections are generated from the same list the sidebar uses,
// so a nav item can never point to a missing page.
const upcomingRoutes = navItems
  .filter((item) => item.upcoming)
  .map((item) => ({ path: item.to, element: <ComingSoonPage item={item} /> }))

export const router = createBrowserRouter([
  {
    element: <AppShell />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: 'inbox', element: <InboxPage /> },
      { path: 'inbox/:conversationId', element: <InboxPage /> },
      ...upcomingRoutes,
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])
