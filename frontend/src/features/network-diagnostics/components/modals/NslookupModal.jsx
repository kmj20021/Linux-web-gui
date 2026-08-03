import { useState } from 'react'
import ToolModalShell from './ToolModalShell'
import { formatNslookupCommand } from '../../commands'
import { simulateNslookup } from '../../simulators'
import { validateDomain } from '../../validation'

function NslookupModal({ onRun, onClose }) {
  const [domain, setDomain] = useState('google.com')
  const [error, setError] = useState('')

  const handleSubmit = () => {
    const checked = validateDomain(domain)
    if (!checked.ok) return setError(checked.error)

    onRun('nslookup', formatNslookupCommand(checked.value), simulateNslookup(checked.value))
  }

  return (
    <ToolModalShell
      title="DNS 조회"
      badge="nslookup"
      command={formatNslookupCommand(domain.trim())}
      error={error}
      onSubmit={handleSubmit}
      onClose={onClose}
    >
      <div className="nd-modal-field">
        <label className="nd-modal-label" htmlFor="nd-nslookup-domain">도메인</label>
        <input
          id="nd-nslookup-domain"
          className="nd-modal-input"
          value={domain}
          onChange={e => { setDomain(e.target.value); setError('') }}
          placeholder="예: google.com"
          autoFocus
        />
      </div>
    </ToolModalShell>
  )
}

export default NslookupModal
