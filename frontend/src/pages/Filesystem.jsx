import { useCallback, useState } from 'react'
import '../styles/Filesystem.css'

import {
  ROOT_PATH,
  buildInitialFS,
  changePermissions,
  createDirectory,
  createFile,
  listDirectories,
  moveEntry,
  removeEntry,
  toggleDirectory,
  writeFile,
} from '../features/filesystem/filesystemModel'
import { basename, dirname, isWithin } from '../features/filesystem/paths'
import { permsToOctal } from '../features/filesystem/permissions'
import { useCommandLog } from '../features/filesystem/useCommandLog'
import { useToasts } from '../features/filesystem/useToasts'

import DetailPanel from '../features/filesystem/components/DetailPanel'
import FileTree from '../features/filesystem/components/FileTree'
import ToastStack from '../features/filesystem/components/ToastStack'
import ChmodModal from '../features/filesystem/components/modals/ChmodModal'
import CreateEntryModal from '../features/filesystem/components/modals/CreateEntryModal'
import DeleteModal from '../features/filesystem/components/modals/DeleteModal'
import EditModal from '../features/filesystem/components/modals/EditModal'
import MoveModal from '../features/filesystem/components/modals/MoveModal'

// 새로 만들어지거나 이동한 항목을 잠시 강조하는 시간
const HIGHLIGHT_MS = 600

// 교육용 가상 파일시스템 탐색기 페이지.
// 상태 전이는 features/filesystem/filesystemModel의 순수 함수가 담당하고,
// 이 컴포넌트는 조작 결과를 트리·로그·토스트에 반영하는 역할만 한다.
function FilesystemPage() {
  const [fs, setFs] = useState(buildInitialFS)
  const [selectedPath, setSelectedPath] = useState(null)
  const [newPath, setNewPath] = useState(null)
  const [modal, setModal] = useState(null)

  const { logs, addLog, clearLogs, bodyRef } = useCommandLog()
  const { toasts, showToast } = useToasts()

  const closeModal = () => setModal(null)

  const highlight = useCallback((path) => {
    setNewPath(path)
    setTimeout(() => setNewPath(current => (current === path ? null : current)), HIGHLIGHT_MS)
  }, [])

  const selectedNode = selectedPath ? fs[selectedPath] : null
  const isSelected = !!selectedPath
  const isFileSelected = isSelected && selectedNode?.type === 'file'

  const handleToggle = useCallback((path) => {
    setFs(prev => toggleDirectory(prev, path))
  }, [])

  // 모델 결과를 트리·로그·토스트에 반영한다. 실패면 모달을 열어 둔 채 알린다.
  const apply = (result, successMessage) => {
    if (!result.ok) {
      showToast(result.error, 'error')
      return false
    }
    setFs(result.fs)
    addLog(result.command)
    showToast(successMessage)
    closeModal()
    return true
  }

  const handleMkdir = (parentPath, name) => {
    const result = createDirectory(fs, parentPath, name)
    if (apply(result, `폴더 '${basename(result.path || '')}' 생성 완료`)) {
      highlight(result.path)
    }
  }

  const handleTouch = (parentPath, name) => {
    const result = createFile(fs, parentPath, name)
    if (apply(result, `파일 '${basename(result.path || '')}' 생성 완료`)) {
      highlight(result.path)
    }
  }

  const handleDelete = (path) => {
    const result = removeEntry(fs, path)
    if (apply(result, `'${basename(path)}' 삭제 완료`)) {
      if (selectedPath && isWithin(selectedPath, path)) setSelectedPath(null)
    }
  }

  const handleEdit = (path, content) => {
    apply(writeFile(fs, path, content), `'${basename(path)}' 저장 완료`)
  }

  const handleMove = (srcPath, destDir) => {
    const result = moveEntry(fs, srcPath, destDir)
    if (apply(result, `'${basename(srcPath)}' 이동 완료`)) {
      if (selectedPath === srcPath) setSelectedPath(result.path)
      highlight(result.path)
    }
  }

  const handleChmod = (path, perms) => {
    apply(changePermissions(fs, path, perms), `권한 변경 완료: chmod ${permsToOctal(perms)}`)
  }

  // 선택 항목이 폴더면 그 안에, 파일이면 그 부모 폴더에 만든다.
  const targetDirectory = () =>
    selectedNode?.type === 'directory' ? selectedPath : dirname(selectedPath)

  const renderModal = () => {
    if (!modal) return null
    const node = fs[modal.path]

    switch (modal.type) {
      case 'mkdir':
        return (
          <CreateEntryModal
            kind="directory"
            parentPath={modal.path}
            onConfirm={(name) => handleMkdir(modal.path, name)}
            onClose={closeModal}
          />
        )
      case 'touch':
        return (
          <CreateEntryModal
            kind="file"
            parentPath={modal.path}
            onConfirm={(name) => handleTouch(modal.path, name)}
            onClose={closeModal}
          />
        )
      case 'delete':
        return (
          <DeleteModal
            path={modal.path}
            isDir={node?.type === 'directory'}
            onConfirm={() => handleDelete(modal.path)}
            onClose={closeModal}
          />
        )
      case 'edit':
        return (
          <EditModal
            path={modal.path}
            content={node?.content || ''}
            onConfirm={(content) => handleEdit(modal.path, content)}
            onClose={closeModal}
          />
        )
      case 'move':
        return (
          <MoveModal
            srcPath={modal.path}
            dirs={listDirectories(fs).filter(d => d !== modal.path)}
            onConfirm={(dest) => handleMove(modal.path, dest)}
            onClose={closeModal}
          />
        )
      case 'chmod':
        return (
          <ChmodModal
            path={modal.path}
            perms={node?.permissions || Array(9).fill(false)}
            onConfirm={(perms) => handleChmod(modal.path, perms)}
            onClose={closeModal}
          />
        )
      default:
        return null
    }
  }

  return (
    <div className="filesystem-page">
      {/* 가상 환경 고지: 항상 표시한다 */}
      <div className="fs-simulation-notice" data-testid="fs-simulation-notice">
        교육용 가상 파일시스템입니다. 브라우저 안에서만 동작하며 실제 서버
        파일시스템을 변경하지 않습니다.
      </div>

      {/* 상단 툴바 */}
      <div className="fs-toolbar">
        <span className="fs-toolbar-title">파일시스템 탐색기</span>
        <div className="fs-toolbar-divider" />

        <button
          className="fs-btn success"
          disabled={!isSelected}
          onClick={() => setModal({ type: 'mkdir', path: targetDirectory() })}
        >
          <span className="fs-btn-label">폴더 생성</span>
          <span className="fs-btn-cmd">mkdir</span>
        </button>

        <button
          className="fs-btn primary"
          disabled={!isSelected}
          onClick={() => setModal({ type: 'touch', path: targetDirectory() })}
        >
          <span className="fs-btn-label">파일 생성</span>
          <span className="fs-btn-cmd">touch</span>
        </button>

        <div className="fs-toolbar-divider" />

        <button
          className="fs-btn danger"
          disabled={!isSelected}
          onClick={() => setModal({ type: 'delete', path: selectedPath })}
        >
          <span className="fs-btn-label">{isFileSelected ? '파일 삭제' : '폴더 삭제'}</span>
          <span className="fs-btn-cmd">{isFileSelected ? 'rm' : 'rm -rf'}</span>
        </button>

        <button
          className="fs-btn warning"
          disabled={!isSelected}
          onClick={() => setModal({ type: 'move', path: selectedPath })}
        >
          <span className="fs-btn-label">이동</span>
          <span className="fs-btn-cmd">mv</span>
        </button>

        <div className="fs-toolbar-divider" />

        <button
          className="fs-btn primary"
          disabled={!isFileSelected}
          onClick={() => setModal({ type: 'edit', path: selectedPath })}
        >
          <span className="fs-btn-label">파일 수정</span>
          <span className="fs-btn-cmd">nano</span>
        </button>

        <button
          className="fs-btn warning"
          disabled={!isSelected}
          onClick={() => setModal({ type: 'chmod', path: selectedPath })}
        >
          <span className="fs-btn-label">권한 수정</span>
          <span className="fs-btn-cmd">chmod</span>
        </button>
      </div>

      {/* 메인 영역: 트리 + 상세 */}
      <div className="fs-main">
        <div className="fs-tree-panel">
          <div className="fs-tree-panel-header">파일 트리</div>
          <div className="fs-tree-body" data-testid="fs-tree">
            <FileTree
              rootPath={ROOT_PATH}
              fs={fs}
              selectedPath={selectedPath}
              onSelect={setSelectedPath}
              onToggle={handleToggle}
              newPath={newPath}
            />
          </div>
        </div>

        <div className="fs-detail-panel">
          {!selectedPath ? (
            <div className="fs-detail-empty">
              <div className="fs-detail-empty-icon">[F]</div>
              <div>항목을 선택하면 상세 정보가 표시됩니다.</div>
            </div>
          ) : (
            <DetailPanel path={selectedPath} node={selectedNode} />
          )}
        </div>
      </div>

      {/* 하단 명령어 로그 */}
      <div className="fs-log-panel">
        <div className="fs-log-header">
          <span className="fs-log-header-title">명령어 로그 (Command Log)</span>
          <button className="fs-log-clear-btn" onClick={clearLogs}>clear</button>
        </div>
        <div className="fs-log-body" ref={bodyRef} data-testid="fs-command-log">
          {logs.map(entry => (
            <div key={entry.id} className="fs-log-entry">
              <span className="fs-log-time">[{entry.time}]</span>
              <span className="fs-log-prompt">user@linux:~$</span>
              <span className="fs-log-cmd">{entry.cmd}</span>
              {entry.result && (
                <span className={`fs-log-result${entry.result.includes('오류') ? ' error' : ''}`}>
                  # {entry.result}
                </span>
              )}
            </div>
          ))}
        </div>
      </div>

      {renderModal()}

      <ToastStack toasts={toasts} />
    </div>
  )
}

export default FilesystemPage
