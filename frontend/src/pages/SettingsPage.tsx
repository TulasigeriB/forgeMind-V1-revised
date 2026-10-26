import { useState } from 'react'
import { KeyRound, Save } from 'lucide-react'

function SettingsPage() {
  const [token, setToken] = useState(() => localStorage.getItem('token') ?? '')
  const [saved, setSaved] = useState(false)

  function saveToken() {
    if (token.trim()) localStorage.setItem('token', token.trim())
    else localStorage.removeItem('token')
    setToken(token.trim())
    setSaved(true)
  }

  return (
    <section className="page-wrap">
      <div className="page-heading">
        <div><div className="eyebrow">WORKSPACE CONFIGURATION</div><h1>Settings</h1><p>Manage API access for protected workspace actions.</p></div>
      </div>
      <section className="panel settings-panel">
        <div className="form-section-heading"><span className="settings-icon"><KeyRound size={18} /></span><div><h2>API access token</h2><p>Used to authorize engineering file uploads.</p></div></div>
        <label className="form-field settings-token">
          <span>Bearer token</span>
          <input type="password" autoComplete="off" value={token} onChange={(event) => { setToken(event.target.value); setSaved(false) }} placeholder="Paste an access token" />
        </label>
        <p className="settings-hint">The token is stored in this browser only and sent to the ForgeMind API when required.</p>
        <button type="button" className="button button-primary" onClick={saveToken}><Save size={16} /> {saved ? 'Saved' : 'Save token'}</button>
      </section>
    </section>
  )
}

export default SettingsPage
