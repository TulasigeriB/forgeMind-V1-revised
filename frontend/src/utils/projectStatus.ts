export type PipelineStatus = 'Uploaded' | 'Analyzing' | 'Costed' | 'Quoted'

export function normalizeProjectStatus(status: string): PipelineStatus {
  const normalized = status.toLowerCase()
  if (normalized === 'completed' || normalized === 'costed') return 'Costed'
  if (normalized === 'quoted') return 'Quoted'
  if (normalized === 'analyzing' || normalized === 'processing') return 'Analyzing'
  return 'Uploaded'
}
