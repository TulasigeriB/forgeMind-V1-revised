import axios from 'axios'

export type ProjectStatus = 'initialization' | 'uploaded' | 'analyzing' | 'completed' | 'costed' | 'quoted' | string
export type ProjectPriority = 'low' | 'normal' | 'high' | 'urgent'

export interface Project {
  id: string
  rfq_id: string
  part_number: string
  material_spec: string | null
  status: ProjectStatus
  created_at: string
  customer_name: string | null
}

export interface Customer {
  id: string
  name: string
  contact_email: string
  address: string | null
  created_at: string
}

export interface Rfq {
  id: string
}

export interface CustomerCreate {
  name: string
  contact_email: string
  address?: string | null
}

export type CustomerUpdate = Partial<CustomerCreate>

export interface RfqCreate {
  customer_id: string
  quantity: number
  priority: ProjectPriority
}

export interface ProjectCreate {
  rfq_id: string
  part_number: string
  material_spec?: string | null
}

export interface Feature {
  id: string
  project_id: string
  feature_type: string
  dimension: number | null
  tolerance: string | null
  quantity: number
  created_at: string
}

export interface DrawingDimension {
  callout: string
  type: string
  value: number | null
  units: string
  dimension_line_ref: string
  bounding_box: {
    page: number
    x0: number
    y0: number
    x1: number
    y1: number
    page_width?: number | null
    page_height?: number | null
  }
  vector_alignment_confidence: number
  nearest_vector_line: string | null
  confidence: number
  needs_engineer_confirmation: boolean
  semantic_source?: string
}

export interface DrawingAnalysisFeature {
  feature: string
  dimensions: DrawingDimension[]
  quantity?: number
  page?: number
  bounding_box?: number[]
  page_width?: number | null
  page_height?: number | null
  nearest_vector_line?: string | null
  confidence?: number
  needs_engineer_confirmation?: boolean
}

export interface DrawingPrecisionFit {
  feature: string
  callout: string
  nominal_size: string
  fit: string | null
  upper_deviation: string | null
  lower_deviation: string | null
  confidence: number
  needs_engineer_confirmation: boolean
}

export interface DrawingGeometricTolerance {
  feature: string
  symbol: string | null
  callout: string
  tolerance_value: number | null
  datum_references: string[]
  page: number
  bounding_box: number[]
  page_width: number | null
  page_height: number | null
  nearest_vector_line: string | null
  confidence: number
  needs_engineer_confirmation: boolean
}

export interface DrawingFormFeature {
  feature: string
  callout: string
  value?: number
  size?: number
  angle_degrees?: number
  units?: string
  page?: number
  bounding_box?: number[]
  page_width?: number | null
  page_height?: number | null
  nearest_vector_line?: string | null
  confidence: number
  needs_engineer_confirmation: boolean
  dimensions?: DrawingDimension[]
}

export interface DrawingMetadata {
  part_identifier: string
  supplier: string | null
  drawing_description: string | null
  material: string | null
  component_type: string | null
  component_classification: {
    shape: string
    material_family: string
    stock_form: string
    confidence: number
    needs_engineer_confirmation: boolean
    evidence: Record<string, string | null>
  }
  heat_treatments: Record<string, unknown>[]
  surface_treatments: Record<string, unknown>[]
  units: 'mm' | 'inches'
  source_files: string[]
  page_count: number
  notes: string[]
  surface_specifications: Record<string, unknown>[]
  general_tolerance_callouts: string[]
  confidence: number
  needs_engineer_confirmation: boolean
}

export interface DrawingAnalysis {
  part_identifier: string
  units: 'mm' | 'inches'
  manufacturing_operations: {
    turning: DrawingAnalysisFeature[]
    milling: DrawingAnalysisFeature[]
  }
  precision_fits: DrawingPrecisionFit[]
  geometric_tolerances: DrawingGeometricTolerance[]
  form_features: DrawingFormFeature[]
  critical_operations: Record<string, unknown>[]
  inspection_checklist: Record<string, unknown>[]
  quality_document_templates: Record<string, unknown>
  metadata_and_notes: DrawingMetadata[]
  review_flags: {
    issue: string
    confidence: number
    needs_engineer_confirmation?: boolean
    page?: number
    bounding_box?: number[]
  }[]
}

export interface EngineeringFile {
  id: string
  project_id: string
  file_type: string
  storage_path: string
  version: number
  status: string
  created_at: string
}

export type ReviewDecisionKind = 'accepted' | 'corrected' | 'rejected'

export interface AnalysisReviewDecision {
  target_id: string
  decision: ReviewDecisionKind
  corrected_callout?: string | null
  corrected_value?: number | null
  corrected_feature?: string | null
  corrected_units?: 'mm' | 'inches' | null
  comment?: string | null
}

export interface ProjectAnalysisReview {
  status: 'in_review' | 'approved' | 'changes_requested'
  reviewer: string
  updated_at: string
  decisions: AnalysisReviewDecision[]
}

export interface ProcessOperation {
  id: string
  project_id: string
  operation_name: string
  sequence_order: number
  estimated_time_minutes: number
  estimated_cost: number
  machine_type: string | null
  created_at: string
}

export interface QuoteBreakdownItem {
  operation: string
  quantity: number
  unit_cost: number
  extended_cost: number
  unit_time_minutes: number
  extended_time_minutes: number
  machine_type: string | null
}

export interface Quote {
  id: string
  project_id: string
  order_quantity: number
  status: string
  total_cost: number
  total_time_minutes: number
  assumptions: string[]
  breakdown: QuoteBreakdownItem[]
  created_at: string
}

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export function getApiErrorMessage(error: unknown, fallback = 'The request failed. Please try again.') {
  if (!axios.isAxiosError(error)) return fallback
  if (error.response?.status === 401) {
    return 'Your API access token is missing or invalid. Add a valid token in Settings.'
  }
  const detail = error.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (!error.response) return 'Could not reach the ForgeMind API. Check that the backend is running.'
  return `Request failed with HTTP ${error.response.status}.`
}

export const ProjectService = {
  getProjects: () => apiClient.get<Project[]>('/projects'),
  getProject: (id: string) => apiClient.get<Project>(`/projects/${id}`),
  getCustomers: () => apiClient.get<Customer[]>('/customers'),
  getCustomerByEmail: (email: string) => apiClient.get<Customer>('/customers/by-email', { params: { email } }),
  createCustomer: (customer: CustomerCreate) => apiClient.post<Customer>('/customers', customer),
  updateCustomer: (id: string, customer: CustomerUpdate) => apiClient.patch<Customer>(`/customers/${id}`, customer),
  deleteCustomer: (id: string) => apiClient.delete(`/customers/${id}`),
  createRfq: (rfq: RfqCreate) => apiClient.post<Rfq>('/rfqs', rfq),
  createProject: (project: ProjectCreate) => apiClient.post<Project>('/projects', project),
  deleteProject: (id: string) => apiClient.delete(`/projects/${id}`),
  uploadFile: (projectId: string, file: File, onProgress?: (progress: number) => void) => {
    const formData = new FormData()
    formData.append('file', file)
    return apiClient.post<EngineeringFile>('/upload', formData, {
      params: { project_id: projectId },
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (event) => {
        if (event.total) onProgress?.(Math.round((event.loaded / event.total) * 100))
      },
    })
  },
  analyzeFile: (projectId: string, file: File, onProgress?: (progress: number) => void) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('project_id', projectId)
    return apiClient.post<DrawingAnalysis>('/files/analyze', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (event) => {
        if (event.total) onProgress?.(Math.round((event.loaded / event.total) * 100))
      },
    })
  },
  getFiles: (id: string) => apiClient.get<EngineeringFile[]>(`/projects/${id}/files`),
  deleteFile: (id: string) => apiClient.delete(`/files/${id}`),
  getFileContent: (id: string) => apiClient.get<Blob>(`/files/${id}/content`, { responseType: 'blob' }),
  getFeatures: (id: string) => apiClient.get<Feature[]>(`/projects/${id}/features`),
  getQuote: (id: string) => apiClient.get<Quote>(`/projects/${id}/quote`),
  createQuote: (id: string) => apiClient.post<Quote>(`/projects/${id}/quote`),
  getOperations: (id: string) => apiClient.get<ProcessOperation[]>(`/projects/${id}/operations`),
  getAnalysis: (id: string) => apiClient.get<{
    project_id: string
    status: string
    analysis: DrawingAnalysis | null
    review: ProjectAnalysisReview | null
    process_plan_status: string
    route_review: { status: string; reviewer: string; updated_at: string; comment: string | null } | null
  }>(`/projects/${id}/analysis`),
  analyzeProject: (id: string) => apiClient.post(`/projects/${id}/analyze`),
  saveAnalysisReview: (id: string, status: ProjectAnalysisReview['status'], decisions: AnalysisReviewDecision[]) =>
    apiClient.put(`/projects/${id}/analysis/review`, { status, decisions }),
  generateRoutes: (id: string) => apiClient.post<ProcessOperation[]>(`/projects/${id}/routes`),
  saveRouteReview: (id: string, status: 'approved' | 'changes_requested', comment: string, operations: ProcessOperation[]) =>
    apiClient.put(`/projects/${id}/routes/review`, {
      status,
      comment,
      operations: operations.map(({ id: operation_id, operation_name, sequence_order, estimated_time_minutes, estimated_cost, machine_type }) => ({
        operation_id,
        operation_name,
        sequence_order,
        estimated_time_minutes,
        estimated_cost,
        machine_type,
      })),
    }),
}

export default apiClient
