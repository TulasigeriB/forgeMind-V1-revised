import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { api, clearToken, getToken, saveToken } from './api'
import type { AuthUser, Customer, CustomerInput } from './api'

type Section = 'Overview' | 'Customers' | 'RFQs' | 'Projects' | 'Engineering' | 'Process planning' | 'Cost estimates' | 'Quotations' | 'Production feedback' | 'Settings'
type AuthMode = 'login' | 'register'

const sections: { label: Section; group: string }[] = [
  { label: 'Overview', group: 'WORKSPACE' },
  { label: 'Customers', group: 'WORKSPACE' },
  { label: 'RFQs', group: 'WORKSPACE' },
  { label: 'Projects', group: 'WORKSPACE' },
  { label: 'Engineering', group: 'ENGINEERING' },
  { label: 'Process planning', group: 'ENGINEERING' },
  { label: 'Cost estimates', group: 'COMMERCIAL' },
  { label: 'Quotations', group: 'COMMERCIAL' },
  { label: 'Production feedback', group: 'OPERATIONS' },
  { label: 'Settings', group: 'SYSTEM' },
]

const descriptions: Record<Section, string> = {
  Overview: 'A clear view of work in progress, backed by real project records.',
  Customers: 'Manage customer records and commercial contacts.',
  RFQs: 'Capture enquiries, requirements, quantities, and delivery expectations.',
  Projects: 'Organize parts, engineering files, reviews, estimates, and quotations.',
  Engineering: 'Upload and review source-linked CAD models and drawing analysis.',
  'Process planning': 'Build reviewable operation sequences from configurable manufacturing rules.',
  'Cost estimates': 'Create reproducible estimates from explicit rates, inputs, and assumptions.',
  Quotations: 'Prepare and revise customer quotations linked to reviewed estimates.',
  'Production feedback': 'Capture actual cycle time, material use, scrap, and cost outcomes.',
  Settings: 'Configure company details, currencies, roles, and manufacturing parameters.',
}

const emptyCustomer: CustomerInput = {
  name: '', contact_name: '', email: '', phone: '', address: '', notes: '',
}

function App() {
  const [active, setActive] = useState<Section>('Overview')
  const [user, setUser] = useState<AuthUser | null>(null)
  const [authMode, setAuthMode] = useState<AuthMode>('login')
  const [authBusy, setAuthBusy] = useState(false)
  const [authError, setAuthError] = useState('')
  const [customerRows, setCustomerRows] = useState<Customer[]>([])
  const [customersBusy, setCustomersBusy] = useState(false)
  const [customerError, setCustomerError] = useState('')
  const [editing, setEditing] = useState<Customer | null>(null)
  const [customerForm, setCustomerForm] = useState<CustomerInput>(emptyCustomer)
  const [formOpen, setFormOpen] = useState(false)
  const [savingCustomer, setSavingCustomer] = useState(false)
  const [customerNotice, setCustomerNotice] = useState('')
  const groups = [...new Set(sections.map((section) => section.group))]

  useEffect(() => {
    const onUnauthorized = () => {
      setUser(null)
      setAuthError('Your session expired. Please sign in again.')
    }
    window.addEventListener('forgemind:unauthorized', onUnauthorized)
    const token = getToken()
    if (token) {
      api.me().then(setUser).catch(() => {
        clearToken()
        setUser(null)
      })
    }
    return () => window.removeEventListener('forgemind:unauthorized', onUnauthorized)
  }, [])

  useEffect(() => {
    if (user && active === 'Customers') void loadCustomers()
  }, [user, active])

  async function loadCustomers() {
    setCustomersBusy(true)
    setCustomerError('')
    try {
      setCustomerRows(await api.customers())
    } catch (error) {
      setCustomerError(error instanceof Error ? error.message : 'Could not load customers.')
    } finally {
      setCustomersBusy(false)
    }
  }

  async function submitAuth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    setAuthBusy(true)
    setAuthError('')
    try {
      const result = authMode === 'register'
        ? await api.register({
            organization_name: String(data.get('organization_name') || '').trim(),
            email: String(data.get('email') || '').trim(),
            password: String(data.get('password') || ''),
            default_currency: String(data.get('default_currency') || 'INR'),
          })
        : await api.login({
            email: String(data.get('email') || '').trim(),
            password: String(data.get('password') || ''),
          })
      saveToken(result.access_token)
      setUser(result.user)
      setActive('Overview')
      setAuthError('')
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : 'Authentication failed.')
    } finally {
      setAuthBusy(false)
    }
  }

  function logout() {
    clearToken()
    setUser(null)
    setCustomerRows([])
    setActive('Overview')
    setAuthError('')
  }

  function openCreateCustomer() {
    setEditing(null)
    setCustomerForm(emptyCustomer)
    setCustomerNotice('')
    setFormOpen(true)
  }

  function openEditCustomer(customer: Customer) {
    setEditing(customer)
    setCustomerForm({
      name: customer.name,
      contact_name: customer.contact_name || '',
      email: customer.email || '',
      phone: customer.phone || '',
      address: customer.address || '',
      notes: customer.notes || '',
    })
    setCustomerNotice('')
    setFormOpen(true)
  }

  async function saveCustomer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSavingCustomer(true)
    setCustomerError('')
    setCustomerNotice('')
    const payload: CustomerInput = {
      name: customerForm.name.trim(),
      contact_name: customerForm.contact_name?.trim() || null,
      email: customerForm.email?.trim() || null,
      phone: customerForm.phone?.trim() || null,
      address: customerForm.address?.trim() || null,
      notes: customerForm.notes?.trim() || null,
    }
    try {
      if (editing) await api.updateCustomer(editing.id, payload)
      else await api.createCustomer(payload)
      setFormOpen(false)
      setCustomerNotice(editing ? 'Customer updated.' : 'Customer created.')
      await loadCustomers()
    } catch (error) {
      setCustomerError(error instanceof Error ? error.message : 'Could not save customer.')
    } finally {
      setSavingCustomer(false)
    }
  }

  async function deleteCustomer(customer: Customer) {
    if (!window.confirm(`Delete ${customer.name}? This cannot be undone.`)) return
    setCustomerError('')
    setCustomerNotice('')
    try {
      await api.deleteCustomer(customer.id)
      setCustomerNotice('Customer deleted.')
      await loadCustomers()
    } catch (error) {
      setCustomerError(error instanceof Error ? error.message : 'Could not delete customer.')
    }
  }

  if (!user) {
    return (
      <main className="auth-page">
        <section className="auth-card">
          <div className="auth-brand"><div className="brand-mark">F</div><div><strong>ForgeMind</strong><span>MANUFACTURING INTELLIGENCE</span></div></div>
          <p className="eyebrow">LOCAL WORKSPACE</p>
          <h1>{authMode === 'login' ? 'Welcome back.' : 'Create your workspace.'}</h1>
          <p className="auth-subtitle">{authMode === 'login' ? 'Sign in to access your organization’s manufacturing workspace.' : 'Register your organization and create its first owner account.'}</p>
          {authError && <div className="error-banner" role="alert">{authError}</div>}
          <form className="auth-form" onSubmit={submitAuth}>
            {authMode === 'register' && <>
              <label>Organization name<input name="organization_name" autoComplete="organization" minLength={2} maxLength={200} required /></label>
              <label>Default costing currency<select name="default_currency" defaultValue="INR"><option value="INR">INR — Indian rupee</option><option value="USD">USD — US dollar</option><option value="EUR">EUR — euro</option><option value="GBP">GBP — pound sterling</option></select></label>
            </>}
            <label>Email address<input name="email" type="email" autoComplete="email" maxLength={320} required /></label>
            <label>Password<input name="password" type="password" autoComplete={authMode === 'login' ? 'current-password' : 'new-password'} minLength={authMode === 'register' ? 12 : 1} maxLength={128} required /></label>
            {authMode === 'register' && <p className="field-help">Use at least 12 characters. Registration is currently intended for local development only.</p>}
            <button className="primary-button auth-submit" type="submit" disabled={authBusy}>{authBusy ? 'Please wait…' : authMode === 'login' ? 'Sign in' : 'Create organization'}</button>
          </form>
          <p className="auth-switch">{authMode === 'login' ? 'New to ForgeMind?' : 'Already registered?'} <button type="button" onClick={() => { setAuthMode(authMode === 'login' ? 'register' : 'login'); setAuthError('') }}>{authMode === 'login' ? 'Create an account' : 'Sign in'}</button></p>
          <p className="auth-footnote">Local development build · Keep this service off public networks.</p>
        </section>
      </main>
    )
  }

  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Main navigation">
        <div className="brand"><div className="brand-mark">F</div><div><strong>ForgeMind</strong><span>MANUFACTURING INTELLIGENCE</span></div></div>
        <div className="workspace-switch"><span className="workspace-dot" /> {user.email} <span className="chevron">⌄</span></div>
        <nav>
          {groups.map((group) => (
            <div className="nav-group" key={group}>
              <p className="nav-label">{group}</p>
              {sections.filter((section) => section.group === group).map((section) => (
                <button key={section.label} className={`nav-item ${active === section.label ? 'active' : ''}`} onClick={() => setActive(section.label)} aria-current={active === section.label ? 'page' : undefined}>
                  <span className={`nav-icon icon-${section.label.toLowerCase().replaceAll(' ', '-')}`} aria-hidden="true">{navSymbol(section.label)}</span>
                  {section.label}
                </button>
              ))}
            </div>
          ))}
        </nav>
        <div className="sidebar-footer"><span className="status-dot" /> Local development <button className="logout-button" onClick={logout}>Sign out</button><span className="version">v0.2.0</span></div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="breadcrumb"><span>ForgeMind</span><span className="crumb-separator">/</span><strong>{active}</strong></div>
          <div className="topbar-actions"><span className="environment-badge">DEVELOPMENT</span><button className="avatar" aria-label="User profile" title={user.email}>{user.email.slice(0, 2).toUpperCase()}</button></div>
        </header>
        <div className="page-content">
          <div className="page-heading"><div><p className="eyebrow">MANUFACTURING WORKSPACE</p><h1>{active === 'Overview' ? 'Good work starts with clarity.' : active}</h1><p className="page-description">{descriptions[active]}</p></div><div className="date-chip"><span className="date-chip-dot" /> Connected workspace</div></div>
          {active === 'Customers' ? (
            <section className="customer-panel">
              <div className="customer-toolbar"><div><h2>Customers</h2><p>Customer records are stored in your organization’s database.</p></div><button className="primary-button" onClick={openCreateCustomer}>+ New customer</button></div>
              {customerError && <div className="error-banner" role="alert">{customerError}</div>}
              {customerNotice && <div className="success-banner" role="status">{customerNotice}</div>}
              {formOpen && <form className="customer-form" onSubmit={saveCustomer}>
                <div className="customer-form-heading"><h3>{editing ? 'Edit customer' : 'New customer'}</h3><button type="button" className="text-button" onClick={() => setFormOpen(false)}>Cancel</button></div>
                <div className="form-grid">
                  <label>Company / customer name *<input required minLength={2} maxLength={200} value={customerForm.name} onChange={e => setCustomerForm({ ...customerForm, name: e.target.value })} /></label>
                  <label>Contact person<input maxLength={200} value={customerForm.contact_name || ''} onChange={e => setCustomerForm({ ...customerForm, contact_name: e.target.value })} /></label>
                  <label>Email<input type="email" maxLength={320} value={customerForm.email || ''} onChange={e => setCustomerForm({ ...customerForm, email: e.target.value })} /></label>
                  <label>Phone<input maxLength={50} value={customerForm.phone || ''} onChange={e => setCustomerForm({ ...customerForm, phone: e.target.value })} /></label>
                  <label className="wide-field">Address<textarea rows={2} maxLength={5000} value={customerForm.address || ''} onChange={e => setCustomerForm({ ...customerForm, address: e.target.value })} /></label>
                  <label className="wide-field">Notes<textarea rows={2} maxLength={5000} value={customerForm.notes || ''} onChange={e => setCustomerForm({ ...customerForm, notes: e.target.value })} /></label>
                </div>
                <div className="form-actions"><button className="primary-button" type="submit" disabled={savingCustomer}>{savingCustomer ? 'Saving…' : editing ? 'Save changes' : 'Create customer'}</button></div>
              </form>}
              {customersBusy ? <div className="empty-state"><p>Loading customer records…</p></div> : customerRows.length === 0 ? <div className="empty-state"><div className="empty-state-icon">◎</div><h2>No customers yet</h2><p>Create your first customer to start organizing RFQs and projects.</p><button className="secondary-button" onClick={openCreateCustomer}>Add first customer</button></div> : <div className="table-wrap"><table className="data-table"><thead><tr><th>Customer</th><th>Contact</th><th>Email</th><th>Phone</th><th>Actions</th></tr></thead><tbody>{customerRows.map(customer => <tr key={customer.id}><td><strong>{customer.name}</strong><small>{customer.address || 'No address added'}</small></td><td>{customer.contact_name || '—'}</td><td>{customer.email || '—'}</td><td>{customer.phone || '—'}</td><td><div className="row-actions"><button className="text-button" onClick={() => openEditCustomer(customer)}>Edit</button><button className="text-button danger-text" onClick={() => void deleteCustomer(customer)}>Delete</button></div></td></tr>)}</tbody></table></div>}
            </section>
          ) : active === 'Overview' ? <>
            <section className="welcome-panel"><div className="welcome-copy"><span className="panel-kicker">WORKSPACE CONNECTED</span><h2>Your manufacturing workflow starts here.</h2><p>ForgeMind is built around traceable engineering, reviewed manufacturing decisions, and explainable cost estimates. Customer records now connect to your authenticated API.</p><button className="primary-button" onClick={() => setActive('Customers')}>Open customers <span aria-hidden="true">→</span></button></div><div className="blueprint-art" aria-hidden="true"><div className="blueprint-ring ring-one"/><div className="blueprint-ring ring-two"/><div className="blueprint-ring ring-three"/><div className="blueprint-cross cross-one"/><div className="blueprint-cross cross-two"/><div className="blueprint-center"><span>FM</span></div><div className="blueprint-dimension dim-top">X — Y — Z</div><div className="blueprint-dimension dim-side">REV 00</div></div></section>
            <section className="section-heading"><div><h2>Workflow modules</h2><p>Customer management is connected. Other modules will be integrated in their planned milestones.</p></div><span className="module-count">CORE MODULES</span></section>
            <div className="module-grid">{sections.filter(section => section.label !== 'Overview').slice(0, 6).map((section, index) => <button className="module-card" key={section.label} onClick={() => setActive(section.label)}><div className={`module-icon tone-${index + 1}`}>{navSymbol(section.label)}</div><div className="module-card-copy"><h3>{section.label}</h3><p>{descriptions[section.label]}</p></div><span className="module-arrow" aria-hidden="true">↗</span></button>)}</div>
          </> : <section className="empty-state"><div className="empty-state-icon">{navSymbol(active)}</div><span className="panel-kicker">MODULE FOUNDATION</span><h2>{active} is not implemented yet</h2><p>{descriptions[active]} This module will be connected to real records and APIs in its planned milestone.</p><button className="secondary-button" onClick={() => setActive('Overview')}>Return to overview</button></section>}
          <footer className="page-footer"><span>ForgeMind · Built for traceability</span><span>Development build · No fabricated production data</span></footer>
        </div>
      </main>
    </div>
  )
}

function navSymbol(section: Section): string {
  const symbols: Record<Section, string> = { Overview: '⌂', Customers: '◎', RFQs: '↗', Projects: '▦', Engineering: '⌁', 'Process planning': '⋈', 'Cost estimates': '∑', Quotations: '▤', 'Production feedback': '↻', Settings: '⚙' }
  return symbols[section]
}

export default App
