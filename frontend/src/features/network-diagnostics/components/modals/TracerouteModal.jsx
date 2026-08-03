import { useState } from 'react'
import ToolModalShell from './ToolModalShell'
import { formatTracerouteCommand } from '../../commands'
import { simulateTraceroute } from '../../simulators'
import { validateHost } from '../../validation'

function TracerouteModal({ onRun, onClose }) {
  const [host, setHost] = useState('google.com')
  const [error, setError] = useState('')

  const handleSubmit = () => {
    const checked = validateHost(host)
    if (!checked.ok) return setError(checked.error)

    onRun('traceroute', formatTracerouteCommand(checked.value), simulateTraceroute(checked.value))
  }

  return (
    <ToolModalShell
      title="경로 추적"
      badge="traceroute"
      command={formatTracerouteCommand(host.trim())}
      error={error}
      onSubmit={handleSubmit}
      onClose={onClose}
    >
      <div className="nd-modal-field">
        <label className="nd-modal-label" htmlFor="nd-traceroute-host">호스트</label>
        <input
          id="nd-traceroute-host"
          className="nd-modal-input"
          value={host}
          onChange={e => { setHost(e.target.value); setError('') }}
          placeholder="예: google.com"
          autoFocus
        />
      </div>
    </ToolModalShell>
  )
}

export default TracerouteModal
