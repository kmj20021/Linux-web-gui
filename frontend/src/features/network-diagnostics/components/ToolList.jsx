import { TOOLS } from '../tools'

function ToolIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden="true">
      <circle cx="5.5" cy="5.5" r="3.5" stroke="currentColor" strokeWidth="1.3"/>
      <path d="M8.5 8.5L12 12" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
    </svg>
  )
}

// 좌측 진단 도구 목록
function ToolList({ selectedTool, onSelect }) {
  return (
    <div className="nd-list-panel">
      <div className="nd-list-panel-header">진단 도구</div>
      <div className="nd-list-body" data-testid="nd-tool-list">
        {TOOLS.map(tool => (
          <div
            key={tool.id}
            className={`nd-list-item${selectedTool === tool.id ? ' selected' : ''}`}
            onClick={() => onSelect(tool.id)}
          >
            <span className="nd-list-item-icon"><ToolIcon /></span>
            <span className="nd-list-item-name">{tool.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default ToolList
