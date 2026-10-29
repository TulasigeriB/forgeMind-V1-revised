import { useCallback, useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { ArrowLeft, BadgeDollarSign, Check, CheckCircle2, CircleAlert, FileText, LayoutDashboard, LoaderCircle, RefreshCw, Save, UploadCloud, Workflow, Trash2 } from 'lucide-react'
import axios from 'axios'
import { getApiErrorMessage, ProjectService, type EngineeringFile, type Feature, type ProcessOperation, type Project, type Quote, type ProjectAnalysisReview } from '../services/api'
import FeatureMatrix from '../components/FeatureMatrix'
import OperationTimeline from '../components/OperationTimeline'
import DrawingAnalysisPanel from '../components/DrawingAnalysisPanel'
import DrawingReviewWorkspace from '../components/DrawingReviewWorkspace'
import { useActiveProject } from '../store/ActiveProjectContext'
import { normalizeProjectStatus } from '../utils/projectStatus'
import type { DrawingAnalysis } from '../services/api'

type WorkspaceTab = 'overview' | 'files' | 'analysis' | 'process' | 'quote'

function statusClass(status: string) {
  return `status-pill status-${normalizeProjectStatus(status).toLowerCase().replace(/ /g, '-')}`
}

function errorMessage(error: unknown) {
  return getApiErrorMessage(error, 'Unable to load project intelligence.')
}

function ProjectIntelligenceViewer() {
  const { projectId } = useParams<{ projectId: string }>()
  const location = useLocation()
  const routeAnalysis = (location.state as { analysis?: DrawingAnalysis | null } | null)?.analysis ?? null
  const { setActiveProject } = useActiveProject()
  const [project, setProject] = useState<Project | null>(null)
  const [files, setFiles] = useState<EngineeringFile[]>([])
  const [features, setFeatures] = useState<Feature[]>([])
  const [operations, setOperations] = useState<ProcessOperation[]>([])
  const [quote, setQuote] = useState<Quote | null>(null)
  const [analysis, setAnalysis] = useState<DrawingAnalysis | null>(routeAnalysis)
  const [analysisReview, setAnalysisReview] = useState<ProjectAnalysisReview | null>(null)
  const [processPlanStatus, setProcessPlanStatus] = useState('not_generated')
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)
  const [savingRoute, setSavingRoute] = useState(false)
  const [creatingQuote, setCreatingQuote] = useState(false)
  const [routeComment, setRouteComment] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [activeTab, setActiveTab] = useState<WorkspaceTab>('overview')
  const [draggingFiles, setDraggingFiles] = useState(false)
  const [uploadingFiles, setUploadingFiles] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
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
      setAnalysis(response.analysis ?? routeAnalysis)
      setAnalysisReview(response.review)
      setProcessPlanStatus(response.process_plan_status)
      setRouteComment(response.route_review?.comment ?? '')
    } catch (requestError) {
      setError(errorMessage(requestError))
    } finally {
      setLoading(false)
    }
  }, [projectId, routeAnalysis, setActiveProject])

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

  async function handleDeleteFile(fileId: string) {
    if (!confirm('Are you sure you want to delete this drawing?')) return

    try {
      await ProjectService.deleteFile(fileId)
      setFiles((current) => current.filter((f) => f.id !== fileId))
      setNotice('Drawing deleted successfully.')
    } catch (error) {
      setError('Failed to delete drawing file.')
    }
  }
  async function uploadDrawings(selectedFiles: FileList) {
    if (!projectId) return
    const pdfFiles = Array.from(selectedFiles).filter((file) => file.name.toLowerCase().endsWith('.pdf'))
    if (pdfFiles.length !== selectedFiles.length) {
      setError('Only PDF drawings are supported.')
      return
    }
    if (pdfFiles.length === 0) return

    setUploadingFiles(true)
    setUploadProgress(0)
    setError('')
    setNotice('')
    try {
      for (let index = 0; index < pdfFiles.length; index += 1) {
        const response = await ProjectService.analyzeFile(projectId, pdfFiles[index], (progress) => {
          setUploadProgress(Math.round(((index + progress / 100) / pdfFiles.length) * 100))
        })
        setAnalysis(response.data)
      }
      setFiles((await ProjectService.getFiles(projectId)).data)
      setAnalysisReview(null)
      setProcessPlanStatus('not_generated')
      setOperations([])
      setFeatures([])
      setQuote(null)
      setProject((current) => current ? { ...current, status: 'analysis_ready' } : current)
      setNotice(`${pdfFiles.length} drawing${pdfFiles.length === 1 ? '' : 's'} uploaded and analyzed. Review the extracted features before continuing.`)
    } catch (uploadError) {
      setError(errorMessage(uploadError))
    } finally {
      setUploadingFiles(false)
    }
  }

  const rawStatus = project?.status.toLowerCase() ?? 'uploaded'
  const lifecycleSteps = ['Uploaded', 'Analysis', 'Engineer review', 'Route review', 'Costed', 'Quoted']
  const currentStep = rawStatus === 'quoted' ? 5
    : rawStatus === 'costed' ? 4
      : rawStatus === 'routing' || processPlanStatus !== 'not_generated' ? 3
        : rawStatus === 'analysis_approved' || rawStatus === 'analysis_ready' ? 2
          : rawStatus === 'analyzing' ? 1
            : 0

  if (loading) return <div className="loading-state page-loading"><span className="loading-spinner" /> Loading project intelligence…</div>
  if (error && !project) {
    return <section className="page-wrap"><div className="inline-error" role="alert"><CircleAlert size={18} />{error}<Link to="/projects">Back to projects</Link></div></section>
  }
  if (!project) return <section className="page-wrap"><div className="empty-panel"><h2>Project not found</h2><Link to="/projects">Return to the project explorer</Link></div></section>

  const tabs: { id: WorkspaceTab; label: string; icon: typeof LayoutDashboard }[] = [
    { id: 'overview', label: 'Overview', icon: LayoutDashboard },
    { id: 'files', label: 'Design files', icon: FileText },
    { id: 'analysis', label: 'Design analysis', icon: CheckCircle2 },
    { id: 'process', label: 'Manufacturing', icon: Workflow },
    { id: 'quote', label: 'Costing & quote', icon: BadgeDollarSign },
  ]

  return (
    <section className="page-wrap project-workspace">
      <div className="page-heading project-detail-heading">
        <div>
          <div className="eyebrow">PROJECT WORKSPACE</div>
          <h1>{project.part_number}</h1>
          <p>{project.material_spec || 'Material not specified'} <span className="detail-separator">/</span> Created {new Date(project.created_at).toLocaleDateString()}</p>
        </div>
        <button type="button" onClick={() => void handleAnalyze()} disabled={analyzing || files.length === 0} className="button button-primary">
          {analyzing ? <LoaderCircle className="spin" size={16} /> : <RefreshCw size={16} />}
          {analyzing ? 'Analyzing drawing…' : analysis ? 'Reanalyze drawing' : 'Analyze drawings'}
        </button>
      </div>
      {error && <div className="inline-error" role="alert"><CircleAlert size={18} />{error}</div>}
      {notice && <div className="inline-success" role="status">{notice}</div>}

      <section className="panel lifecycle-panel">
        <div className="lifecycle-header"><div><div className="eyebrow">PROJECT LIFECYCLE</div><h2>Work order progress</h2></div><span className={statusClass(normalizedStatus)}><span />{normalizedStatus}</span></div>
        <ol className="lifecycle-steps">
          {lifecycleSteps.map((step, index) => (
            <li className={`lifecycle-step${index < currentStep ? ' is-complete' : ''}${index === currentStep ? ' is-current' : ''}`} key={step}>
              <span className="lifecycle-step-marker">{index < currentStep ? <Check size={13} /> : index + 1}</span><span>{step}</span>
            </li>
          ))}
        </ol>
      </section>

      <div className="workspace-tabs" role="tablist" aria-label="Project workspace sections">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button type="button" role="tab" aria-selected={activeTab === id} aria-controls={`project-tab-${id}`} id={`project-tab-button-${id}`} className={`workspace-tab${activeTab === id ? ' workspace-tab-active' : ''}`} key={id} onClick={() => setActiveTab(id)}>
            <Icon size={16} />{label}
          </button>
        ))}
      </div>

      <div role="tabpanel" id={`project-tab-${activeTab}`} aria-labelledby={`project-tab-button-${activeTab}`} className="workspace-tab-content">
        {activeTab === 'overview' && (
          <div className="overview-tab">
            <div className="detail-metrics">
              <div className="detail-metric"><span>Associated customer</span><strong>{project.customer_name || 'Customer not linked'}</strong><small>RFQ {project.rfq_id.slice(0, 8).toUpperCase()}</small></div>
              <div className="detail-metric"><span>Linked drawings</span><strong>{files.length}</strong></div>
              <div className="detail-metric"><span>Calculated quote</span><strong className="cost-value">{quote ? `$${quote.total_cost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : 'Pending route approval'}</strong></div>
            </div>
            <div className="overview-grid">
              <section className="panel overview-summary"><div className="panel-heading"><div><div className="eyebrow">NEXT ACTION</div><h2>{analysis ? 'Review drawing intelligence' : files.length ? 'Run drawing analysis' : 'Add a drawing to begin'}</h2></div></div><div className="overview-action-body"><p>{analysis ? 'Validate extracted dimensions and engineer review flags before approving the manufacturing route.' : files.length ? 'The uploaded PDF drawings are ready for geometry and feature extraction.' : 'Upload a PDF engineering drawing to start this work order.'}</p><button className="button button-secondary" type="button" onClick={() => setActiveTab(analysis ? 'analysis' : 'files')}>{analysis ? 'Open analysis' : files.length ? 'View drawings' : 'Upload drawing'} <ArrowLeft className="button-arrow" size={15} /></button></div></section>
              <section className="panel overview-summary"><div className="panel-heading"><div><div className="eyebrow">QUOTE SNAPSHOT</div><h2>{quote ? 'Current estimate' : 'Not quoted yet'}</h2></div></div><div className="overview-action-body"><strong className="overview-quote-value">{quote ? `$${quote.total_cost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '—'}</strong><p>{quote ? `${quote.order_quantity} part(s) · ${quote.total_time_minutes.toFixed(1)} estimated minutes` : 'A quote is available after the manufacturing route has been approved.'}</p><button className="text-link" type="button" onClick={() => setActiveTab('quote')}>View costing <ArrowLeft className="button-arrow" size={14} /></button></div></section>
            </div>
            <DrawingAnalysisPanel analysis={analysis} />
          </div>
        )}

        {activeTab === 'files' && (
          <div className="files-tab">
            <section className="panel files-panel">
              <div className="panel-heading"><div><div className="eyebrow">ENGINEERING INPUTS</div><h2>Drawing files</h2></div><span className="file-count">{files.length} {files.length === 1 ? 'file' : 'files'}</span></div>
              <label className={`project-drop-zone${draggingFiles ? ' project-drop-zone-active' : ''}`} onDragOver={(event) => { event.preventDefault(); setDraggingFiles(true) }} onDragLeave={() => setDraggingFiles(false)} onDrop={(event) => { event.preventDefault(); setDraggingFiles(false); void uploadDrawings(event.dataTransfer.files) }}>
                <input type="file" accept=".pdf,application/pdf" multiple disabled={uploadingFiles} onChange={(event) => { if (event.target.files) void uploadDrawings(event.target.files); event.target.value = '' }} />
                <span className="upload-icon"><UploadCloud size={22} /></span><strong>{uploadingFiles ? 'Uploading drawings…' : 'Drop PDF drawings here or browse'}</strong><small>PDF files only · drawings are attached to this project</small>
                {uploadingFiles && <span className="upload-progress"><span style={{ width: `${uploadProgress}%` }} /></span>}
              </label>
              {files.length > 0 ? <div className="table-scroll"><table className="data-table file-table"><thead><tr><th>Drawing</th><th>File type</th><th>Version</th><th>Status</th><th>Uploaded</th><th></th></tr></thead><tbody>
                {files.map((file) => <tr key={file.id}><td><span className="file-table-name"><FileText size={17} /><strong>Drawing {file.version}</strong></span></td><td className="muted-cell">{file.file_type.toUpperCase()}</td><td className="muted-cell">v{file.version}</td><td><span className={`file-status file-status-${file.status.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`}>{file.status}</span></td><td className="muted-cell">{new Date(file.created_at).toLocaleDateString()}</td><td><button type="button" className="button button-ghost button-compact text-danger" onClick={() => void handleDeleteFile(file.id)} aria-label={`Delete ${file.storage_path}`}><Trash2 size={14} /></button></td></tr>)}
              </tbody></table></div> : <div className="empty-files"><FileText size={23} /><strong>No drawings uploaded</strong><span>Add one or more PDF files to start analysis.</span></div>}
            </section>
          </div>
        )}

        {activeTab === 'analysis' && (
          <div className="analysis-tab">
            {/* <DrawingAnalysisPanel analysis={analysis} /> */}
            {analysis && <DrawingReviewWorkspace projectId={project.id} analysis={analysis} review={analysisReview} files={files} onReviewSaved={(review) => void handleAnalysisReviewSaved(review)} />}
          </div>
        )}

        {activeTab === 'process' && (
          <div className="process-tab">
            {processPlanStatus !== 'not_generated' ? (
              <section className="panel route-review-panel">
                <div className="panel-heading"><div><div className="eyebrow">MANUFACTURING ROUTE</div><h2>Review planned operations</h2></div><span className={`review-state review-state-${processPlanStatus.replace('_', '-')}`}>{processPlanStatus.replace('_', ' ')}</span></div>
                <div className="route-review-content">
                  {operations.map((operation) => <div className="route-operation-editor" key={operation.id}>
                    <label className="form-field"><span>Operation</span><input value={operation.operation_name} onChange={(event) => updateOperation(operation.id, { operation_name: event.target.value })} /></label>
                    <label className="form-field"><span>Sequence</span><input type="number" min={1} step={1} value={operation.sequence_order} onChange={(event) => updateOperation(operation.id, { sequence_order: Number(event.target.value) })} /></label>
                    <label className="form-field"><span>Machine</span><input value={operation.machine_type ?? ''} onChange={(event) => updateOperation(operation.id, { machine_type: event.target.value || null })} /></label>
                    <label className="form-field"><span>Time / part (min)</span><input type="number" min={0} step="any" value={operation.estimated_time_minutes} onChange={(event) => updateOperation(operation.id, { estimated_time_minutes: Number(event.target.value) })} /></label>
                    <label className="form-field"><span>Cost / part</span><input type="number" min={0} step="any" value={operation.estimated_cost} onChange={(event) => updateOperation(operation.id, { estimated_cost: Number(event.target.value) })} /></label>
                  </div>)}
                  <label className="form-field route-comment"><span>Engineer route review note</span><textarea rows={2} value={routeComment} onChange={(event) => setRouteComment(event.target.value)} /></label>
                  <div className="inspection-decision-actions"><button type="button" className="button button-secondary" disabled={savingRoute} onClick={() => void handleRouteReview('changes_requested')}><Save size={15} />Save changes requested</button><button type="button" className="button button-primary" disabled={savingRoute || operations.length === 0} onClick={() => void handleRouteReview('approved')}><Check size={15} />Approve route</button></div>
                </div>
              </section>
            ) : <section className="panel route-empty"><Workflow size={25} /><h2>Manufacturing route not generated</h2><p>Approve the drawing analysis to generate a route for engineer review.</p><button className="button button-secondary" type="button" disabled={!analysis} onClick={() => setActiveTab('analysis')}>Review drawing analysis</button></section>}
            <FeatureMatrix features={features} />
            <OperationTimeline operations={operations} />
          </div>
        )}

        {activeTab === 'quote' && (
          <section className="panel quote-workspace" id="quotation-print">
            <div className="panel-heading"><div><div className="eyebrow">COSTING ANALYSIS</div><h2>{quote ? 'Preliminary quotation' : 'Quotation workspace'}</h2></div>
              <div className="quote-actions">{quote && <button type="button" className="button button-secondary button-compact" onClick={() => window.print()}><FileText size={15} />Export PDF</button>}
                {processPlanStatus === 'approved' && <button type="button" className="button button-primary button-compact" disabled={creatingQuote} onClick={() => void handleCreateQuote()}>{creatingQuote ? <LoaderCircle className="spin" size={15} /> : <RefreshCw size={15} />}{quote ? 'Refresh estimate' : 'Generate estimate'}</button>}
              </div>
            </div>
            {quote ? <>
              <div className="quote-workspace-total"><span>Total quoted value</span><strong>${quote.total_cost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong><small>Estimate for {quote.order_quantity} part(s)</small></div>
              <div className="table-scroll"><table className="data-table quote-table"><thead><tr><th>Operation</th><th>Machine</th><th>Qty</th><th>Unit cost</th><th>Extended cost</th><th>Time / part</th></tr></thead><tbody>
                {quote.breakdown.map((item, index) => <tr key={`${item.operation}-${index}`}><td><strong>{item.operation}</strong></td><td className="muted-cell">{item.machine_type ?? 'Not specified'}</td><td className="muted-cell">{item.quantity}</td><td className="muted-cell">${item.unit_cost.toFixed(2)}</td><td><strong>${item.extended_cost.toFixed(2)}</strong></td><td className="muted-cell">{item.unit_time_minutes.toFixed(1)} min</td></tr>)}
              </tbody></table></div>
              <div className="quote-summary-row"><span>Estimated machining time</span><strong>{quote.total_time_minutes.toFixed(1)} min</strong></div>
              {quote.assumptions.length > 0 && <div className="quote-assumptions"><h3>Estimate assumptions</h3>{quote.assumptions.map((assumption) => <p key={assumption}>{assumption}</p>)}</div>}
            </> : <div className="quote-empty"><BadgeDollarSign size={28} /><h3>Quote is not available yet</h3><p>Approve the manufacturing route to generate a quantity-based estimate from the backend costing model.</p>{processPlanStatus !== 'approved' && <button type="button" className="button button-secondary" onClick={() => setActiveTab('process')}>Review manufacturing route</button>}</div>}
          </section>
        )}
      </div>
    </section>
  )
}

export default ProjectIntelligenceViewer
