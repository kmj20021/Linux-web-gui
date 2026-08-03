// 토스트 알림 목록
function ToastStack({ toasts }) {
  return (
    <div className="fs-toast-container" role="status" aria-live="polite">
      {toasts.map(t => (
        <div key={t.id} className={`fs-toast${t.type === 'error' ? ' error' : ''}`}>
          <span className="fs-toast-icon" aria-hidden="true">{t.type === 'error' ? 'X' : 'V'}</span>
          <span className="fs-toast-msg">{t.message}</span>
        </div>
      ))}
    </div>
  )
}

export default ToastStack
