import { useEffect, useMemo, useRef, useState } from 'react'
import { Document, Page, pdfjs } from 'react-pdf'
import pdfWorkerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'
import { Check, ChevronLeft, ChevronRight, CircleAlert, FileText, Maximize2, Save, X, ZoomIn, ZoomOut } from 'lucide-react'
import {
  ProjectService,
  type AnalysisReviewDecision,
  type DrawingAnalysis,
  type EngineeringFile,
  type ProjectAnalysisReview,
  type ReviewDecisionKind,
} from '../services/api'

import 'react-pdf/dist/Page/AnnotationLayer.css'
import 'react-pdf/dist/Page/TextLayer.css'

pdfjs.GlobalWorkerOptions.workerSrc = `${pdfWorkerUrl}?v=${pdfjs.version}`

interface ReviewTarget {
  id: string
  label: string
  callout: string
  feature: string
  value: number | null
  units: 'mm' | 'inches' | null
  confidence: number
  page: number | null
  box: [number, number, number, number] | null
  pageWidth: number | null
  pageHeight: number | null
}

interface DraftDecision {
  decision: ReviewDecisionKind | 'pending'
  correctedCallout: string
  correctedValue: string
  correctedFeature: string
  correctedUnits: 'mm' | 'inches' | ''
  comment: string
}

function record(value: unknown): Record<string, unknown> | null {
  return typeof value === 'object' && value !== null ? value as Record<string, unknown> : null
}

function text(value: unknown, fallback = '') {
  return typeof value === 'string' ? value : fallback
}

function number(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function bboxFromDimension(value: unknown): Pick<ReviewTarget, 'page' | 'box' | 'pageWidth' | 'pageHeight'> {
  const box = record(value)
  if (!box) return { page: null, box: null, pageWidth: null, pageHeight: null }
  const coordinates = [number(box.x0), number(box.y0), number(box.x1), number(box.y1)]
  if (coordinates.some((coordinate) => coordinate === null)) {
    return { page: number(box.page), box: null, pageWidth: number(box.page_width), pageHeight: number(box.page_height) }
  }
  return {
    page: number(box.page),
    box: coordinates as [number, number, number, number],
    pageWidth: number(box.page_width),
    pageHeight: number(box.page_height),
  }
}

function buildTargets(analysis: DrawingAnalysis): ReviewTarget[] {
  const targets: ReviewTarget[] = []
  Object.entries(analysis.manufacturing_operations).forEach(([operation, features]) => {
    features.forEach((feature, featureIndex) => {
      feature.dimensions.forEach((dimension, dimensionIndex) => {
        targets.push({
          id: `manufacturing_operations.${operation}.${featureIndex}.dimensions.${dimensionIndex}`,
          label: `${operation} · ${feature.feature}`,
          callout: dimension.callout,
          feature: feature.feature,
          value: dimension.value,
          units: dimension.units === 'inches' ? 'inches' : 'mm',
          confidence: dimension.confidence,
          ...bboxFromDimension(dimension.bounding_box),
        })
      })
    })
  })

  analysis.precision_fits.forEach((unknownFit, index) => {
    const fit = record(unknownFit)
    if (!fit) return
    const nominalSize = text(fit.nominal_size)
    const nominalValue = Number.parseFloat(nominalSize)
    const matchingDimension = Object.values(analysis.manufacturing_operations)
      .flat()
      .flatMap((feature) => feature.dimensions)
      .find((dimension) => dimension.callout === fit.callout || (
        Number.isFinite(nominalValue) && dimension.value === nominalValue
      ))
    targets.push({
      id: `precision_fits.${index}`,
      label: `Precision fit · ${text(fit.fit, 'limit tolerance')}`,
      callout: text(fit.callout),
      feature: text(fit.fit, 'precision fit'),
      value: Number.isFinite(nominalValue) ? nominalValue : null,
      units: nominalSize.includes('inches') ? 'inches' : 'mm',
      confidence: number(fit.confidence) ?? 0,
      ...(matchingDimension
        ? bboxFromDimension(matchingDimension.bounding_box)
        : { page: null, box: null, pageWidth: null, pageHeight: null }),
    })
  })

  analysis.geometric_tolerances.forEach((unknownTolerance, index) => {
    const tolerance = record(unknownTolerance)
    if (!tolerance) return
    const coordinates = Array.isArray(tolerance.bounding_box)
      ? tolerance.bounding_box.slice(0, 4).map(number)
      : null
    const box = coordinates && coordinates.every((coordinate) => coordinate !== null)
      ? coordinates as [number, number, number, number]
      : null
    targets.push({
      id: `geometric_tolerances.${index}`,
      label: `GD&T · ${text(tolerance.feature, 'geometric tolerance')}`,
      callout: text(tolerance.callout),
      feature: text(tolerance.feature, 'geometric tolerance'),
      value: number(tolerance.tolerance_value),
      units: null,
      confidence: number(tolerance.confidence) ?? 0,
      page: number(tolerance.page),
      box,
      pageWidth: number(tolerance.page_width),
      pageHeight: number(tolerance.page_height),
    })
  })

  analysis.form_features.forEach((unknownFeature, index) => {
    const feature = record(unknownFeature)
    if (!feature) return
    const dimensions = Array.isArray(feature.bounding_box) ? feature.bounding_box : null
    const coordinates = dimensions?.slice(0, 4).map(number)
    const box = coordinates && coordinates.every((coordinate) => coordinate !== null)
      ? coordinates as [number, number, number, number]
      : null
    targets.push({
      id: `form_features.${index}`,
      label: `Form feature · ${text(feature.feature)}`,
      callout: text(feature.callout),
      feature: text(feature.feature),
      value: number(feature.value) ?? number(feature.size),
      units: feature.units === 'inches' ? 'inches' : feature.units === 'mm' ? 'mm' : null,
      confidence: number(feature.confidence) ?? 0,
      page: number(feature.page),
      box,
      pageWidth: number(feature.page_width),
      pageHeight: number(feature.page_height),
    })
  })
  return targets
}

function makeDraft(target: ReviewTarget, existing?: AnalysisReviewDecision): DraftDecision {
  return {
    decision: existing?.decision ?? 'pending',
    correctedCallout: existing?.corrected_callout ?? target.callout,
    correctedValue: existing?.corrected_value?.toString() ?? target.value?.toString() ?? '',
    correctedFeature: existing?.corrected_feature ?? target.feature,
    correctedUnits: existing?.corrected_units ?? target.units ?? '',
    comment: existing?.comment ?? '',
  }
}

function DrawingReviewWorkspace({
  projectId,
  analysis,
  review,
  files,
  onReviewSaved,
}: {
  projectId: string
  analysis: DrawingAnalysis
  review: ProjectAnalysisReview | null
  files: EngineeringFile[]
  onReviewSaved: (review: ProjectAnalysisReview) => void
}) {
  const pdfFiles = files.filter((file) => file.file_type.toUpperCase() === 'PDF')
  const targets = useMemo(() => buildTargets(analysis), [analysis])
  const [selectedTargetId, setSelectedTargetId] = useState('')
  const [selectedFileId, setSelectedFileId] = useState(pdfFiles[0]?.id ?? '')
  const [pdfUrl, setPdfUrl] = useState('')
  const [pdfError, setPdfError] = useState('')
  const [pageNumber, setPageNumber] = useState(1)
  const [pageCount, setPageCount] = useState(0)
  const [renderWidth, setRenderWidth] = useState(900)
  const [zoom, setZoom] = useState(1)
  const canvasRef = useRef<HTMLDivElement>(null)
  const [drafts, setDrafts] = useState<Record<string, DraftDecision>>({})
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState('')
  const [saveNotice, setSaveNotice] = useState('')

  useEffect(() => {
    setSelectedTargetId((current) => targets.some((target) => target.id === current) ? current : targets[0]?.id ?? '')
    const existing = new Map(review?.decisions.map((decision) => [decision.target_id, decision]) ?? [])
    setDrafts(Object.fromEntries(targets.map((target) => [target.id, makeDraft(target, existing.get(target.id))])))
  }, [targets, review])

  useEffect(() => {
    const element = canvasRef.current
    if (!element) return
    const observer = new ResizeObserver(([entry]) => {
      setRenderWidth(Math.max(320, entry.contentRect.width - 24))
    })
    observer.observe(element)
    return () => observer.disconnect()
  }, [pdfUrl])

  useEffect(() => {
    if (pdfFiles.length && !pdfFiles.some((file) => file.id === selectedFileId)) {
      setSelectedFileId(pdfFiles[0].id)
    }
  }, [files, pdfFiles, selectedFileId])

  useEffect(() => {
    if (!selectedFileId) {
      setPdfUrl('')
      return
    }
    let objectUrl = ''
    let cancelled = false
    setPdfError('')
    void ProjectService.getFileContent(selectedFileId).then(({ data }) => {
      if (cancelled) return
      objectUrl = URL.createObjectURL(data)
      setPdfUrl(objectUrl)
    }).catch(() => {
      if (!cancelled) setPdfError('Could not load the source PDF. Check that the stored drawing file is available.')
    })
    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
      setPdfUrl('')
    }
  }, [selectedFileId])

  const selectedTarget = targets.find((target) => target.id === selectedTargetId) ?? null
  const pageRenderWidth = Math.max(320, Math.min(renderWidth * zoom, 1800))
  const currentPageTargets = targets.filter((target) => target.page === pageNumber && target.box && target.pageWidth && target.pageHeight)
  const allReviewed = targets.length > 0 && targets.every((target) => drafts[target.id]?.decision !== 'pending')

  function updateDraft(targetId: string, patch: Partial<DraftDecision>) {
    setDrafts((current) => ({ ...current, [targetId]: { ...current[targetId], ...patch } }))
  }

  async function saveReview(status: 'in_review' | 'approved' | 'changes_requested') {
    setSaving(true)
    setSaveError('')
    setSaveNotice('')
    try {
      if (status === 'approved' && !allReviewed) {
        throw new Error('Review every extracted callout before approving the analysis.')
      }
      const decisions: AnalysisReviewDecision[] = targets.flatMap((target) => {
        const draft = drafts[target.id]
        if (!draft || draft.decision === 'pending') return []
        const decision: AnalysisReviewDecision = {
          target_id: target.id,
          decision: draft.decision,
          comment: draft.comment || null,
        }
        if (draft.decision === 'corrected') {
          if (draft.correctedCallout !== target.callout) decision.corrected_callout = draft.correctedCallout
          if (draft.correctedValue && Number(draft.correctedValue) !== target.value) {
            decision.corrected_value = Number(draft.correctedValue)
          }
          if (draft.correctedFeature !== target.feature) decision.corrected_feature = draft.correctedFeature
          if (draft.correctedUnits && draft.correctedUnits !== target.units) decision.corrected_units = draft.correctedUnits
        }
        return [decision]
      })
      const { data } = await ProjectService.saveAnalysisReview(projectId, status, decisions)
      onReviewSaved(data.review)
      setSaveNotice(status === 'approved' ? 'Drawing analysis approved. Manufacturing routes can now be generated.' : 'Engineer review saved.')
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : 'Could not save the engineer review.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="panel inspection-workspace">
      <div className="panel-heading">
        <div><div className="eyebrow">ENGINEER INSPECTION</div><h2>Drawing callout review</h2></div>
        <span className={`review-state review-state-${review?.status ?? 'pending'}`}>{review?.status?.replace('_', ' ') ?? 'pending review'}</span>
      </div>
      <div className="inspection-layout">
        <div className="inspection-drawing">
          <div className="inspection-toolbar">
            <label>
              <FileText size={15} />
              <select aria-label="Select drawing PDF" value={selectedFileId} onChange={(event) => setSelectedFileId(event.target.value)}>
                {pdfFiles.map((file) => <option key={file.id} value={file.id}>{file.storage_path.split(/[\\/]/).pop()}</option>)}
              </select>
            </label>
            <div className="inspection-page-controls">
              <button type="button" className="button button-secondary button-compact" disabled={pageNumber <= 1} onClick={() => setPageNumber((page) => Math.max(1, page - 1))} aria-label="Previous PDF page"><ChevronLeft size={15} /></button>
              <span>{pageNumber} / {pageCount || '—'}</span>
              <button type="button" className="button button-secondary button-compact" disabled={pageNumber >= pageCount} onClick={() => setPageNumber((page) => Math.min(pageCount, page + 1))} aria-label="Next PDF page"><ChevronRight size={15} /></button>
              <span className="inspection-toolbar-divider" />
              <button type="button" className="button button-secondary button-compact" disabled={zoom <= 0.5} onClick={() => setZoom((value) => Math.max(0.5, Number((value - 0.25).toFixed(2))))} aria-label="Zoom out"><ZoomOut size={15} /></button>
              <span className="inspection-zoom-level">{Math.round(zoom * 100)}%</span>
              <button type="button" className="button button-secondary button-compact" disabled={zoom >= 2} onClick={() => setZoom((value) => Math.min(2, Number((value + 0.25).toFixed(2))))} aria-label="Zoom in"><ZoomIn size={15} /></button>
              <button type="button" className="button button-secondary button-compact" disabled={zoom === 1} onClick={() => setZoom(1)} aria-label="Fit page"><Maximize2 size={15} /></button>
            </div>
          </div>
          {pdfError && <div className="inline-error" role="alert"><CircleAlert size={16} />{pdfError}</div>}
          {!pdfFiles.length && <div className="inspection-no-pdf">No uploaded PDF is available for visual review.</div>}
          {pdfUrl && (
            <div className="inspection-canvas" ref={canvasRef}>
              <Document
                file={pdfUrl}
                onLoadSuccess={({ numPages }) => { setPageCount(numPages); setPageNumber((page) => Math.min(page, numPages)) }}
                onLoadError={() => setPdfError('The uploaded file could not be rendered as a PDF.')}
                error={<div className="inspection-pdf-message inspection-pdf-error">This drawing could not be rendered. Check that it is a valid PDF and reload the project.</div>}
                loading={<div className="loading-state"><span className="loading-spinner" />Rendering drawing…</div>}
              >
                <div className="drawing-page-shell" style={{ width: pageRenderWidth }}>
                  <Page
                    pageNumber={pageNumber}
                    width={pageRenderWidth}
                    renderTextLayer={false}
                    renderAnnotationLayer={false}
                  />
                  <div className="drawing-callout-overlays">
                    {currentPageTargets.map((target) => {
                      const [x0, y0, x1, y1] = target.box!
                      return (
                        <button
                          key={target.id}
                          type="button"
                          className={`drawing-callout-overlay${target.id === selectedTargetId ? ' drawing-callout-overlay-active' : ''}`}
                          style={{
                            left: `${x0 / target.pageWidth! * 100}%`,
                            top: `${y0 / target.pageHeight! * 100}%`,
                            width: `${Math.max((x1 - x0) / target.pageWidth! * 100, 1.2)}%`,
                            height: `${Math.max((y1 - y0) / target.pageHeight! * 100, 1.2)}%`,
                          }}
                          aria-label={`Review callout ${target.callout}`}
                          title={`${targets.indexOf(target) + 1}. ${target.callout}`}
                          onClick={() => setSelectedTargetId(target.id)}
                        >
                          <span>{targets.indexOf(target) + 1}</span>
                        </button>
                      )
                    })}
                  </div>
                </div>
              </Document>
            </div>
          )}
        </div>
        <aside className="inspection-callouts">
          <h3>Extracted callouts <span>{targets.length}</span></h3>
          <div className="inspection-target-list">
            {targets.map((target) => {
              const draft = drafts[target.id]
              return (
                <>
                  <span key={target.id} className="inspection-target-index">{targets.indexOf(target) + 1}</span>
                  <button
                    type="button"
                    key={target.id}
                    className={`inspection-target${target.id === selectedTargetId ? ' inspection-target-active' : ''}`}
                    onClick={() => {
                      setSelectedTargetId(target.id)
                      if (target.page) setPageNumber(target.page)
                    }}
                  >
                    <strong>{target.callout || target.feature}</strong>
                    <span>{target.label}</span>
                    <small>{Math.round(target.confidence * 100)}% confidence · {draft?.decision ?? 'not reviewed'}</small>
                  </button>
                </>
              )
            })}
            {!targets.length && <p className="analysis-muted">No reviewable callouts were extracted.</p>}
          </div>
          {selectedTarget && drafts[selectedTarget.id] && (
            <div className="inspection-editor">
              <h3>Review selected callout</h3>
              <label className="form-field">
                <span>Callout text</span>
                <input value={drafts[selectedTarget.id].correctedCallout} onChange={(event) => updateDraft(selectedTarget.id, { correctedCallout: event.target.value, decision: 'corrected' })} />
              </label>
              <div className="inspection-edit-grid">
                <label className="form-field">
                  <span>Numeric value</span>
                  <input type="number" step="any" value={drafts[selectedTarget.id].correctedValue} onChange={(event) => updateDraft(selectedTarget.id, { correctedValue: event.target.value, decision: 'corrected' })} />
                </label>
                <label className="form-field">
                  <span>Units</span>
                  <select value={drafts[selectedTarget.id].correctedUnits} onChange={(event) => updateDraft(selectedTarget.id, { correctedUnits: event.target.value as 'mm' | 'inches' | '', decision: 'corrected' })}>
                    <option value="">Not applicable</option>
                    <option value="mm">mm</option>
                    <option value="inches">inches</option>
                  </select>
                </label>
              </div>
              <label className="form-field">
                <span>Feature classification</span>
                <input value={drafts[selectedTarget.id].correctedFeature} onChange={(event) => updateDraft(selectedTarget.id, { correctedFeature: event.target.value, decision: 'corrected' })} />
              </label>
              <label className="form-field">
                <span>Review note</span>
                <textarea value={drafts[selectedTarget.id].comment} onChange={(event) => updateDraft(selectedTarget.id, { comment: event.target.value })} rows={2} />
              </label>
              <div className="inspection-decision-actions">
                <button type="button" className="button button-secondary button-compact" onClick={() => updateDraft(selectedTarget.id, { decision: 'accepted' })}><Check size={14} /> Accept</button>
                <button type="button" className="button button-secondary button-compact" onClick={() => updateDraft(selectedTarget.id, { decision: 'rejected' })}><X size={14} /> Reject</button>
              </div>
            </div>
          )}
          <div className="inspection-save-actions">
            {saveError && <div className="inline-error" role="alert"><CircleAlert size={15} />{saveError}</div>}
            {saveNotice && <div className="inline-success">{saveNotice}</div>}
            <button type="button" className="button button-secondary" disabled={saving} onClick={() => void saveReview('in_review')}><Save size={15} />Save review</button>
            <button type="button" className="button button-primary" disabled={saving || !allReviewed} onClick={() => void saveReview('approved')}><Check size={15} />Approve analysis</button>
            {!allReviewed && <small>Accept, correct, or reject every extracted callout to approve.</small>}
          </div>
        </aside>
      </div>
    </section>
  )
}

export default DrawingReviewWorkspace
