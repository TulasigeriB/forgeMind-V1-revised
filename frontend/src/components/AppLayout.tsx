import { NavLink, useLocation } from 'react-router-dom'
import {
  Activity,
  Boxes,
  ChevronRight,
  CircleUserRound,
  Factory,
  LayoutDashboard,
  Settings,
} from 'lucide-react'
import type { ReactNode } from 'react'
import { useActiveProject } from '../store/ActiveProjectContext'

const navigation = [
  { label: 'Dashboard', to: '/', icon: LayoutDashboard, end: true },
  { label: 'Project Explorer', to: '/projects', icon: Boxes },
  { label: 'Customer CRM', to: '/customers', icon: CircleUserRound },
  { label: 'DNA Templates', to: '/templates', icon: Factory },
  { label: 'Settings', to: '/settings', icon: Settings },
]

function AppLayout({ children }: { children: ReactNode }) {
  const location = useLocation()
  const { activeProject } = useActiveProject()
  const isProjectView = location.pathname.startsWith('/project/')
  const isIntake = location.pathname === '/projects/new'

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <NavLink to="/" className="brand-lockup" aria-label="ForgeMind home">
          <span className="brand-mark"><Activity size={19} strokeWidth={2.5} /></span>
          <span>FORGEMIND<span className="brand-ai"> AI</span></span>
        </NavLink>

        <div className="sidebar-section-label">WORKSPACE</div>
        <nav className="sidebar-nav" aria-label="Main navigation">
          {navigation.map(({ label, to, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) => `nav-link${isActive ? ' nav-link-active' : ''}`}
            >
              <Icon size={18} strokeWidth={1.8} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="system-status"><span className="status-light" /> SYSTEM OPERATIONAL</div>
          <div className="sidebar-version">FORGEMIND PLATFORM <span>v0.1</span></div>
        </div>
      </aside>

      <div className="main-column">
        <header className="topbar">
          <div className="breadcrumbs" aria-label="Breadcrumb">
            <span>ForgeMind</span>
            <ChevronRight size={14} />
            {isProjectView ? (
              <>
                <NavLink to="/projects" className="breadcrumb-link">Projects</NavLink>
                <ChevronRight size={14} />
                <span>{activeProject?.part_number ?? 'Project'}</span>
                <ChevronRight size={14} />
                <span className="breadcrumb-current">Costing Analysis</span>
              </>
            ) : (
              <span className="breadcrumb-current">
                {isIntake ? 'New Project' : navigation.find((item) => item.to === location.pathname)?.label ?? 'Workspace'}
              </span>
            )}
          </div>
          <div className="topbar-meta">
            <span className="environment-label">MANUFACTURING INTELLIGENCE</span>
            <span className="avatar">FM</span>
          </div>
        </header>
        <main className="page-content">{children}</main>
      </div>
    </div>
  )
}

export default AppLayout
