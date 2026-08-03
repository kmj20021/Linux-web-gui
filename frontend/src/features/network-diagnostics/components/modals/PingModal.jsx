import { useState } from 'react'
import ToolModalShell from './ToolModalShell'
import { formatPingCommand } from '../../commands'
import { simulatePing } from '../../simulators'
import { validateHost, validatePingCount } from '../../validation'

const PACKET_COUNTS = [1, 2, 4, 8, 16]

function PingModal({ onRun, onClose }) {
  const [host, setHost] = useState('google.com')
  const [count, setCount] = useState(4)
  const [error, setError] = useState('')

  const command = formatPingCommand(host.trim(), count)

  const handleSubmit = () => {
    const checkedHost = validateHost(host)
    if (!checkedHost.ok) return setError(checkedHost.error)

    const checkedCount = validatePingCount(count)
    if (!checkedCount.ok) return setError(checkedCount.error)

    onRun('ping', formatPingCommand(checkedHost.value, checkedCount.value),
      simulatePing(checkedHost.value, checkedCount.value))
  }

  return (
    <ToolModalShell
      title="Ping"
      badge="ping"
      command={command}
      error={error}
      onSubmit={handleSubmit}
      onClose={onClose}
    >
      <div className="nd-modal-field">
        <label className="nd-modal-label" htmlFor="nd-ping-host">호스트</label>
        <input
          id="nd-ping-host"
          className="nd-modal-input"
          value={host}
          onChange={e => { setHost(e.target.value); setError('') }}
          placeholder="예: google.com"
          autoFocus
        />
      </div>

      <div className="nd-modal-field">
        <label className="nd-modal-label" htmlFor="nd-ping-count">패킷 수</label>
        <select
          id="nd-ping-count"
          className="nd-modal-select"
          value={count}
          onChange={e => { setCount(e.target.value); setError('') }}
        >
          {PACKET_COUNTS.map(n => (
            <option key={n} value={n}>{n}</option>
          ))}
        </select>
      </div>
    </ToolModalShell>
  )
}

export default PingModal
