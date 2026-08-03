import { useState } from 'react'
import ModalShell from './ModalShell'
import { basename } from '../../paths'

function EditModal({ path, content, onConfirm, onClose }) {
  const [text, setText] = useState(content)

  return (
    <ModalShell
      title="파일 수정"
      badge={`nano ${basename(path)}`}
      size="wide"
      onClose={onClose}
      footer={
        <>
          <button className="fs-action-btn cancel" onClick={onClose}>취소</button>
          <button className="fs-action-btn confirm" onClick={() => onConfirm(text)}>저장</button>
        </>
      }
    >
      <div className="fs-modal-info">{path}</div>
      <textarea
        className="fs-modal-textarea"
        aria-label={`${basename(path)} 내용`}
        value={text}
        onChange={e => setText(e.target.value)}
        rows={10}
      />
    </ModalShell>
  )
}

export default EditModal
