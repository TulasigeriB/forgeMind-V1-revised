import { ArrowUpRight, Construction } from 'lucide-react'
import { Link } from 'react-router-dom'

interface WorkspacePageProps {
  title: string
  description: string
}

function WorkspacePage({ title, description }: WorkspacePageProps) {
  return (
    <section className="page-wrap">
      <div className="page-heading">
        <div>
          <div className="eyebrow">WORKSPACE MODULE</div>
          <h1>{title}</h1>
          <p>{description}</p>
        </div>
      </div>
      <div className="empty-panel module-panel">
        <span className="empty-icon"><Construction size={22} /></span>
        <h2>Module is being prepared</h2>
        <p>This area is part of the ForgeMind workspace and will be available in a future release.</p>
        <Link to="/projects" className="text-link">Explore projects <ArrowUpRight size={15} /></Link>
      </div>
    </section>
  )
}

export default WorkspacePage
