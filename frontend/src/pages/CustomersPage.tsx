import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { ArrowUpRight, CircleAlert, Mail, MapPin, Plus, Search, UsersRound, Trash2, Pencil, X } from 'lucide-react'
import { Link } from 'react-router-dom'
import { getApiErrorMessage, ProjectService, type Customer, type CustomerCreate } from '../services/api'
import { showToast } from '../utils/toast'

function CustomersPage() {
  const [customers, setCustomers] = useState<Customer[]>([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [formOpen, setFormOpen] = useState(false)
  const [editingCustomer, setEditingCustomer] = useState<Customer | null>(null)
  const [form, setForm] = useState<CustomerCreate>({ name: '', contact_email: '', address: '' })

  async function loadCustomers() {
    setLoading(true)
    setError('')
    try {
      const response = await ProjectService.getCustomers()
      setCustomers(response.data)
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, 'Unable to load customer records. Please try again.'))
    } finally {
      setLoading(false)
    }
  }

  async function handleDeleteCustomer(id: string) {
    if (!confirm('Are you sure you want to delete this customer? This cannot be undone.')) return

    setDeletingId(id)
    try {
      await ProjectService.deleteCustomer(id)
      setCustomers((current) => current.filter((c) => c.id !== id))
      showToast('Customer deleted.')
    } catch (err) {
      showToast(getApiErrorMessage(err, 'Failed to delete customer. They may have active projects linked to them.'), 'error')
    } finally {
      setDeletingId(null)
    }
  }

  function openCreateForm() {
    setEditingCustomer(null)
    setForm({ name: '', contact_email: '', address: '' })
    setFormOpen(true)
    setError('')
  }

  function openEditForm(customer: Customer) {
    setEditingCustomer(customer)
    setForm({ name: customer.name, contact_email: customer.contact_email, address: customer.address ?? '' })
    setFormOpen(true)
    setError('')
  }

  async function handleSaveCustomer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSaving(true)
    setError('')
    const customerData: CustomerCreate = {
      name: form.name.trim(),
      contact_email: form.contact_email.trim(),
      address: form.address?.trim() || null,
    }
    try {
      if (editingCustomer) {
        const response = await ProjectService.updateCustomer(editingCustomer.id, customerData)
        setCustomers((current) => current.map((customer) => customer.id === response.data.id ? response.data : customer).sort((a, b) => a.name.localeCompare(b.name)))
        showToast('Customer updated.')
      } else {
        const response = await ProjectService.createCustomer(customerData)
        setCustomers((current) => [...current, response.data].sort((a, b) => a.name.localeCompare(b.name)))
        showToast('Customer created.')
      }
      setFormOpen(false)
      setEditingCustomer(null)
    } catch (requestError) {
      showToast(getApiErrorMessage(requestError, 'Unable to save the customer. Please try again.'), 'error')
    } finally {
      setSaving(false)
    }
  }

  useEffect(() => {
    void loadCustomers()
  }, [])

  const visibleCustomers = useMemo(() => {
    const query = search.trim().toLowerCase()
    if (!query) return customers
    return customers.filter((customer) => `${customer.name} ${customer.contact_email} ${customer.address ?? ''}`.toLowerCase().includes(query))
  }, [customers, search])

  return (
    <section className="page-wrap customers-page">
      <div className="page-heading">
        <div><div className="eyebrow">CUSTOMER RELATIONSHIPS</div><h1>Customer directory</h1><p>Customer records associated with manufacturing requests and projects.</p></div>
        <div className="page-actions"><button type="button" className="button button-secondary" onClick={openCreateForm}><Plus size={16} /> Add customer</button><Link to="/projects/new" className="button button-primary"><Plus size={16} /> New project</Link></div>
      </div>
      <div className="metric-grid customer-metrics">
        <article className="metric-card"><div className="metric-top"><span>Customer accounts</span><span className="metric-icon"><UsersRound size={17} /></span></div><div className="metric-value">{loading ? '—' : customers.length.toLocaleString()}</div><div className="metric-foot">Records in the ForgeMind workspace</div></article>
        <article className="metric-card customer-note"><div className="metric-top"><span>Customer records</span><span className="metric-icon metric-icon-green"><UsersRound size={17} /></span></div><div className="customer-note-copy">Create and maintain customer details here, or add a new customer as part of project intake.</div><Link to="/projects/new" className="text-link">Start project intake <ArrowUpRight size={14} /></Link></article>
      </div>

      {formOpen && <form className="panel customer-form-panel" onSubmit={handleSaveCustomer}>
        <div className="panel-heading"><div><div className="eyebrow">CUSTOMER DETAILS</div><h2>{editingCustomer ? 'Edit customer' : 'Add customer'}</h2></div><button type="button" className="button button-ghost button-compact" onClick={() => setFormOpen(false)} aria-label="Close customer form"><X size={16} /></button></div>
        <div className="form-grid">
          <label className="form-field"><span>Customer name <b>*</b></span><input required maxLength={255} value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} /></label>
          <label className="form-field"><span>Contact email <b>*</b></span><input required type="email" value={form.contact_email} onChange={(event) => setForm((current) => ({ ...current, contact_email: event.target.value }))} /></label>
          <label className="form-field"><span>Address</span><input maxLength={1000} value={form.address ?? ''} onChange={(event) => setForm((current) => ({ ...current, address: event.target.value }))} /></label>
        </div>
        <div className="customer-form-actions"><button type="submit" className="button button-primary" disabled={saving}>{saving ? 'Saving…' : editingCustomer ? 'Save changes' : 'Create customer'}</button><button type="button" className="button button-secondary" onClick={() => setFormOpen(false)} disabled={saving}>Cancel</button></div>
      </form>}
      <section className="panel customer-directory-panel">
        <div className="panel-heading"><div><div className="eyebrow">WORKSPACE RECORDS</div><h2>Customers</h2></div><button type="button" className="button button-secondary button-compact" onClick={() => void loadCustomers()} disabled={loading}>Refresh</button></div>
        <div className="filter-bar"><label className="search-field"><Search size={16} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search customer, email, or address" /></label></div>
        {error ? <div className="inline-error" role="alert"><CircleAlert size={18} /><span>{error}</span><button type="button" onClick={() => void loadCustomers()}>Retry</button></div>
          : loading ? <div className="loading-state"><span className="loading-spinner" /> Loading customers…</div>
            : visibleCustomers.length === 0 ? <div className="empty-panel customer-empty"><span className="empty-icon"><UsersRound size={21} /></span><h3>{customers.length ? 'No matching customers' : 'No customer records yet'}</h3><p>{customers.length ? 'Try another search term.' : 'Customer records are created when you start a project intake.'}</p>{customers.length === 0 && <Link to="/projects/new" className="button button-primary"><Plus size={15} /> Create first customer</Link>}</div>
              : <div className="table-scroll"><table className="data-table customer-table"><thead><tr><th>Customer</th><th>Email</th><th>Address</th><th>Added</th><th></th></tr></thead><tbody>
                {visibleCustomers.map((customer) => <tr key={customer.id} className={deletingId === customer.id ? 'opacity-50' : ''}><td><span className="customer-name-cell"><span className="customer-initial">{customer.name.trim().charAt(0).toUpperCase()}</span><strong>{customer.name}</strong></span></td><td><a className="customer-email" href={`mailto:${customer.contact_email}`}><Mail size={14} />{customer.contact_email}</a></td><td className="muted-cell">{customer.address ? <span className="customer-address"><MapPin size={13} />{customer.address}</span> : 'Not provided'}</td><td className="muted-cell">{new Date(customer.created_at).toLocaleDateString()}</td><td><div className="customer-row-actions"><button type="button" className="button button-ghost button-compact" onClick={() => openEditForm(customer)} disabled={deletingId !== null} aria-label={`Edit ${customer.name}`}><Pencil size={14} /></button><button type="button" className="button button-ghost button-compact text-danger" onClick={() => handleDeleteCustomer(customer.id)} disabled={deletingId !== null} aria-label={`Delete ${customer.name}`}><Trash2 size={14} /></button></div></td></tr>)}
              </tbody></table></div>}
        <div className="table-footer"><span>{loading ? '' : `Showing ${visibleCustomers.length} of ${customers.length} customers`}</span><span>DIRECTORY</span></div>
      </section>
    </section>
  )
}

export default CustomersPage
