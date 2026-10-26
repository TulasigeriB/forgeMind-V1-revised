import { AlertTriangle, CheckCircle2, FileJson2 } from 'lucide-react'
import type { DrawingAnalysis, DrawingAnalysisFeature } from '../services/api'

function DimensionList({ features }: { features: DrawingAnalysisFeature[] }) {
  if (features.length === 0) return <p className="analysis-muted">No callouts extracted for this operation type.</p>

  return (
    <div className="analysis-feature-list">
      {features.map((feature, index) => (
        <article key={`${feature.feature}-${index}`} className="analysis-feature">
          <div className="analysis-feature-title">
            <strong>{feature.feature}</strong>
            {typeof feature.quantity === 'number' && <span>QTY {feature.quantity}</span>}
          </div>
          {feature.dimensions.map((dimension, dimensionIndex) => (
            <div key={`${dimension.dimension_line_ref}-${dimensionIndex}`} className="analysis-dimension">
              <code>{dimension.callout}</code>
              <span>{dimension.type}{dimension.value !== null ? ` · ${dimension.value} ${dimension.units}` : ''}</span>
              <span className={dimension.needs_engineer_confirmation ? 'analysis-confidence review-needed' : 'analysis-confidence'}>
                {Math.round(dimension.confidence * 100)}% confidence
                {dimension.needs_engineer_confirmation && ' · review'}
              </span>
            </div>
          ))}
        </article>
      ))}
    </div>
  )
}

function DrawingAnalysisPanel({ analysis }: { analysis: DrawingAnalysis | null }) {
  if (!analysis) {
    return (
      <section className="panel drawing-analysis-panel">
        <div className="panel-heading">
          <div><div className="eyebrow">DRAWING INTELLIGENCE</div><h2>Engineering drawing analysis</h2></div>
        </div>
        <div className="analysis-empty">
          <FileJson2 size={20} />
          <span>No drawing analysis is available yet. Upload a searchable PDF (or configure Tesseract OCR for scanned PDFs), then start drawing extraction.</span>
        </div>
      </section>
    )
  }

  const metadata = analysis.metadata_and_notes[0]
  const classification = metadata?.component_classification as Record<string, unknown> | undefined
  const surfaceSpecifications = metadata?.surface_specifications as Record<string, unknown>[] | undefined
  const heatTreatments = metadata?.heat_treatments as Record<string, unknown>[] | undefined
  const surfaceTreatments = metadata?.surface_treatments as Record<string, unknown>[] | undefined
  const fai = analysis.quality_document_templates.first_article_inspection as Record<string, unknown> | undefined
  const ppap = analysis.quality_document_templates.ppap as Record<string, unknown> | undefined

  return (
    <section className="panel drawing-analysis-panel">
      <div className="panel-heading">
        <div><div className="eyebrow">DRAWING INTELLIGENCE</div><h2>Engineering drawing analysis</h2></div>
        <span className="analysis-units">{analysis.units.toUpperCase()}</span>
      </div>
      <div className="analysis-metadata">
        <div><span>Part identifier</span><strong>{analysis.part_identifier}</strong></div>
        <div><span>Drawing description</span><strong>{String(metadata?.drawing_description ?? 'Not identified')}</strong></div>
        <div><span>Material</span><strong>{String(metadata?.material ?? 'Not identified')}</strong></div>
        <div><span>Component / stock</span><strong>{String(metadata?.component_type ?? classification?.shape ?? 'Unclassified')} · {String(classification?.stock_form ?? 'stock unspecified')}</strong></div>
      </div>
      <div className="analysis-sections">
        <section><h3>Turning dimensions</h3><DimensionList features={analysis.manufacturing_operations.turning} /></section>
        <section><h3>Milling dimensions &amp; patterns</h3><DimensionList features={analysis.manufacturing_operations.milling} /></section>
        <section>
          <h3>Precision fits &amp; tolerances</h3>
          {analysis.precision_fits.length === 0 ? <p className="analysis-muted">No fit callouts extracted.</p> : (
            <div className="analysis-callout-list">
              {analysis.precision_fits.map((fit, index) => (
                <div key={index}><code>{String(fit.callout)}</code><span>{String(fit.fit ?? 'Limit tolerance')}</span><span>{Math.round(Number(fit.confidence) * 100)}% confidence</span></div>
              ))}
            </div>
          )}
        </section>
        <section>
          <h3>Geometric tolerances</h3>
          {analysis.geometric_tolerances.length === 0 ? <p className="analysis-muted">No GD&amp;T callouts extracted.</p> : (
            <div className="analysis-callout-list">
              {analysis.geometric_tolerances.map((tolerance, index) => (
                <div key={index}>
                  <code>{String(tolerance.callout)}</code>
                  <span>{String(tolerance.feature)}{tolerance.tolerance_value != null ? ` · ${String(tolerance.tolerance_value)} ${analysis.units}` : ''}</span>
                  <span>{Array.isArray(tolerance.datum_references) && tolerance.datum_references.length ? `Datums ${tolerance.datum_references.join(' · ')}` : 'Datum references require review'}</span>
                </div>
              ))}
            </div>
          )}
        </section>
        <section>
          <h3>Form &amp; surface features</h3>
          {analysis.form_features.length === 0 ? <p className="analysis-muted">No form callouts extracted.</p> : (
            <div className="analysis-callout-list">
              {analysis.form_features.map((feature, index) => (
                <div key={index}><code>{String(feature.callout)}</code><span>{String(feature.feature)}</span><span>{Math.round(Number(feature.confidence) * 100)}% confidence</span></div>
              ))}
            </div>
          )}
          {(surfaceSpecifications?.length || heatTreatments?.length || surfaceTreatments?.length) ? (
            <div className="analysis-callout-list">
              {[...(surfaceSpecifications ?? []), ...(heatTreatments ?? []), ...(surfaceTreatments ?? [])].map((specification, index) => (
                <div key={index}>
                  <code>{String(specification.callout)}</code>
                  <span>{String(specification.feature ?? specification.hardness_specification ?? specification.treatment)}</span>
                  {specification.value != null && <span>{String(specification.parameter)} {String(specification.value)} {String(specification.units ?? '')}</span>}
                </div>
              ))}
            </div>
          ) : null}
        </section>
        <section>
          <h3>CTQ inspection checklist <span>{analysis.inspection_checklist.length}</span></h3>
          {analysis.inspection_checklist.length === 0 ? <p className="analysis-muted">No inspection checks were derived from explicit callouts.</p> : (
            <ul className="analysis-review-list">
              {analysis.inspection_checklist.map((item, index) => (
                <li key={index}><CheckCircle2 size={15} /><span>{String(item.requirement)} · {String(item.measurement_method)}</span><small>{String(item.status)}</small></li>
              ))}
            </ul>
          )}
          <p className="analysis-muted">Quality document drafts: FAI {String(fai?.status ?? 'unavailable')} · PPAP {String(ppap?.status ?? 'unavailable')}. Engineer approval is required before production use.</p>
        </section>
        <section className="analysis-review-section">
          <h3>Engineer review flags <span>{analysis.review_flags.length}</span></h3>
          {analysis.review_flags.length === 0 ? (
            <p className="analysis-clear"><CheckCircle2 size={15} /> No review flags were raised.</p>
          ) : (
            <ul className="analysis-review-list">
              {analysis.review_flags.map((flag, index) => (
                <li key={index}><AlertTriangle size={15} /><span>{String(flag.issue)}</span><small>{Math.round(Number(flag.confidence) * 100)}%</small></li>
              ))}
            </ul>
          )}
        </section>
        <details className="analysis-json">
          <summary><FileJson2 size={15} /> View structured JSON</summary>
          <pre>{JSON.stringify(analysis, null, 2)}</pre>
        </details>
      </div>
    </section>
  )
}

export default DrawingAnalysisPanel
