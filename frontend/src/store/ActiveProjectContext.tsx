import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'
import type { Project } from '../services/api'

interface ActiveProjectContextValue {
  activeProject: Project | null
  setActiveProject: (project: Project | null) => void
}

const ActiveProjectContext = createContext<ActiveProjectContextValue | undefined>(undefined)

export function ActiveProjectProvider({ children }: { children: ReactNode }) {
  const [activeProject, setActiveProject] = useState<Project | null>(null)
  const value = useMemo(() => ({ activeProject, setActiveProject }), [activeProject])

  return <ActiveProjectContext.Provider value={value}>{children}</ActiveProjectContext.Provider>
}

export function useActiveProject() {
  const context = useContext(ActiveProjectContext)
  if (!context) {
    throw new Error('useActiveProject must be used within ActiveProjectProvider')
  }
  return context
}
