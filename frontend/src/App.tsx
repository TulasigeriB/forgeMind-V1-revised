import { Navigate, Route, Routes } from 'react-router-dom'
import AppLayout from './components/AppLayout'
import Dashboard from './pages/Dashboard'
import ProjectIntake from './pages/ProjectIntake'
import ProjectIntelligenceViewer from './pages/ProjectIntelligenceViewer'
import SettingsPage from './pages/SettingsPage'
import WorkspacePage from './pages/WorkspacePage'
import { ActiveProjectProvider } from './store/ActiveProjectContext'

function App() {
  return (
    <ActiveProjectProvider>
      <AppLayout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/projects" element={<Dashboard />} />
          <Route path="/projects/new" element={<ProjectIntake />} />
          <Route path="/project/:projectId" element={<ProjectIntelligenceViewer />} />
          <Route path="/customers" element={<WorkspacePage title="Customer CRM" description="Customer records and quoting relationships." />} />
          <Route path="/templates" element={<WorkspacePage title="DNA Templates" description="Reusable manufacturing and costing templates." />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AppLayout>
    </ActiveProjectProvider>
  )
}

export default App
