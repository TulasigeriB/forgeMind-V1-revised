export type AuthUser = {
  id: string
  organization_id: string
  email: string
  role: string
}

export type AuthResponse = {
  access_token: string
  token_type: 'bearer'
  expires_in: number
  user: AuthUser
}

export type Customer = {
  id: string
  name: string
  contact_name: string | null
  email: string | null
  phone: string | null
  address: string | null
  notes: string | null
  created_at: string
  updated_at: string
}

export type CustomerInput = Omit<Customer, 'id' | 'created_at' | 'updated_at'>

export type RFQStatus = 'Draft' | 'Received' | 'Quoting' | 'Submitted' | 'Won' | 'Lost' | 'Cancelled'
export type RFQ = {
  id: string; organization_id: string; customer_id: string; customer_name: string
  reference: string; title: string; description: string | null; quantity: number
  due_date: string | null; status: RFQStatus; notes: string | null
  created_at: string; updated_at: string
}
export type RFQInput = Omit<RFQ, 'id' | 'organization_id' | 'customer_name' | 'created_at' | 'updated_at'>

export type QuoteStatus = 'Draft' | 'Under Review' | 'Submitted' | 'Accepted' | 'Rejected' | 'Expired'
export type QuoteLineItem = { description: string; quantity: number; unit: string; material_unit_cost: number; labor_unit_cost: number; overhead_unit_cost: number; unit_selling_price: number }
export type Quotation = { id: string; organization_id: string; rfq_id: string; rfq_reference: string; customer_name: string; reference: string; revision: number; currency: 'INR' | 'USD' | 'EUR' | 'GBP'; status: QuoteStatus; valid_until: string | null; line_items: QuoteLineItem[]; material_cost: number; labor_cost: number; overhead_cost: number; total_cost: number; selling_price: number; gross_margin_percent: number; notes: string | null; created_at: string; updated_at: string }
export type QuotationInput = Omit<Quotation, 'id' | 'organization_id' | 'rfq_reference' | 'customer_name' | 'material_cost' | 'labor_cost' | 'overhead_cost' | 'total_cost' | 'selling_price' | 'gross_margin_percent' | 'created_at' | 'updated_at'>


export type ExtractedField = { key: string; label: string; value: string; source: string; confidence: number; review_status: 'needs_review' | 'approved' | 'rejected' }
export type ExtractionDocument = { id: string; organization_id: string; rfq_id: string | null; rfq_reference: string | null; filename: string; file_type: string; content_sha256: string; file_size_bytes: number; extracted_text: string; source_map: { source: string; text: string }[]; fields: ExtractedField[]; status: 'needs_review' | 'reviewed'; extraction_warnings: string[]; created_at: string; updated_at: string }

const API_BASE = ((import.meta as ImportMeta & { env?: { VITE_API_BASE_URL?: string } }).env?.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')
const TOKEN_KEY = 'forgemind_access_token'

export function getToken(): string | null {
  return window.sessionStorage.getItem(TOKEN_KEY)
}

export function saveToken(token: string): void {
  window.sessionStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  window.sessionStorage.removeItem(TOKEN_KEY)
}

async function request<T>(path: string, options: RequestInit = {}, authenticated = true): Promise<T> {
  const headers = new Headers(options.headers)
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  if (authenticated) {
    const token = getToken()
    if (token) headers.set('Authorization', `Bearer ${token}`)
  }
  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, { ...options, headers })
  } catch {
    throw new Error('Cannot reach the ForgeMind API. Check that the backend is running at ' + API_BASE + '.')
  }
  if (!response.ok) {
    let message = `Request failed (${response.status})`
    try {
      const body = await response.json() as { detail?: string | { msg?: string }[] }
      if (typeof body.detail === 'string') message = body.detail
      else if (Array.isArray(body.detail)) message = body.detail.map((item: { msg?: string }) => item.msg || 'Invalid input').join('; ')
    } catch {
      // Use the HTTP status message if the response is not JSON.
    }
    if (response.status === 401 && authenticated) {
      clearToken()
      window.dispatchEvent(new Event('forgemind:unauthorized'))
    }
    throw new Error(message)
  }
  if (response.status === 204) return undefined as T
  return await response.json() as T
}

export const api = {
  register: (input: { organization_name: string; email: string; password: string; default_currency: string }) =>
    request<AuthResponse>('/auth/register', { method: 'POST', body: JSON.stringify(input) }, false),
  login: (input: { email: string; password: string }) =>
    request<AuthResponse>('/auth/login', { method: 'POST', body: JSON.stringify(input) }, false),
  me: () => request<AuthUser>('/auth/me'),
  customers: () => request<Customer[]>('/customers'),
  createCustomer: (input: CustomerInput) => request<Customer>('/customers', { method: 'POST', body: JSON.stringify(input) }),
  updateCustomer: (id: string, input: CustomerInput) => request<Customer>(`/customers/${encodeURIComponent(id)}`, { method: 'PATCH', body: JSON.stringify(input) }),
  deleteCustomer: (id: string) => request<void>(`/customers/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  rfqs: () => request<RFQ[]>('/rfqs'),
  createRFQ: (input: RFQInput) => request<RFQ>('/rfqs', { method: 'POST', body: JSON.stringify(input) }),
  updateRFQ: (id: string, input: RFQInput) => request<RFQ>(`/rfqs/${encodeURIComponent(id)}`, { method: 'PATCH', body: JSON.stringify(input) }),
  deleteRFQ: (id: string) => request<void>(`/rfqs/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  quotations: () => request<Quotation[]>('/quotations'),
  createQuotation: (input: QuotationInput) => request<Quotation>('/quotations', { method: 'POST', body: JSON.stringify(input) }),
  updateQuotation: (id: string, input: QuotationInput) => request<Quotation>(`/quotations/${encodeURIComponent(id)}`, { method: 'PATCH', body: JSON.stringify(input) }),
  deleteQuotation: (id: string) => request<void>(`/quotations/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  extractions: () => request<ExtractionDocument[]>('/extractions'),
  uploadExtraction: (file: File, rfqId: string) => { const body = new FormData(); body.append('file', file); body.append('rfq_id', rfqId); return request<ExtractionDocument>('/extractions', { method: 'POST', body }) },
  reviewExtraction: (id: string, fields: (Pick<ExtractedField, 'key' | 'value' | 'review_status'> & { label?: string; source?: string; confidence?: number })[]) => request<ExtractionDocument>(`/extractions/${encodeURIComponent(id)}/review`, { method: 'PATCH', body: JSON.stringify({ fields }) }),
  deleteExtraction: (id: string) => request<void>(`/extractions/${encodeURIComponent(id)}`, { method: 'DELETE' }),
}
