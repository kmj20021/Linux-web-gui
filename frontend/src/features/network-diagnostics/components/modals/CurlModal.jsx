import { useState } from 'react'
import ToolModalShell from './ToolModalShell'
import { formatCurlCommand } from '../../commands'
import { simulateCurl } from '../../simulators'
import { validateUrl } from '../../validation'

const CURL_OPTIONS = [
  { value: '-I', label: '-I  헤더만' },
  { value: '-v', label: '-v  상세' },
  { value: '-L', label: '-L  리다이렉트 따라가기' },
]

function CurlModal({ onRun, onClose }) {
  const [url, setUrl] = useState('google.com')
  const [option, setOption] = useState('-I')
  const [error, setError] = useState('')

  const handleSubmit = () => {
    const checked = validateUrl(url)
    if (!checked.ok) return setError(checked.error)

    onRun('curl', formatCurlCommand(checked.value, option), simulateCurl(checked.value, option))
  }

  return (
    <ToolModalShell
      title="HTTP 테스트"
      badge="curl"
      command={formatCurlCommand(url.trim(), option)}
      error={error}
      onSubmit={handleSubmit}
      onClose={onClose}
    >
      <div className="nd-modal-field">
        <label className="nd-modal-label" htmlFor="nd-curl-url">URL</label>
        <input
          id="nd-curl-url"
          className="nd-modal-input"
          value={url}
          onChange={e => { setUrl(e.target.value); setError('') }}
          placeholder="예: google.com"
          autoFocus
        />
      </div>

      <div className="nd-modal-field">
        <label className="nd-modal-label" htmlFor="nd-curl-option">옵션</label>
        <select
          id="nd-curl-option"
          className="nd-modal-select"
          value={option}
          onChange={e => setOption(e.target.value)}
        >
          {CURL_OPTIONS.map(o => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>
    </ToolModalShell>
  )
}

export default CurlModal
