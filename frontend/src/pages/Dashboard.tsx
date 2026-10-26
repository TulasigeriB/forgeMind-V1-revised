import { useEffect, useMemo, useState } from 'react'
import { Activity, ArrowDownRight, ArrowRight, CircleAlert, Plus, RefreshCw, Search } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import axios from 'axios'
import { ProjectService, type Project } from '../services/api'
import { useActiveProject } from '../store/ActiveProjectContext'
import { normalizeProjectStatus } from '../utils/projectStatus'

function statusClass(status: string) {
  return `status-pill status-${normalizeProjectStatus(status).toLowerCase()}`
}

function getErrorMessage(error: unknown) {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (error.response?.status === 401) return 'Your API access token is missing or invalid. Add a valid token in Settings.'
    if (typeof detail === 'string') return `Unable to load projects: ${detail}`
    if (!error.response) return 'Unable to reach the ForgeMind API. Check that the backend is running.'
    return `Unable to load projects (HTTP ${error.response.status}).`
  }
  return 'Unable to load projects. Please try again.'
}

function Dashboard() {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [materialFilter, setMaterialFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
  const navigate = useNavigate()
  const { setActiveProject } = useActiveProject()

  async function fetchProjects() {
    setLoading(true)
    setError('')
    try {
      const response = await ProjectService.getProjects()
      setProjects(response.data)
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void fetchProjects()
  }, [])

  const materials = useMemo(
    () => Array.from(new Set(projects.map((project) => project.material_spec).filter((material): material is string => Boolean(material)))).sort(),
    [projects],
  )
  const visibleProjects = projects.filter((project) => {
    const matchesSearch = `${project.part_number} ${project.material_spec ?? ''}`.toLowerCase().includes(search.toLowerCase())
    const matchesMaterial = materialFilter === 'all' || project.material_spec === materialFilter
    const matchesStatus = statusFilter === 'all' || normalizeProjectStatus(project.status) === statusFilter
    return matchesSearch && matchesMaterial && matchesStatus
  })

  const analyzedCount = projects.filter((project) => ['Costed', 'Quoted'].includes(normalizeProjectStatus(project.status))).length
  const analyzingCount = projects.filter((project) => normalizeProjectStatus(project.status) === 'Analyzing').length

  function openProject(project: Project) {
    setActiveProject(project)
    navigate(`/project/${project.id}`)
  }

  return (
    <section className="page-wrap">
      <div className="page-heading">
        <div>
          <div className="eyebrow">OPERATIONS OVERVIEW <span className="eyebrow-dot" /></div>
          <h1>Manufacturing Command Center</h1>
          <p>Track incoming work, engineering analysis, and quote readiness.</p>
        </div>
        <Link to="/projects/new" className="button button-primary">
          <Plus size={17} /> New Project
        </Link>
      </div>

      <div className="metric-grid">
        <article className="metric-card">
          <div className="metric-top"><span>Total Projects</span><span className="metric-icon"><Activity size={17} /></span></div>
          <div className="metric-value">{loading ? '—' : projects.length.toString().padStart(2, '0')}</div>
          <div className="metric-foot">Projects in your workspace</div>
        </article>
        <article className="metric-card">
          <div className="metric-top"><span>Costed / Quoted</span><span className="metric-icon metric-icon-green"><ArrowDownRight size={17} /></span></div>
          <div className="metric-value">{loading ? '—' : analyzedCount.toString().padStart(2, '0')}</div>
          <div className="metric-foot">Ready for commercial review</div>
        </article>
        <article className="metric-card">
          <div className="metric-top"><span>In Analysis</span><span className="metric-icon metric-icon-amber"><RefreshCw size={16} /></span></div>
          <div className="metric-value">{loading ? '—' : analyzingCount.toString().padStart(2, '0')}</div>
          <div className="metric-foot">Currently processing</div>
        </article>
      </div>

      <section className="panel project-panel">
        <div className="panel-heading">
          <div>
            <div className="eyebrow">WORK QUEUE</div>
            <h2>Project Explorer</h2>
          </div>
          <button type="button" className="button button-secondary button-compact" onClick={() => void fetchProjects()} disabled={loading}>
            <RefreshCw size={15} className={loading ? 'spin' : ''} /> Refresh
          </button>
        </div>

        <div className="filter-bar">
          <label className="search-field">
            <Search size={16} />
            <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search part number or material" />
          </label>
          <label className="filter-select">
            <span>Status</span>
            <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
              <option value="all">All statuses</option>
              <option value="Uploaded">Uploaded</option>
              <option value="Analyzing">Analyzing</option>
              <option value="Costed">Costed</option>
              <option value="Quoted">Quoted</option>
            </select>
          </label>
          <label className="filter-select">
            <span>Material</span>
            <select value={materialFilter} onChange={(event) => setMaterialFilter(event.target.value)}>
              <option value="all">All materials</option>
              {materials.map((material) => <option key={material} value={material}>{material}</option>)}
            </select>
          </label>
        </div>

        {error ? (
          <div className="inline-error" role="alert">
            <CircleAlert size={18} />
            <span>{error}</span>
            <button type="button" onClick={() => void fetchProjects()}>Retry</button>
          </div>
        ) : loading ? (
          <div className="loading-state"><span className="loading-spinner" /> Loading project queue…</div>
        ) : visibleProjects.length === 0 ? (
          <div className="empty-panel">
            {projects.length === 0 ? (
              <>
                <span className="empty-icon"><Activity size={21} /></span>
                <h3>Your project queue is clear</h3>
                <p>Create a project to begin drawing intake and manufacturing analysis.</p>
                <Link to="/projects/new" className="button button-primary"><Plus size={16} /> Create first project</Link>
              </>
            ) : (
              <>
                <span className="empty-icon"><Search size={20} /></span>
                <h3>No matching projects</h3>
                <p>Try changing the material, status, or search filters.</p>
              </>
            )}
          </div>
        ) : (
          <div className="table-scroll">
            <table className="data-table">
              <thead><tr><th>Part Number</th><th>Material Specification</th><th>Pipeline Status</th><th>Created</th><th><span className="sr-only">Open project</span></th></tr></thead>
              <tbody>
                {visibleProjects.map((project) => (
                  <tr key={project.id} onClick={() => openProject(project)} className="project-row" tabIndex={0} onKeyDown={(event) => { if (event.key === 'Enter') openProject(project) }}>
                    <td><span className="part-cell">{project.part_number}</span></td>
                    <td className="muted-cell">{project.material_spec || 'Not specified'}</td>
                    <td><span className={statusClass(project.status)}><span />{normalizeProjectStatus(project.status)}</span></td>
                    <td className="muted-cell">{new Date(project.created_at).toLocaleDateString()}</td>
                    <td><button type="button" className="row-action" aria-label={`Open ${project.part_number}`} onClick={(event) => { event.stopPropagation(); openProject(project) }}><ArrowRight size={17} /></button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="table-footer"><span>{loading ? ' ' : `Showing ${visibleProjects.length} of ${projects.length} projects`}</span><span>LIVE WORK QUEUE</span></div>
      </section>
    </section>
  )
}

export default Dashboard
