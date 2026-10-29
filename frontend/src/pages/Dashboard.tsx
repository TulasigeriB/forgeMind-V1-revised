import { useEffect, useMemo, useState } from 'react'
import { Bar, Chart, Doughnut } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  ArcElement,
  BarElement,
  CategoryScale,
  Filler,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip,
  type ChartData,
  type ChartOptions,
} from 'chart.js'

import { Activity, ArrowDownRight, ArrowRight, BadgeDollarSign, CheckCircle2, CircleAlert, Clock3, FileText, Plus, RefreshCw, Search, Wallet, Trash2 } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import axios from 'axios'
import { ProjectService, type DrawingAnalysis, type EngineeringFile, type Project, type Quote } from '../services/api'
import { useActiveProject } from '../store/ActiveProjectContext'
import { normalizeProjectStatus } from '../utils/projectStatus'

ChartJS.register(ArcElement, BarElement, CategoryScale, Filler, Legend, LinearScale, LineElement, PointElement, Tooltip)

interface ProjectInsight {
  project: Project
  files: EngineeringFile[] | null
  quote: Quote | null
  analysis: DrawingAnalysis | null
  reviewDate: string | null
}

interface ActivityItem {
  id: string
  title: string
  description: string
  createdAt: string
  kind: 'upload' | 'analysis' | 'quote'
}

interface DashboardInsights {
  drawingCount: number
  quotedValue: number
  averageRunTime: number | null
  quoteCount: number
  quoteDates: string[]
  recentActivity: ActivityItem[]
  turning: number
  milling: number
  precision: number
}

const emptyInsights: DashboardInsights = {
  drawingCount: 0,
  quotedValue: 0,
  averageRunTime: null,
  quoteCount: 0,
  quoteDates: [],
  recentActivity: [],
  turning: 0,
  milling: 0,
  precision: 0,
}

function statusClass(status: string) {
  return `status-pill status-${normalizeProjectStatus(status).toLowerCase().replace(/ /g, '-')}`
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

function getSixMonthLabels() {
  const now = new Date()
  return Array.from({ length: 6 }, (_, index) => {
    const date = new Date(now.getFullYear(), now.getMonth() - 5 + index, 1)
    return {
      key: `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`,
      label: date.toLocaleDateString(undefined, { month: 'short' }),
    }
  })
}

function Dashboard({ mode = 'overview' }: { mode?: 'overview' | 'projects' }) {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [loadingInsights, setLoadingInsights] = useState(false)
  const [insightsError, setInsightsError] = useState('')
  const [insights, setInsights] = useState<DashboardInsights>(emptyInsights)
  const [search, setSearch] = useState('')
  const [materialFilter, setMaterialFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const navigate = useNavigate()
  const { setActiveProject } = useActiveProject()
  const isProjectList = mode === 'projects'

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

  useEffect(() => {
    if (isProjectList) {
      setInsights(emptyInsights)
      setInsightsError('')
      setLoadingInsights(false)
      return
    }
    if (loading) return
    if (projects.length === 0) {
      setInsights(emptyInsights)
      setInsightsError('')
      setLoadingInsights(false)
      return
    }

    let cancelled = false
    setLoadingInsights(true)
    setInsightsError('')

    async function loadInsights() {
      const results: Array<ProjectInsight & { incomplete: boolean }> = []
      for (let offset = 0; offset < projects.length; offset += 4) {
        const batch = await Promise.all(projects.slice(offset, offset + 4).map(async (project) => {
          const [filesResult, quoteResult, analysisResult] = await Promise.allSettled([
            ProjectService.getFiles(project.id),
            project.status.toLowerCase() === 'quoted'
              ? ProjectService.getQuote(project.id).then((response) => response.data)
              : Promise.resolve(null),
            ProjectService.getAnalysis(project.id).then((response) => response.data),
          ])
          return {
            project,
            files: filesResult.status === 'fulfilled' ? filesResult.value.data : null,
            quote: quoteResult.status === 'fulfilled' ? quoteResult.value : null,
            analysis: analysisResult.status === 'fulfilled' ? analysisResult.value.analysis : null,
            reviewDate: analysisResult.status === 'fulfilled' ? analysisResult.value.review?.updated_at ?? null : null,
            incomplete: filesResult.status === 'rejected' || quoteResult.status === 'rejected' || analysisResult.status === 'rejected',
          }
        }))
        if (cancelled) return
        results.push(...batch)
      }
      if (cancelled) return

      const usable = results.filter((result): result is typeof result & { files: EngineeringFile[] } => result.files !== null)
      const quotes = results.flatMap((result) => result.quote ? [result.quote] : [])
      const cycleTimes = quotes.map((quote) => quote.total_time_minutes).filter((time) => time > 0)
      const features = results.flatMap((result) => result.analysis ? [result.analysis] : [])
      const recentActivity = results.flatMap((result) => [
        ...(result.files ?? []).map((file) => ({
          id: `upload-${file.id}`,
          title: 'Drawing uploaded',
          description: `${result.project.part_number} · PDF drawing`,
          createdAt: file.created_at,
          kind: 'upload' as const,
        })),
        ...(result.analysis && result.reviewDate ? [{
          id: `analysis-${result.project.id}`,
          title: 'Analysis reviewed',
          description: `${result.project.part_number} · engineering review saved`,
          createdAt: result.reviewDate,
          kind: 'analysis' as const,
        }] : []),
        ...(result.quote ? [{
          id: `quote-${result.quote.id}`,
          title: 'Quotation generated',
          description: `${result.project.part_number} · $${result.quote.total_cost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
          createdAt: result.quote.created_at,
          kind: 'quote' as const,
        }] : []),
      ]).sort((left, right) => Date.parse(right.createdAt) - Date.parse(left.createdAt)).slice(0, 6)
      setInsights({
        drawingCount: usable.reduce((count, result) => count + result.files.length, 0),
        quotedValue: quotes.reduce((total, quote) => total + quote.total_cost, 0),
        averageRunTime: cycleTimes.length ? cycleTimes.reduce((total, time) => total + time, 0) / cycleTimes.length : null,
        quoteCount: quotes.length,
        quoteDates: quotes.map((quote) => quote.created_at),
        recentActivity,
        turning: features.reduce((total, analysis) => total + analysis.manufacturing_operations.turning.reduce((count, feature) => count + (feature.quantity ?? 1), 0), 0),
        milling: features.reduce((total, analysis) => total + analysis.manufacturing_operations.milling.reduce((count, feature) => count + (feature.quantity ?? 1), 0), 0),
        precision: features.reduce((total, analysis) => total + analysis.precision_fits.length, 0),
      })
      if (results.some((result) => result.incomplete)) {
        setInsightsError('Some project details could not be loaded. Dashboard totals may be incomplete; refresh to try again.')
      } else {
        setInsightsError('')
      }
      setLoadingInsights(false)
    }

    void loadInsights().catch((requestError: unknown) => {
      if (!cancelled) {
        setInsightsError(getErrorMessage(requestError))
        setLoadingInsights(false)
      }
    })

    return () => {
      cancelled = true
    }
  }, [isProjectList, loading, projects])

  async function handleDeleteProject(id: string) {
    if (!confirm('Are you sure you want to delete this project? This will remove all associated drawings and calculations.')) return

    try {
      await ProjectService.deleteProject(id)
      setProjects((current) => current.filter((p) => p.id !== id))
      setNotice('Project deleted successfully')
    } catch (err) {
      setError('Failed to delete project. Please try again.')
    }
  }

  const materials = useMemo(
    () => Array.from(new Set(projects.map((project) => project.material_spec).filter((material): material is string => Boolean(material)))).sort(),
    [projects],
  )
  const visibleProjects = projects.filter((project) => {
    const matchesSearch = `${project.part_number} ${project.material_spec ?? ''} ${project.customer_name ?? ''} ${project.rfq_id}`.toLowerCase().includes(search.toLowerCase())
    const matchesMaterial = materialFilter === 'all' || project.material_spec === materialFilter
    const matchesStatus = statusFilter === 'all' || normalizeProjectStatus(project.status) === statusFilter
    return matchesSearch && matchesMaterial && matchesStatus
  })
  const analyzedCount = projects.filter((project) => ['Costed', 'Quoted'].includes(normalizeProjectStatus(project.status))).length
  const analyzingCount = projects.filter((project) => normalizeProjectStatus(project.status) === 'Analyzing').length
  const monthLabels = getSixMonthLabels()
  const monthlyProjects = monthLabels.map(({ key }) => projects.filter((project) => project.created_at.slice(0, 7) === key))
  const monthlyQuotes = monthLabels.map(({ key }) => insights.quoteDates.filter((createdAt) => createdAt.slice(0, 7) === key).length)
  const conversionRate = monthlyProjects.map((cohort) => {
    if (cohort.length === 0) return 0
    const quotedIds = new Set(projects.filter((project) => normalizeProjectStatus(project.status) === 'Quoted').map((project) => project.id))
    return Math.round((cohort.filter((project) => quotedIds.has(project.id)).length / cohort.length) * 100)
  })
  const quotationData: ChartData<'bar' | 'line', number[], string> = {
    labels: monthLabels.map((month) => month.label),
    datasets: [
      {
        type: 'bar',
        label: 'Projects quoted',
        data: monthlyQuotes,
        backgroundColor: '#f0a66f',
        borderRadius: 5,
        maxBarThickness: 26,
        yAxisID: 'y',
      },
      {
        type: 'line',
        label: 'Conversion',
        data: conversionRate,
        borderColor: '#386b61',
        backgroundColor: '#386b61',
        pointBackgroundColor: '#fff',
        pointBorderColor: '#386b61',
        pointBorderWidth: 2,
        pointRadius: 4,
        tension: 0.35,
        yAxisID: 'y1',
      },
    ],
  }
  const quotationOptions: ChartOptions<'bar' | 'line'> = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { intersect: false, mode: 'index' },
    plugins: {
      legend: { position: 'bottom', labels: { usePointStyle: true, boxWidth: 7, boxHeight: 7, padding: 18, color: '#728078', font: { size: 10 } } },
      tooltip: { backgroundColor: '#1e302d', padding: 10, titleFont: { size: 11 }, bodyFont: { size: 11 } },
    },
    scales: {
      x: { grid: { display: false }, ticks: { color: '#87938c', font: { size: 10 } }, border: { display: false } },
      y: { beginAtZero: true, grid: { color: '#edf0ec' }, ticks: { precision: 0, color: '#87938c', font: { size: 10 } }, border: { display: false } },
      y1: { beginAtZero: true, position: 'right', max: 100, grid: { drawOnChartArea: false }, ticks: { callback: (value) => `${value}%`, color: '#87938c', font: { size: 10 } }, border: { display: false } },
    },
  }
  const featureData = {
    labels: ['Turning', 'Milling', 'Precision fits'],
    datasets: [{
      data: [insights.turning, insights.milling, insights.precision],
      backgroundColor: ['#294d48', '#e6a16c', '#9cb2a3'],
      borderWidth: 0,
      hoverOffset: 5,
    }],
  }
  const featureOptions: ChartOptions<'doughnut'> = {
    responsive: true,
    maintainAspectRatio: false,
    cutout: '72%',
    plugins: {
      legend: { display: false },
      tooltip: { backgroundColor: '#1e302d', padding: 10, bodyFont: { size: 11 } },
    },
  }

  function openProject(project: Project) {
    setActiveProject(project)
    navigate(`/project/${project.id}`)
  }

  return (
    <section className={`page-wrap ${isProjectList ? 'projects-page' : 'dashboard-page'}`}>
      <div className="page-heading">
        <div>
          <div className="eyebrow">{isProjectList ? 'WORK QUEUE' : 'OPERATIONS OVERVIEW'} <span className="eyebrow-dot" /></div>
          <h1>{isProjectList ? 'Project Explorer' : 'Manufacturing overview'}</h1>
          <p>{isProjectList ? 'Search and track every project moving through your production pipeline.' : 'A live view of project throughput, drawing intelligence, and quoted work.'}</p>
        </div>
        <Link to="/projects/new" className="button button-primary"><Plus size={17} /> New project</Link>
      </div>

      {!isProjectList && (
        <>
          {insightsError && <div className="inline-warning" role="status"><CircleAlert size={16} />{insightsError}</div>}
          <div className="metric-grid dashboard-metrics">
            <article className="metric-card metric-card-featured">
              <div className="metric-top"><span>Active projects</span><span className="metric-icon"><Activity size={17} /></span></div>
              <div className="metric-value">{loading ? '—' : projects.length.toLocaleString()}</div>
              <div className="metric-foot">{analyzingCount} currently in analysis</div>
            </article>
            <article className="metric-card">
              <div className="metric-top"><span>Drawings processed</span><span className="metric-icon metric-icon-blue"><FileText size={17} /></span></div>
              <div className="metric-value">{loadingInsights ? '—' : insights.drawingCount.toLocaleString()}</div>
              <div className="metric-foot">PDF files in project workspaces</div>
            </article>
            <article className="metric-card">
              <div className="metric-top"><span>Total quoted value</span><span className="metric-icon metric-icon-green"><Wallet size={17} /></span></div>
              <div className="metric-value">{loadingInsights ? '—' : `$${insights.quotedValue.toLocaleString(undefined, { maximumFractionDigits: 0 })}`}</div>
              <div className="metric-foot">{insights.quoteCount} generated {insights.quoteCount === 1 ? 'quote' : 'quotes'}</div>
            </article>
            <article className="metric-card">
              <div className="metric-top"><span>Avg. quoted run time</span><span className="metric-icon metric-icon-amber"><Clock3 size={17} /></span></div>
              <div className="metric-value">{loadingInsights || insights.averageRunTime === null ? '—' : <>{insights.averageRunTime.toFixed(0)}<span className="metric-unit"> min</span></>}</div>
              <div className="metric-foot">Average machining time per quoted order</div>
            </article>
          </div>

          <div className="dashboard-chart-grid">
            <section className="panel chart-panel quotation-chart-panel">
              <div className="chart-heading"><div><div className="eyebrow">COMMERCIAL PULSE</div><h2>Quotation volume &amp; conversion</h2></div><span className="chart-period">Last 6 months</span></div>
              <div className="chart-canvas">{loadingInsights ? <div className="chart-loading">Preparing live project insights…</div> : <Chart type="bar" data={quotationData} options={quotationOptions} />}</div>
            </section>
            <section className="panel chart-panel feature-chart-panel">
              <div className="chart-heading"><div><div className="eyebrow">ENGINEERING SIGNAL</div><h2>Extracted operations</h2></div></div>
              <div className="feature-chart-body">
                <div className="feature-donut">
                  {loadingInsights ? <div className="chart-loading">Loading…</div> : <Doughnut data={featureData} options={featureOptions} />}
                  {!loadingInsights && <div className="donut-center"><strong>{insights.turning + insights.milling + insights.precision}</strong><span>features</span></div>}
                </div>
                <div className="feature-legend">
                  {featureData.labels.map((label, index) => (
                    <div className="feature-legend-row" key={label}><span className={`feature-key feature-key-${index}`} /><span>{label}</span><strong>{featureData.datasets[0].data[index]}</strong></div>
                  ))}
                </div>
              </div>
            </section>
          </div>
          <section className="panel activity-panel">
            <div className="panel-heading"><div><div className="eyebrow">SHOP FLOOR FEED</div><h2>Recent activity</h2></div><span className="activity-live"><span /> Latest project events</span></div>
            {loadingInsights ? <div className="activity-empty">Loading recent project events…</div> : insights.recentActivity.length === 0 ? <div className="activity-empty">New drawing uploads, engineer reviews, and quotations will appear here.</div> : (
              <ol className="activity-list">{insights.recentActivity.map((item) => {
                const Icon = item.kind === 'quote' ? BadgeDollarSign : item.kind === 'analysis' ? CheckCircle2 : FileText
                return <li className="activity-item" key={item.id}><span className={`activity-icon activity-icon-${item.kind}`}><Icon size={15} /></span><span className="activity-copy"><strong>{item.title}</strong><small>{item.description}</small></span><time dateTime={item.createdAt}>{new Date(item.createdAt).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}</time></li>
              })}</ol>
            )}
          </section>
        </>
      )}

      <section className="panel project-panel">
        <div className="panel-heading">
          <div><div className="eyebrow">{isProjectList ? 'ALL WORK ORDERS' : 'LIVE WORK QUEUE'}</div><h2>{isProjectList ? 'Projects' : 'Recent projects'}</h2></div>
          <button type="button" className="button button-secondary button-compact" onClick={() => void fetchProjects()} disabled={loading}>
            <RefreshCw size={15} className={loading ? 'spin' : ''} /> Refresh
          </button>
        </div>

        <div className="filter-bar">
          <label className="search-field"><Search size={16} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search part number, material, or RFQ" /></label>
          <label className="filter-select"><span>Status</span><select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option value="all">All statuses</option><option value="Draft">Draft</option><option value="Uploaded">Uploaded</option><option value="Analyzing">Analyzing</option><option value="In review">In review</option><option value="Approved">Approved</option><option value="Route review">Route review</option><option value="Costed">Costed</option><option value="Quoted">Quoted</option><option value="Failed">Failed</option></select></label>
          <label className="filter-select"><span>Material</span><select value={materialFilter} onChange={(event) => setMaterialFilter(event.target.value)}><option value="all">All materials</option>{materials.map((material) => <option key={material} value={material}>{material}</option>)}</select></label>
        </div>

        {error ? (
          <div className="inline-error" role="alert"><CircleAlert size={18} /><span>{error}</span><button type="button" onClick={() => void fetchProjects()}>Retry</button></div>
        ) : loading ? (
          <div className="loading-state"><span className="loading-spinner" /> Loading project queue…</div>
        ) : visibleProjects.length === 0 ? (
          <div className="empty-panel">
            {projects.length === 0 ? <><span className="empty-icon"><Activity size={21} /></span><h3>Your project queue is clear</h3><p>Create a project to begin drawing intake and manufacturing analysis.</p><Link to="/projects/new" className="button button-primary"><Plus size={16} /> Create first project</Link></> : <><span className="empty-icon"><Search size={20} /></span><h3>No matching projects</h3><p>Try changing the material, status, or search filters.</p></>}
          </div>
        ) : (
          <div className="table-scroll"><table className="data-table">
            <thead><tr><th>Project / part</th><th>Customer</th><th>Material specification</th><th>Pipeline status</th><th>Created</th><th></th><th><span className="sr-only">Open project</span></th></tr></thead>
            <tbody>{visibleProjects.map((project) => (
              <tr key={project.id} onClick={() => openProject(project)} className="project-row" tabIndex={0} onKeyDown={(event) => { if (event.key === 'Enter') openProject(project) }}>
                <td><span className="part-cell">{project.part_number}</span><span className="part-rfq">RFQ {project.rfq_id.slice(0, 8).toUpperCase()}</span></td>
                <td className="muted-cell">{project.customer_name || 'Customer not linked'}</td>
                <td className="muted-cell">{project.material_spec || 'Not specified'}</td>
                <td><span className={statusClass(project.status)}><span />{normalizeProjectStatus(project.status)}</span></td>
                <td className="muted-cell">{new Date(project.created_at).toLocaleDateString()}</td>
                <td className="text-right">
                  <button type="button" className="button button-ghost button-compact text-danger" onClick={(event) => { event.stopPropagation(); handleDeleteProject(project.id); }} aria-label={`Delete ${project.part_number}`}>
                    <Trash2 size={14} />
                  </button>
                </td>
                <td><button type="button" className="row-action" aria-label={`Open ${project.part_number}`} onClick={(event) => { event.stopPropagation(); openProject(project) }}><ArrowRight size={17} /></button></td>
              </tr>
            ))}</tbody>
          </table></div>
        )}
        <div className="table-footer"><span>{loading ? ' ' : `Showing ${visibleProjects.length} of ${projects.length} projects`}</span><span>{analyzedCount} costed or quoted</span></div>
      </section>
    </section>
  )
}

export default Dashboard
