import { NavLink, useLocation } from 'react-router-dom'
import {
  Activity,
  Boxes,
  ChevronRight,
  CircleUserRound,
  Factory,
  LayoutDashboard,
  Settings,
  PanelLeftClose,
  PanelLeftOpen,
  UserCircle,
} from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { useActiveProject } from '../store/ActiveProjectContext'
import ToastViewport from './ToastViewport'

const navigation = [
  { label: 'Dashboard', to: '/dashboard', icon: LayoutDashboard },
  { label: 'Projects', to: '/projects', icon: Boxes },
  { label: 'Customers', to: '/customers', icon: CircleUserRound },
  { label: 'Settings', to: '/settings', icon: Settings },
]

function AppLayout({ children }: { children: ReactNode }) {
  const location = useLocation()
  const { activeProject } = useActiveProject()
  const [isCollapsed, setIsCollapsed] = useState(false)
  const isIntake = location.pathname === '/projects/new'
  const isProjectView = location.pathname.startsWith('/project/') || (!isIntake && /^\/projects\/[^/]+$/.test(location.pathname))

  return (
    <div className={`app-shell ${isCollapsed ? 'sidebar-collapsed' : ''}`}>
      <aside className="sidebar">
        <div className="sidebar-header">
          <NavLink to="/dashboard" className="brand-lockup" aria-label="ForgeMind home">
            <span className="brand-mark"><Activity size={19} strokeWidth={2.5} /></span>
            {!isCollapsed && <span>FORGEMIND<span className="brand-ai"> AI</span></span>}
          </NavLink>
          <button
            className="sidebar-toggle"
            onClick={() => setIsCollapsed(!isCollapsed)}
            aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {isCollapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
          </button>
        </div>

        {!isCollapsed && (
          <div className="workspace-switcher">
            <span className="workspace-mark"><Factory size={15} strokeWidth={2.2} /></span>
            <span><strong>ForgeMind shop</strong><small>Manufacturing workspace</small></span>
            <ChevronRight size={14} />
          </div>
        )}

        {!isCollapsed && <div className="sidebar-section-label">WORKSPACE</div>}
        <nav className="sidebar-nav" aria-label="Main navigation">
          {navigation.map(({ label, to, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) => `nav-link${isActive ? ' nav-link-active' : ''}`}
              title={isCollapsed ? label : undefined}
            >
              <Icon size={18} strokeWidth={1.8} />
              {!isCollapsed && <span>{label}</span>}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <NavLink to="/profile" className="nav-link profile-link" title={isCollapsed ? 'Profile' : undefined}>
            <UserCircle size={18} strokeWidth={1.8} />
            {!isCollapsed && <span>User Profile</span>}
          </NavLink>

          {!isCollapsed && (
            <>
              <div className="system-status"><span className="status-light" /> SYSTEM OPERATIONAL</div>
              <div className="sidebar-version">FORGEMIND PLATFORM <span>v0.1</span></div>
            </>
          )}
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
                <span className="breadcrumb-current">Project workspace</span>
              </>
            ) : (
              <span className="breadcrumb-current">
                {isIntake ? 'New project' : navigation.find((item) => item.to === location.pathname)?.label ?? (location.pathname === '/dashboard' ? 'Dashboard' : 'Workspace')}
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
      <ToastViewport />
    </div>
  )
}

export default AppLayout
