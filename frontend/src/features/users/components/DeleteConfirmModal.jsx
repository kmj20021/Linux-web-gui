import CliPreview from './CliPreview'

function DeleteConfirmModal({ user, onConfirm, onCancel }) {
  const lines = [
    { type: 'comment', text: '# 홈 디렉터리까지 함께 삭제' },
    { type: 'cmd', text: `sudo userdel -r ${user.username}` },
  ]

  return (
    <div className="ua-modal-overlay" onClick={onCancel}>
      <div
        className="ua-modal"
        role="dialog"
        aria-modal="true"
        aria-label="계정 삭제 확인"
        onClick={e => e.stopPropagation()}
      >
        <div className="ua-modal-header">
          <span className="ua-modal-title">계정 삭제 확인</span>
        </div>
        <div className="ua-modal-body">
          <p className="ua-modal-desc">
            <strong>{user.username}</strong> 계정을 삭제하려면 아래 Linux CLI 명령어를 참고하세요.<br />
            이 작업은 되돌릴 수 없습니다.
          </p>
          <CliPreview title="Linux CLI 명령어" lines={lines} className="ua-modal-cli" />
        </div>
        <div className="ua-modal-footer">
          <button type="button" className="ua-cancel-btn" onClick={onCancel}>
            취소
          </button>
          <button type="button" className="ua-modal-confirm-btn" onClick={onConfirm}>
            삭제 확인
          </button>
        </div>
      </div>
    </div>
  )
}

export default DeleteConfirmModal
