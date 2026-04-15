import { Suspense, lazy } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from './components/layout/AppLayout'
import { SocProvider } from './context/SocContext'

const OverviewPage = lazy(async () => ({
  default: (await import('./pages/OverviewPage')).OverviewPage,
}))

const OperationsPage = lazy(async () => ({
  default: (await import('./pages/OperationsPage')).OperationsPage,
}))

const ReportingPage = lazy(async () => ({
  default: (await import('./pages/ReportingPage')).ReportingPage,
}))

function App() {
  return (
    <SocProvider>
      <Routes>
        <Route element={<AppLayout />}>
          <Route
            index
            element={
              <Suspense fallback={<RouteLoader />}>
                <OverviewPage />
              </Suspense>
            }
          />
          <Route
            path="operations"
            element={
              <Suspense fallback={<RouteLoader />}>
                <OperationsPage />
              </Suspense>
            }
          />
          <Route
            path="reporting"
            element={
              <Suspense fallback={<RouteLoader />}>
                <ReportingPage />
              </Suspense>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </SocProvider>
  )
}

function RouteLoader() {
  return (
    <div className="panel animate-rise flex min-h-40 items-center justify-center">
      <p className="text-sm uppercase tracking-[0.16em] text-cyan-100">Loading module...</p>
    </div>
  )
}

export default App
