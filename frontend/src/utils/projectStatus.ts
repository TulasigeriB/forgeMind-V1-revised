export type PipelineStatus = 'Draft' | 'Uploaded' | 'Analyzing' | 'In review' | 'Approved' | 'Route review' | 'Costed' | 'Quoted' | 'Failed'

export function normalizeProjectStatus(status: string): PipelineStatus {
  const normalized = status.toLowerCase()
  if (normalized === 'initialization' || normalized === 'draft') return 'Draft'
  if (normalized === 'analysis_failed') return 'Failed'
  if (normalized === 'analysis_ready') return 'In review'
  if (normalized === 'analysis_approved') return 'Approved'
  if (normalized === 'routing') return 'Route review'
  if (normalized === 'completed' || normalized === 'costed') return 'Costed'
  if (normalized === 'quoted') return 'Quoted'
  if (normalized === 'analyzing' || normalized === 'processing') return 'Analyzing'
  return 'Uploaded'
}
