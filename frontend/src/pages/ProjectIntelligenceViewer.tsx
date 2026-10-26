import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, CircleAlert, Check, LoaderCircle, RefreshCw, Save } from 'lucide-react'
import axios from 'axios'
import { ProjectService, type EngineeringFile, type Feature, type ProcessOperation, type Project, type Quote, type ProjectAnalysisReview } from '../services/api'
import FeatureMatrix from '../components/FeatureMatrix'
import OperationTimeline from '../components/OperationTimeline'
import DrawingAnalysisPanel from '../components/DrawingAnalysisPanel'
import DrawingReviewWorkspace from '../components/DrawingReviewWorkspace'
import { useActiveProject } from '../store/ActiveProjectContext'
import { normalizeProjectStatus } from '../utils/projectStatus'
import type { DrawingAnalysis } from '../services/api'

function errorMessage(error: unknown) {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (error.response?.status === 401) return 'Your API access token is missing or invalid. Add a valid token in Settings.'
    if (typeof detail === 'string') return detail
    if (!error.response) return 'Could not reach the ForgeMind API.'
    return `Request failed with HTTP ${error.response.status}.`
  }
  return 'Unable to load project intelligence.'
}

function ProjectIntelligenceViewer() {
  const { projectId } = useParams<{ projectId: string }>()
  const { setActiveProject } = useActiveProject()
  const [project, setProject] = useState<Project | null>(null)
  const [files, setFiles] = useState<EngineeringFile[]>([])
  const [features, setFeatures] = useState<Feature[]>([])
  const [operations, setOperations] = useState<ProcessOperation[]>([])
  const [quote, setQuote] = useState<Quote | null>(null)
  const [analysis, setAnalysis] = useState<DrawingAnalysis | null>(null)
  const [analysisReview, setAnalysisReview] = useState<ProjectAnalysisReview | null>(null)
  const [processPlanStatus, setProcessPlanStatus] = useState('not_generated')
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)
  const [savingRoute, setSavingRoute] = useState(false)
  const [creatingQuote, setCreatingQuote] = useState(false)
  const [routeComment, setRouteComment] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const normalizedStatus = project ? normalizeProjectStatus(project.status) : 'Uploaded'

  const loadProjectData = useCallback(async () => {
    if (!projectId) return
    setLoading(true)
    setError('')
    try {
      const [projectResponse, analysisResponse, filesResponse] = await Promise.all([
        ProjectService.getProject(projectId),
        ProjectService.getAnalysis(projectId),
        ProjectService.getFiles(projectId),
      ])
      const response = analysisResponse.data
      const [featuresResponse, operationsResponse] = await Promise.all([
        ProjectService.getFeatures(projectId),
        ProjectService.getOperations(projectId),
      ])
      let quoteData: Quote | null = null
      if (response.process_plan_status === 'approved') {
        try {
          quoteData = (await ProjectService.getQuote(projectId)).data
        } catch (quoteError) {
          if (!axios.isAxiosError(quoteError) || quoteError.response?.status !== 404) throw quoteError
        }
      }

      setProject(projectResponse.data)
      setActiveProject(projectResponse.data)
      setFiles(filesResponse.data)
      setFeatures(featuresResponse.data)
      setOperations(operationsResponse.data)
      setQuote(quoteData)
      setAnalysis(response.analysis)
      setAnalysisReview(response.review)
      setProcessPlanStatus(response.process_plan_status)
      setRouteComment(response.route_review?.comment ?? '')
    } catch (requestError) {
      setError(errorMessage(requestError))
    } finally {
      setLoading(false)
    }
  }, [projectId, setActiveProject])

  useEffect(() => {
    void loadProjectData()
  }, [loadProjectData])

  useEffect(() => {
    if (!projectId || project?.status !== 'analyzing') return
    let cancelled = false
    let timer = 0
    const pollAnalysis = async () => {
      try {
        const response = await ProjectService.getAnalysis(projectId)
        if (cancelled) return
        if (response.data.status === 'analyzing') {
          timer = window.setTimeout(pollAnalysis, 1500)
          return
        }
        setAnalyzing(false)
        setAnalysis(response.data.analysis)
        setAnalysisReview(response.data.review)
        setProcessPlanStatus(response.data.process_plan_status)
        setProject((current) => current ? { ...current, status: response.data.status } : current)
        if (response.data.status === 'analysis_failed') setError('Drawing analysis failed. Check the worker logs and uploaded PDF.')
        else setNotice('Drawing extraction is ready for engineer review.')
        await loadProjectData()
      } catch (pollError) {
        if (!cancelled) {
          setError(errorMessage(pollError))
          timer = window.setTimeout(pollAnalysis, 3000)
        }
      }
    }
    timer = window.setTimeout(pollAnalysis, 1000)
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [projectId, project?.status, loadProjectData])

  async function handleAnalyze() {
    if (!projectId) return
    setAnalyzing(true)
    setNotice('')
    setError('')
    try {
      const response = await ProjectService.analyzeProject(projectId)
      setNotice(response.data.status ?? 'Analysis queued.')
      setProject((current) => current ? { ...current, status: 'analyzing' } : current)
    } catch (requestError) {
      setAnalyzing(false)
      setError(errorMessage(requestError))
    }
  }

  async function handleAnalysisReviewSaved(review: ProjectAnalysisReview) {
    setAnalysisReview(review)
    setProject((current) => current ? { ...current, status: review.status === 'approved' ? 'analysis_approved' : 'analysis_ready' } : current)
    if (review.status !== 'approved' || !projectId) return

    setNotice('Analysis approved. Generating a manufacturing route…')
    setError('')
    try {
      const response = await ProjectService.generateRoutes(projectId)
      setOperations(response.data)
      setFeatures((await ProjectService.getFeatures(projectId)).data)
      setProcessPlanStatus('generated')
      setProject((current) => current ? { ...current, status: 'routing' } : current)
      setNotice('Manufacturing route generated. Review and approve the operations before quotation.')
    } catch (routeError) {
      setError(errorMessage(routeError))
    }
  }

  async function handleRouteReview(status: 'approved' | 'changes_requested') {
    if (!projectId) return
    setSavingRoute(true)
    setError('')
    setNotice('')
    try {
      const response = await ProjectService.saveRouteReview(projectId, status, routeComment, operations)
      setProcessPlanStatus(response.data.process_plan_status)
      setProject((current) => current ? { ...current, status: status === 'approved' ? 'costed' : 'routing' } : current)
      setNotice(status === 'approved' ? 'Manufacturing route approved. Quotation is now available.' : 'Route review saved with changes requested.')
      if (status === 'approved') {
        try {
          setQuote((await ProjectService.getQuote(projectId)).data)
        } catch (quoteError) {
          if (!axios.isAxiosError(quoteError) || quoteError.response?.status !== 404) throw quoteError
        }
      }
    } catch (routeError) {
      setError(errorMessage(routeError))
    } finally {
      setSavingRoute(false)
    }
  }

  async function handleCreateQuote() {
    if (!projectId) return
    setCreatingQuote(true)
    setError('')
    try {
      const response = await ProjectService.createQuote(projectId)
      setQuote(response.data)
      setProject((current) => current ? { ...current, status: 'quoted' } : current)
      setNotice('Preliminary quotation generated from the approved route.')
    } catch (quoteError) {
      setError(errorMessage(quoteError))
    } finally {
      setCreatingQuote(false)
    }
  }

  function updateOperation(operationId: string, patch: Partial<ProcessOperation>) {
    setOperations((current) => current.map((operation) => operation.id === operationId ? { ...operation, ...patch } : operation))
  }

  if (loading) return <div className="loading-state page-loading"><span className="loading-spinner" /> Loading project intelligence…</div>
  if (error && !project) {
    return <section className="page-wrap"><div className="inline-error" role="alert"><CircleAlert size={18} />{error}<Link to="/projects">Back to projects</Link></div></section>
  }
  if (!project) return <section className="page-wrap"><div className="empty-panel"><h2>Project not found</h2><Link to="/projects">Return to the project explorer</Link></div></section>

  return (
    <section className="page-wrap">
      <div className="page-heading project-detail-heading">
        <div>
          <Link to="/projects" className="back-link"><ArrowLeft size={15} /> Project Explorer</Link>
          <div className="eyebrow">PROJECT INTELLIGENCE</div>
          <h1>{project.part_number}</h1>
          <p>{project.material_spec || 'Material not specified'} <span className="detail-separator">/</span> Created {new Date(project.created_at).toLocaleDateString()}</p>
        </div>
        <button type="button" onClick={() => void handleAnalyze()} disabled={analyzing || files.length === 0} className="button button-primary">
          {analyzing ? <LoaderCircle className="spin" size={16} /> : <RefreshCw size={16} />}
          {analyzing ? 'Analyzing drawing…' : 'Reanalyze drawing'}
        </button>
      </div>
      {error && <div className="inline-error" role="alert"><CircleAlert size={18} />{error}</div>}
      {notice && <div className="inline-success">{notice}</div>}
      <DrawingAnalysisPanel analysis={analysis} />
      {analysis && (
        <DrawingReviewWorkspace
          projectId={project.id}
          analysis={analysis}
          review={analysisReview}
          files={files}
          onReviewSaved={(review) => void handleAnalysisReviewSaved(review)}
        />
      )}
      <div className="detail-metrics">
        <div className="detail-metric"><span>Pipeline status</span><strong className={`status-pill status-${normalizedStatus.toLowerCase().replace(/ /g, '-')}`}><span />{normalizedStatus}</strong></div>
        <div className="detail-metric"><span>Estimated machining time</span><strong>{quote && quote.total_time_minutes > 0 ? <>{quote.total_time_minutes.toFixed(1)} <small>min</small></> : 'Not estimated'}</strong></div>
        <div className="detail-metric"><span>Estimated quote</span><strong className="cost-value">{quote ? `$${quote.total_cost.toFixed(2)}` : 'Pending route approval'}</strong></div>
      </div>
      <div className="detail-content">
        <div className="detail-primary">
          {processPlanStatus !== 'not_generated' && (
            <section className="panel route-review-panel">
              <div className="panel-heading">
                <div><div className="eyebrow">MANUFACTURING ROUTE</div><h2>Review planned operations</h2></div>
                <span className={`review-state review-state-${processPlanStatus.replace('_', '-')}`}>{processPlanStatus.replace('_', ' ')}</span>
              </div>
              <div className="route-review-content">
                {operations.map((operation) => (
                  <div className="route-operation-editor" key={operation.id}>
                    <label className="form-field"><span>Operation</span><input value={operation.operation_name} onChange={(event) => updateOperation(operation.id, { operation_name: event.target.value })} /></label>
                    <label className="form-field"><span>Sequence</span><input type="number" min={1} step={1} value={operation.sequence_order} onChange={(event) => updateOperation(operation.id, { sequence_order: Number(event.target.value) })} /></label>
                    <label className="form-field"><span>Machine</span><input value={operation.machine_type ?? ''} onChange={(event) => updateOperation(operation.id, { machine_type: event.target.value || null })} /></label>
                    <label className="form-field"><span>Time / part (min; 0 = not estimated)</span><input type="number" min={0} step="any" value={operation.estimated_time_minutes} onChange={(event) => updateOperation(operation.id, { estimated_time_minutes: Number(event.target.value) })} /></label>
                    <label className="form-field"><span>Cost / part</span><input type="number" min={0} step="any" value={operation.estimated_cost} onChange={(event) => updateOperation(operation.id, { estimated_cost: Number(event.target.value) })} /></label>
                  </div>
                ))}
                <label className="form-field route-comment"><span>Engineer route review note</span><textarea rows={2} value={routeComment} onChange={(event) => setRouteComment(event.target.value)} /></label>
                <div className="inspection-decision-actions">
                  <button type="button" className="button button-secondary" disabled={savingRoute} onClick={() => void handleRouteReview('changes_requested')}><Save size={15} />Save changes requested</button>
                  <button type="button" className="button button-primary" disabled={savingRoute || operations.length === 0} onClick={() => void handleRouteReview('approved')}><Check size={15} />Approve route</button>
                </div>
              </div>
            </section>
          )}
          <FeatureMatrix features={features} />
          <OperationTimeline operations={operations} />
        </div>
        <aside className="detail-aside">
          <div className="panel quote-panel">
            <div className="eyebrow">COSTING ANALYSIS</div>
            <h2>{quote ? 'Preliminary quote' : 'Quotation'}</h2>
            <div className="quote-total">{quote ? `$${quote.total_cost.toFixed(2)}` : '—'}</div>
            <p>{quote ? `Estimate for ${quote.order_quantity} part(s), based on the approved manufacturing route.` : 'Approve the manufacturing route to generate a quantity-based estimate.'}</p>
            {quote?.assumptions.map((assumption) => <p className="quote-assumption" key={assumption}>{assumption}</p>)}
            {quote && quote.breakdown.length > 0 && (
              <div className="mt-4 space-y-3 border-t border-slate-200 pt-4">
                <h3 className="text-sm font-bold text-slate-800">Cost by process</h3>
                {quote.breakdown.map((item, index) => (
                  <div className="flex items-start justify-between gap-3 text-sm" key={`${item.operation}-${index}`}>
                    <div>
                      <p className="font-semibold text-slate-700">{item.operation}</p>
                      <p className="text-xs text-slate-500">${item.unit_cost.toFixed(2)} / part × {item.quantity}</p>
                    </div>
                    <strong className="shrink-0 text-slate-800">${item.extended_cost.toFixed(2)}</strong>
                  </div>
                ))}
              </div>
            )}
            <div className="quote-meta"><span>Estimated cycle time</span><strong>{quote && quote.total_time_minutes > 0 ? `${quote.total_time_minutes.toFixed(1)} min` : 'Not estimated'}</strong></div>
            <div className="quote-meta"><span>Extracted features</span><strong>{features.length}</strong></div>
            {processPlanStatus === 'approved' && (
              <button type="button" className="button button-primary button-wide quote-generate-button" disabled={creatingQuote} onClick={() => void handleCreateQuote()}>
                {creatingQuote ? <LoaderCircle className="spin" size={15} /> : <RefreshCw size={15} />}
                {quote ? 'Refresh estimate' : 'Generate estimate'}
              </button>
            )}
          </div>
        </aside>
      </div>
    </section>
  )
}

export default ProjectIntelligenceViewer
