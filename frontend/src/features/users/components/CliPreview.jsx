import { useState } from 'react'

// 계정 작업에 해당하는 Linux CLI 명령 미리보기.
// 이 앱이 실행하는 명령이 아니라 사용자가 직접 서버에서 칠 수 있는 예시다.
function CliPreview({ title, lines, className = '' }) {
  const [copied, setCopied] = useState(false)

  const fullText = lines.map(l => (l.type === 'empty' ? '' : l.text)).join('\n')

  const handleCopy = () => {
    navigator.clipboard?.writeText(fullText).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    })
  }

  return (
    <div className={`ua-cli-preview${className ? ` ${className}` : ''}`}>
      <div className="ua-cli-preview-header">
        <span className="ua-cli-preview-title">{title}</span>
        <button
          type="button"
          className={`ua-cli-copy-btn${copied ? ' copied' : ''}`}
          onClick={handleCopy}
        >
          {copied ? '복사됨!' : '복사'}
        </button>
      </div>
      <div className="ua-cli-code">
        {lines.map((line, i) => (
          line.type === 'empty'
            ? <div key={`empty-${i}`} className="ua-cli-line">&nbsp;</div>
            : <div key={line.text} className={`ua-cli-line ua-cli-${line.type}`}>{line.text}</div>
        ))}
      </div>
    </div>
  )
}

export default CliPreview
