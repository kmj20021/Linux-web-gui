// 진단 도구 모달 공통 껍데기.
// 명령 미리보기와 검증 오류 표시 위치를 한 곳에서 관리한다.
function ToolModalShell({ title, badge, command, error, onSubmit, onClose, children }) {
  return (
    <div className="nd-modal-overlay" onClick={onClose}>
      <div
        className="nd-modal"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={e => e.stopPropagation()}
      >
        <div className="nd-modal-header">
          <div className="nd-modal-title">
            {title}
            <span className="nd-modal-cmd-badge">{badge}</span>
          </div>
          <button className="nd-modal-close" aria-label="닫기" onClick={onClose}>x</button>
        </div>
        <div className="nd-modal-body">
          <div className="nd-cmd-preview">시뮬레이션할 명령어: {command}</div>
          {children}
          {error && <div className="nd-modal-error" role="alert">{error}</div>}
        </div>
        <div className="nd-modal-footer">
          <button className="nd-action-btn cancel" onClick={onClose}>취소</button>
          <button className="nd-action-btn confirm" onClick={onSubmit}>시뮬레이션</button>
        </div>
      </div>
    </div>
  )
}

export default ToolModalShell
