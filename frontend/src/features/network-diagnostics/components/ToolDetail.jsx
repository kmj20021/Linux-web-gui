function EmptyIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="11" cy="11" r="7"/>
      <path d="M21 21l-4-4"/>
      <path d="M8 11h6M11 8v6" opacity="0.5"/>
    </svg>
  )
}

// 우측 상세 패널: 도구 설명과 시뮬레이션 결과
function ToolDetail({ tool, result }) {
  if (!tool) {
    return (
      <div className="nd-detail-panel">
        <div className="nd-detail-empty">
          <div className="nd-detail-empty-icon"><EmptyIcon /></div>
          <span>도구를 선택하세요</span>
        </div>
      </div>
    )
  }

  return (
    <div className="nd-detail-panel">
      <div className="nd-detail-section">
        <div className="nd-detail-tool-name">{tool.label}</div>
        <div className="nd-detail-cmd-badge">{tool.cmd}</div>
        <div className="nd-detail-description">{tool.description}</div>
        <div className="nd-detail-section-title">사용법</div>
        <div className="nd-tool-usage">{tool.usage}</div>

        {result && (
          <>
            <div className="nd-detail-section-title" style={{ marginTop: '16px' }}>
              시뮬레이션 결과 (실제 응답 아님)
            </div>
            <div className="nd-result-output" data-testid="nd-result">
              {result.join('\n')}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default ToolDetail
