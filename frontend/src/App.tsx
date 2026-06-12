import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Suspense, lazy } from 'react'
import AppShell from './components/layout/AppShell'
import ErrorBoundary from './components/ErrorBoundary'
import NotFound from './pages/NotFound'

// Lazy-load all pages
const Dashboard       = lazy(() => import('./pages/Dashboard'))
const TaskManager     = lazy(() => import('./pages/work/TaskManager'))
const WipBuilder      = lazy(() => import('./pages/work/WipBuilder'))
const QuickNotes      = lazy(() => import('./pages/work/QuickNotes'))
const ActionPlan      = lazy(() => import('./pages/work/ActionPlan'))
const DiscordNotify   = lazy(() => import('./pages/work/DiscordNotify'))
const EdaTracker      = lazy(() => import('./pages/work/EdaTracker'))
const SqlSandbox      = lazy(() => import('./pages/data/SqlSandbox'))
const SnippetLibrary  = lazy(() => import('./pages/data/SnippetLibrary'))
const FabricViews     = lazy(() => import('./pages/data/FabricViews'))
const Automation      = lazy(() => import('./pages/data/Automation'))
const KpiTracker      = lazy(() => import('./pages/analytics/KpiTracker'))
const MlStudio        = lazy(() => import('./pages/analytics/MlStudio'))
const Performance     = lazy(() => import('./pages/analytics/Performance'))

function Spinner() {
  return (
    <div className="flex-1 flex items-center justify-center h-full">
      <div className="w-6 h-6 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <ErrorBoundary>
        <Suspense fallback={<Spinner />}>
          <Routes>
            <Route element={<AppShell />}>
              <Route index element={<Dashboard />} />
              <Route path="work/tasks"       element={<TaskManager />} />
              <Route path="work/wip"         element={<WipBuilder />} />
              <Route path="work/notes"       element={<QuickNotes />} />
              <Route path="work/action-plan" element={<ActionPlan />} />
              <Route path="work/discord"     element={<DiscordNotify />} />
              <Route path="work/eda"         element={<EdaTracker />} />
              <Route path="data/sql"         element={<SqlSandbox />} />
              <Route path="data/snippets"    element={<SnippetLibrary />} />
              <Route path="data/fabric"      element={<FabricViews />} />
              <Route path="data/automation"  element={<Automation />} />
              <Route path="analytics/kpi"    element={<KpiTracker />} />
              <Route path="analytics/ml"     element={<MlStudio />} />
              <Route path="analytics/perf"   element={<Performance />} />
              <Route path="*"                element={<NotFound />} />
            </Route>
          </Routes>
        </Suspense>
      </ErrorBoundary>
    </BrowserRouter>
  )
}
