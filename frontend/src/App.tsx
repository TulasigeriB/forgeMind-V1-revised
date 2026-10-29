import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import AppLayout from './components/AppLayout'
import Dashboard from './pages/Dashboard'
import ProjectIntake from './pages/ProjectIntake'
import CustomersPage from './pages/CustomersPage'
import SettingsPage from './pages/SettingsPage'
import WorkspacePage from './pages/WorkspacePage'
import { ActiveProjectProvider } from './store/ActiveProjectContext'

const ProjectIntelligenceViewer = lazy(() => import('./pages/ProjectIntelligenceViewer'))

function App() {
  return (
    <ActiveProjectProvider>
      <AppLayout>
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/projects" element={<Dashboard mode="projects" />} />
          <Route path="/projects/new" element={<ProjectIntake />} />
          <Route path="/project/:projectId" element={<Suspense fallback={<div className="loading-state page-loading"><span className="loading-spinner" /> Loading project workspace…</div>}><ProjectIntelligenceViewer /></Suspense>} />
          <Route path="/projects/:projectId" element={<Suspense fallback={<div className="loading-state page-loading"><span className="loading-spinner" /> Loading project workspace…</div>}><ProjectIntelligenceViewer /></Suspense>} />
          <Route path="/customers" element={<CustomersPage />} />
          <Route path="/profile" element={<WorkspacePage title="User profile" description="Account and workspace identity." />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AppLayout>
    </ActiveProjectProvider>
  )
}

export default App
