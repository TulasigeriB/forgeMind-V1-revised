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

// The optional type assertion keeps this file compatible if Vite's ambient
// ImportMetaEnv declarations are not included by the project's TypeScript config.
const viteEnv = (import.meta as ImportMeta & { env?: Record<string, string | undefined> }).env
const API_BASE = (viteEnv?.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')
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
  if (options.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
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
      const body = await response.json() as { detail?: unknown }
      if (typeof body.detail === 'string') {
        message = body.detail
      } else if (Array.isArray(body.detail)) {
        message = body.detail.map((item: unknown) => {
          if (typeof item === 'object' && item !== null && 'msg' in item && typeof item.msg === 'string') {
            return item.msg
          }
          return 'Invalid input'
        }).join('; ')
      }
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
}
