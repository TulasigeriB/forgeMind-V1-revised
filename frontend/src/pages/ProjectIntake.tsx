import { useState, type ChangeEvent, type DragEvent, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Check, FilePlus2, FileText, LoaderCircle, Trash2, UploadCloud } from 'lucide-react'
import axios from 'axios'
import { Link } from 'react-router-dom'
import { getApiErrorMessage, ProjectService, type DrawingAnalysis, type Project, type ProjectPriority } from '../services/api'
import { useActiveProject } from '../store/ActiveProjectContext'

const acceptedExtensions = ['.pdf']

function getRequestError(error: unknown) {
  return getApiErrorMessage(error, 'Project intake failed. Please try again.')
}

function ProjectIntake() {
  const [customerName, setCustomerName] = useState('')
  const [customerEmail, setCustomerEmail] = useState('')
  const [partNumber, setPartNumber] = useState('')
  const [material, setMaterial] = useState('')
  const [quantity, setQuantity] = useState(1)
  const [priority, setPriority] = useState<ProjectPriority>('normal')
  const [files, setFiles] = useState<File[]>([])
  const [error, setError] = useState('')
  const [createdProject, setCreatedProject] = useState<Project | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [dragging, setDragging] = useState(false)
  const navigate = useNavigate()
  const { setActiveProject } = useActiveProject()

  function appendFiles(selectedFiles: FileList | File[]) {
    const validFiles: File[] = []
    const invalidFiles: string[] = []
    Array.from(selectedFiles).forEach((file) => {
      const extension = `.${file.name.split('.').pop()?.toLowerCase() ?? ''}`
      if (acceptedExtensions.includes(extension)) validFiles.push(file)
      else invalidFiles.push(file.name)
    })
    setFiles((current) => [...current, ...validFiles.filter((file) => !current.some((existing) => existing.name === file.name && existing.size === file.size))])
    setError(invalidFiles.length ? `Unsupported file type: ${invalidFiles.join(', ')}. PDF drawings are supported; STEP analysis is planned.` : '')
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    if (event.target.files) appendFiles(event.target.files)
    event.target.value = ''
  }

  function handleDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault()
    setDragging(false)
    appendFiles(event.dataTransfer.files)
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setCreatedProject(null)
    setSubmitting(true)

    try {
      let customer
      try {
        customer = (await ProjectService.getCustomerByEmail(customerEmail.trim())).data
      } catch (lookupError) {
        if (!axios.isAxiosError(lookupError) || lookupError.response?.status !== 404) throw lookupError
        customer = (await ProjectService.createCustomer({
          name: customerName.trim(),
          contact_email: customerEmail.trim(),
        })).data
      }
      const rfq = await ProjectService.createRfq({
        customer_id: customer.id,
        quantity,
        priority,
      })
      const projectResponse = await ProjectService.createProject({
        rfq_id: rfq.data.id,
        part_number: partNumber.trim(),
        material_spec: material.trim(),
      })
      const project = projectResponse.data
      setCreatedProject(project)

      let analysis: DrawingAnalysis | null = null
      for (const file of files) {
        analysis = (await ProjectService.analyzeFile(project.id, file)).data
      }

      setActiveProject(project)
      navigate(`/project/${project.id}`, { state: { analysis } })
    } catch (requestError) {
      setError(getRequestError(requestError))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="page-wrap intake-wrap">
      <div className="page-heading intake-heading">
        <div>
          <Link to="/projects" className="back-link"><ArrowLeft size={15} /> Project Explorer</Link>
          <div className="eyebrow">NEW WORK ORDER</div>
          <h1>Project Intake</h1>
          <p>Capture customer requirements and drawings to create a manufacturing project.</p>
        </div>
        <div className="intake-step"><span>01</span><div><strong>Project details</strong><small>INTAKE &amp; ANALYSIS</small></div></div>
      </div>

      <form className="intake-grid" onSubmit={handleSubmit}>
        <div className="intake-main">
          <section className="panel form-panel">
            <div className="form-section-heading"><span className="section-number">01</span><div><h2>Customer &amp; part details</h2><p>Project information is attached to a customer RFQ.</p></div></div>
            <div className="form-grid">
              <label className="form-field">
                <span>Customer name <b>*</b></span>
                <input required value={customerName} onChange={(event) => setCustomerName(event.target.value)} placeholder="e.g. Acme Manufacturing" />
              </label>
              <label className="form-field">
                <span>Customer email <b>*</b></span>
                <input required type="email" value={customerEmail} onChange={(event) => setCustomerEmail(event.target.value)} placeholder="buyer@company.com" />
              </label>
              <label className="form-field">
                <span>Part number <b>*</b></span>
                <input required value={partNumber} onChange={(event) => setPartNumber(event.target.value)} placeholder="e.g. DE-BRACKET-001" />
              </label>
              <label className="form-field">
                <span>Material specification <b>*</b></span>
                <input required value={material} onChange={(event) => setMaterial(event.target.value)} placeholder="e.g. 316L Stainless Steel" />
              </label>
              <label className="form-field">
                <span>Order quantity <b>*</b></span>
                <input required type="number" min={1} step={1} value={quantity} onChange={(event) => setQuantity(Number(event.target.value))} />
              </label>
              <label className="form-field">
                <span>Priority</span>
                <select value={priority} onChange={(event) => setPriority(event.target.value as ProjectPriority)}>
                  <option value="low">Low</option>
                  <option value="normal">Normal</option>
                  <option value="high">High</option>
                  <option value="urgent">Urgent</option>
                </select>
              </label>
            </div>
          </section>

          <section className="panel form-panel">
          <div className="form-section-heading"><span className="section-number">02</span><div><h2>Engineering drawings</h2><p>Upload PDF drawings for text and vector extraction.</p></div></div>
            <label
              className={`drop-zone${dragging ? ' drop-zone-active' : ''}`}
              onDragOver={(event) => { event.preventDefault(); setDragging(true) }}
              onDragLeave={() => setDragging(false)}
              onDrop={handleDrop}
            >
              <input className="visually-hidden" type="file" accept=".pdf,application/pdf" multiple aria-label="Choose PDF engineering drawings" onChange={handleFileChange} />
              <span className="upload-icon"><UploadCloud size={23} /></span>
              <strong>Drop drawings here or <span>browse files</span></strong>
              <small>PDF drawings only <i>·</i> Multiple files supported</small>
            </label>
            {files.length > 0 && (
              <ul className="file-list">
                {files.map((file) => (
                  <li key={`${file.name}-${file.size}`}>
                    <span className="file-type-icon">{file.name.toLowerCase().endsWith('.pdf') ? <FileText size={17} /> : <FilePlus2 size={17} />}</span>
                    <span className="file-name"><strong>{file.name}</strong><small>{(file.size / 1024 / 1024).toFixed(2)} MB</small></span>
                    <button type="button" className="remove-file" aria-label={`Remove ${file.name}`} onClick={() => setFiles((current) => current.filter((item) => item !== file))}><Trash2 size={16} /></button>
                  </li>
                ))}
              </ul>
            )}
          </section>
          {error && (
            <div className="inline-error intake-error" role="alert">
              <span>{error}</span>
              {createdProject && <Link to={`/project/${createdProject.id}`}>Open created project</Link>}
            </div>
          )}
        </div>

        <aside className="intake-aside">
          <div className="panel analysis-panel">
            <div className="analysis-icon"><UploadCloud size={19} /></div>
            <div className="eyebrow">NEXT STEP</div>
            <h2>Drawing analysis</h2>
            <p>PDF drawings are saved to the project and analyzed immediately for engineer review.</p>
            <ul className="analysis-checklist">
              <li><Check size={14} /> Create or match customer</li>
              <li><Check size={14} /> Register project and RFQ</li>
              <li><Check size={14} /> Analyze and save PDF drawings</li>
            </ul>
            <button type="submit" className="button button-primary button-wide" disabled={submitting || files.length === 0}>
              {submitting ? <><LoaderCircle className="spin" size={17} /> Creating project…</> : <>Create &amp; analyze drawings <ArrowLeft className="arrow-forward" size={16} /></>}
            </button>
            {files.length === 0 && <small className="button-hint">Add at least one PDF drawing to continue.</small>}
          </div>
          <div className="security-note"><span>i</span><p>File upload requires a valid ForgeMind access token in your browser session.</p></div>
        </aside>
      </form>
    </section>
  )
}

export default ProjectIntake
