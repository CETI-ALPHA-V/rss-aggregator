import { StrictMode, Suspense, lazy } from 'react'
import { createRoot } from 'react-dom/client'
import { Navigate, RouterProvider, createBrowserRouter } from 'react-router-dom'
import { Layout } from './components/Layout'
import './index.css'
import { RefreshProvider } from './lib/refresh'
import DigestPage from './pages/DigestPage'
import FeedPage from './pages/FeedPage'

// Charts (recharts) are only needed on this page, so keep them out of the main bundle.
const BenchmarksPage = lazy(() => import('./pages/BenchmarksPage'))

const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { index: true, element: <FeedPage /> },
      {
        path: 'benchmarks',
        element: (
          <Suspense fallback={<p className="py-16 text-center text-sm text-muted">Loading benchmarks…</p>}>
            <BenchmarksPage />
          </Suspense>
        ),
      },
      { path: 'models', element: <Navigate to="/benchmarks" replace /> },
      { path: 'digest', element: <DigestPage /> },
      { path: '*', element: <FeedPage /> },
    ],
  },
])

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <RefreshProvider>
      <RouterProvider router={router} />
    </RefreshProvider>
  </StrictMode>,
)
