import ModalShell from './ModalShell'

function DeleteModal({ path, isDir, onConfirm, onClose }) {
  return (
    <ModalShell
      title={isDir ? '폴더 삭제' : '파일 삭제'}
      badge={isDir ? 'rm -rf' : 'rm'}
      onClose={onClose}
      footer={
        <>
          <button className="fs-action-btn cancel" onClick={onClose}>취소</button>
          <button className="fs-action-btn confirm danger" onClick={onConfirm}>삭제</button>
        </>
      }
    >
      <p className="fs-modal-warning">
        <strong>{path}</strong> {isDir ? '폴더와 모든 하위 항목을' : '파일을'} 삭제합니다.
        이 작업은 되돌릴 수 없습니다.
      </p>
    </ModalShell>
  )
}

export default DeleteModal
