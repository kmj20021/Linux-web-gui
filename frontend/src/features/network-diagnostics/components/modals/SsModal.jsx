import { useState } from 'react'
import ToolModalShell from './ToolModalShell'
import { formatSsCommand } from '../../commands'
import { simulateSs } from '../../simulators'

const OPTIONS = [
  { key: 't', desc: '-t  TCP' },
  { key: 'u', desc: '-u  UDP' },
  { key: 'l', desc: '-l  리슨만' },
  { key: 'n', desc: '-n  숫자 형식' },
]

function SsModal({ onRun, onClose }) {
  const [options, setOptions] = useState({ t: true, u: true, l: true, n: true })

  const toggle = (key) => setOptions(prev => ({ ...prev, [key]: !prev[key] }))

  return (
    <ToolModalShell
      title="포트/소켓"
      badge="ss"
      command={formatSsCommand(options)}
      onSubmit={() => onRun('ss', formatSsCommand(options), simulateSs(options))}
      onClose={onClose}
    >
      <div className="nd-modal-field">
        <span className="nd-modal-label">옵션</span>
        <div className="nd-checkbox-group">
          {OPTIONS.map(({ key, desc }) => (
            <label key={key} className="nd-checkbox-item">
              <input type="checkbox" checked={options[key]} onChange={() => toggle(key)} />
              <span>{desc}</span>
            </label>
          ))}
        </div>
      </div>
    </ToolModalShell>
  )
}

export default SsModal
