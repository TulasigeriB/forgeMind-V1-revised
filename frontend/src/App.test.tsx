import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'

afterEach(() => {
  cleanup()
  window.sessionStorage.clear()
  vi.restoreAllMocks()
})

describe('ForgeMind authentication and customer workflow', () => {
  it('shows login by default and offers organization registration', () => {
    render(<App />)
    expect(screen.getByRole('heading', { name: 'Welcome back.' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Create an account' }))
    expect(screen.getByRole('heading', { name: 'Create your workspace.' })).toBeInTheDocument()
    expect(screen.getByLabelText('Organization name')).toBeRequired()
  })

  it('logs in and loads organization customer records', async () => {
    const user = { id: 'user-1', organization_id: 'org-1', email: 'owner@example.com', role: 'owner' }
    const customer = {
      id: 'customer-1', name: 'Precision Works', contact_name: 'Sam', email: 'sam@example.com',
      phone: null, address: null, notes: null, created_at: '2026-10-16T00:00:00Z', updated_at: '2026-10-16T00:00:00Z',
    }
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input)
      if (url.endsWith('/auth/login')) {
        return new Response(JSON.stringify({ access_token: 'test-token', token_type: 'bearer', expires_in: 3600, user }), { status: 200 })
      }
      if (url.endsWith('/customers')) {
        expect(new Headers(init?.headers).get('Authorization')).toBe('Bearer test-token')
        return new Response(JSON.stringify([customer]), { status: 200 })
      }
      if (url.endsWith('/auth/me')) return new Response(JSON.stringify(user), { status: 200 })
      return new Response('{}', { status: 404 })
    })

    render(<App />)
    fireEvent.change(screen.getByLabelText('Email address'), { target: { value: 'owner@example.com' } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'correct-password' } })
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }))

    await screen.findByText('owner@example.com')
    fireEvent.click(within(screen.getByLabelText('Main navigation')).getByRole('button', { name: 'Customers' }))
    expect(await screen.findByText('Precision Works')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalled()
  })

  it('creates a customer through the authenticated API', async () => {
    const user = { id: 'user-1', organization_id: 'org-1', email: 'owner@example.com', role: 'owner' }
    const created = {
      id: 'customer-2', name: 'New Components', contact_name: null, email: null, phone: null,
      address: null, notes: null, created_at: '2026-10-16T00:00:00Z', updated_at: '2026-10-16T00:00:00Z',
    }
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input)
      if (url.endsWith('/auth/login')) return new Response(JSON.stringify({ access_token: 'test-token', token_type: 'bearer', expires_in: 3600, user }), { status: 200 })
      if (url.endsWith('/customers') && init?.method === 'POST') return new Response(JSON.stringify(created), { status: 201 })
      if (url.endsWith('/customers')) return new Response(JSON.stringify([]), { status: 200 })
      return new Response('{}', { status: 404 })
    })

    render(<App />)
    fireEvent.change(screen.getByLabelText('Email address'), { target: { value: 'owner@example.com' } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'correct-password' } })
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }))
    await screen.findByText('owner@example.com')
    fireEvent.click(within(screen.getByLabelText('Main navigation')).getByRole('button', { name: 'Customers' }))
    fireEvent.click(await screen.findByRole('button', { name: '+ New customer' }))
    fireEvent.change(screen.getByLabelText('Company / customer name *'), { target: { value: 'New Components' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create customer' }))
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Customer created.'))
    expect(screen.getByRole('heading', { name: 'No customers yet' })).toBeInTheDocument()
  })
})
