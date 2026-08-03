import { useState } from 'react'
import ModalShell from './ModalShell'

function MoveModal({ srcPath, dirs, onConfirm, onClose }) {
  const [dest, setDest] = useState(dirs[0] || '')

  return (
    <ModalShell
      title="이동"
      badge="mv"
      onClose={onClose}
      footer={
        <>
          <button className="fs-action-btn cancel" onClick={onClose}>취소</button>
          <button className="fs-action-btn confirm" onClick={() => onConfirm(dest)}>이동</button>
        </>
      }
    >
      <div className="fs-modal-info">원본: {srcPath}</div>
      <div className="fs-modal-field">
        <label className="fs-modal-label" htmlFor="fs-move-dest">이동할 폴더 선택</label>
        <select
          id="fs-move-dest"
          className="fs-modal-select"
          value={dest}
          onChange={e => setDest(e.target.value)}
        >
          {dirs.map(d => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>
      </div>
    </ModalShell>
  )
}

export default MoveModal
