import { useEffect, useRef, useState } from 'react'
import ModalShell from './ModalShell'

// 폴더 생성(mkdir)과 파일 생성(touch)은 입력 하나만 다르므로 한 컴포넌트로 처리한다.
const PRESETS = {
  directory: {
    title: '폴더 생성',
    badge: 'mkdir -p',
    label: '폴더 이름',
    placeholder: '예: new-folder',
    inputId: 'fs-mkdir-name',
  },
  file: {
    title: '파일 생성',
    badge: 'touch',
    label: '파일 이름',
    placeholder: '예: newfile.txt',
    inputId: 'fs-touch-name',
  },
}

function CreateEntryModal({ kind, parentPath, onConfirm, onClose }) {
  const preset = PRESETS[kind]
  const [name, setName] = useState('')
  const inputRef = useRef(null)

  useEffect(() => inputRef.current?.focus(), [])

  const submit = () => onConfirm(name)

  return (
    <ModalShell
      title={preset.title}
      badge={preset.badge}
      onClose={onClose}
      footer={
        <>
          <button className="fs-action-btn cancel" onClick={onClose}>취소</button>
          <button className="fs-action-btn confirm" onClick={submit}>생성</button>
        </>
      }
    >
      <div className="fs-modal-info">{parentPath}/</div>
      <div className="fs-modal-field">
        <label className="fs-modal-label" htmlFor={preset.inputId}>{preset.label}</label>
        <input
          id={preset.inputId}
          ref={inputRef}
          className="fs-modal-input"
          placeholder={preset.placeholder}
          value={name}
          onChange={e => setName(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && submit()}
        />
      </div>
    </ModalShell>
  )
}

export default CreateEntryModal
