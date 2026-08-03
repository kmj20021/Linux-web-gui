import { useState } from 'react'
import ModalShell from './ModalShell'
import PermGrid from '../PermGrid'

function ChmodModal({ path, perms, onConfirm, onClose }) {
  const [localPerms, setLocalPerms] = useState([...perms])

  return (
    <ModalShell
      title="권한 수정"
      badge="chmod"
      size="perm-modal"
      onClose={onClose}
      footer={
        <>
          <button className="fs-action-btn cancel" onClick={onClose}>취소</button>
          <button className="fs-action-btn confirm" onClick={() => onConfirm(localPerms)}>적용</button>
        </>
      }
    >
      <div className="fs-modal-info">{path}</div>
      <PermGrid perms={localPerms} onChange={setLocalPerms} />
    </ModalShell>
  )
}

export default ChmodModal
