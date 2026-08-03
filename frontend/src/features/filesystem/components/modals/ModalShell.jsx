// 모달 공통 껍데기.
// 오버레이 클릭과 닫기 버튼으로 닫히고, 내부 클릭은 전파를 막는다.
function ModalShell({ title, badge, size = '', onClose, children, footer }) {
  return (
    <div className="fs-modal-overlay" onClick={onClose}>
      <div
        className={`fs-modal${size ? ` ${size}` : ''}`}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={e => e.stopPropagation()}
      >
        <div className="fs-modal-header">
          <span className="fs-modal-title">
            {title}
            <span className="fs-modal-cmd-badge">{badge}</span>
          </span>
          <button className="fs-modal-close" aria-label="닫기" onClick={onClose}>x</button>
        </div>
        <div className="fs-modal-body">{children}</div>
        <div className="fs-modal-footer">{footer}</div>
      </div>
    </div>
  )
}

export default ModalShell
