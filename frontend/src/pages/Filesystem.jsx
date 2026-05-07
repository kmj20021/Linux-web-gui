import { useState, useRef, useEffect, useCallback } from 'react'
import '../styles/Filesystem.css'

// ============================================================
// 초기 가상 파일시스템 데이터
// ============================================================
const buildInitialFS = () => ({
  '/home/user': {
    type: 'directory',
    permissions: [true, true, true, true, false, true, true, false, true], // rwxr-xr-x
    owner: 'user',
    children: ['Documents', 'Pictures', 'Downloads', 'hello.txt'],
    expanded: true,
  },
  '/home/user/Documents': {
    type: 'directory',
    permissions: [true, true, true, true, false, true, true, false, true],
    owner: 'user',
    children: ['notes.txt', 'work'],
    expanded: false,
  },
  '/home/user/Documents/notes.txt': {
    type: 'file',
    permissions: [true, true, false, true, false, false, true, false, false],
    owner: 'user',
    content: '리눅스 파일시스템 학습 노트\n\n1. 모든 것은 파일이다\n2. 파일 경로는 /로 시작한다\n3. 디렉토리도 파일이다',
  },
  '/home/user/Documents/work': {
    type: 'directory',
    permissions: [true, true, true, true, false, true, true, false, true],
    owner: 'user',
    children: ['project.md'],
    expanded: false,
  },
  '/home/user/Documents/work/project.md': {
    type: 'file',
    permissions: [true, true, false, true, false, false, true, false, false],
    owner: 'user',
    content: '# 프로젝트 계획서\n\n## 목표\n- 리눅스 GUI 개발\n\n## 일정\n- 1주차: 설계\n- 2주차: 구현',
  },
  '/home/user/Pictures': {
    type: 'directory',
    permissions: [true, true, true, true, false, true, true, false, true],
    owner: 'user',
    children: ['vacation.jpg'],
    expanded: false,
  },
  '/home/user/Pictures/vacation.jpg': {
    type: 'file',
    permissions: [true, true, false, true, false, false, true, false, false],
    owner: 'user',
    content: '[이미지 파일 - JPEG 형식]',
  },
  '/home/user/Downloads': {
    type: 'directory',
    permissions: [true, true, true, true, false, true, true, false, true],
    owner: 'user',
    children: ['archive.tar.gz'],
    expanded: false,
  },
  '/home/user/Downloads/archive.tar.gz': {
    type: 'file',
    permissions: [true, true, false, true, false, false, true, false, false],
    owner: 'user',
    content: '[압축 파일 - tar.gz 형식]',
  },
  '/home/user/hello.txt': {
    type: 'file',
    permissions: [true, true, false, true, false, false, true, false, false],
    owner: 'user',
    content: 'Hello, Linux World!\n안녕하세요, 리눅스!',
  },
})

// ============================================================
// 유틸리티 함수
// ============================================================

// permissions 배열(9개) -> octal 문자열 (예: "755")
function permsToOctal(p) {
  const toDigit = (r, w, x) => (r ? 4 : 0) + (w ? 2 : 0) + (x ? 1 : 0)
  return `${toDigit(p[0], p[1], p[2])}${toDigit(p[3], p[4], p[5])}${toDigit(p[6], p[7], p[8])}`
}

// permissions 배열 -> rwx 문자열 (예: "rwxr-xr-x")
function permsToString(p) {
  const ch = (v, c) => (v ? c : '-')
  return (
    ch(p[0], 'r') + ch(p[1], 'w') + ch(p[2], 'x') +
    ch(p[3], 'r') + ch(p[4], 'w') + ch(p[5], 'x') +
    ch(p[6], 'r') + ch(p[7], 'w') + ch(p[8], 'x')
  )
}

// 경로에서 파일/폴더 이름 추출
function basename(path) {
  return path.split('/').filter(Boolean).pop() || '/'
}

// 경로에서 부모 경로 추출
function dirname(path) {
  const parts = path.split('/').filter(Boolean)
  parts.pop()
  return parts.length === 0 ? '/' : '/' + parts.join('/')
}

// 현재 시각 HH:MM:SS 포맷
function nowTime() {
  const d = new Date()
  return [d.getHours(), d.getMinutes(), d.getSeconds()]
    .map(n => String(n).padStart(2, '0'))
    .join(':')
}

// 파일 타입에 따른 아이콘 텍스트
function fileIcon(node) {
  if (node.type === 'directory') return 'D'
  const name = node._name || ''
  if (name.endsWith('.md')) return 'M'
  if (name.endsWith('.jpg') || name.endsWith('.png') || name.endsWith('.jpeg')) return 'I'
  if (name.endsWith('.tar.gz') || name.endsWith('.zip') || name.endsWith('.gz')) return 'Z'
  return 'F'
}

// ============================================================
// 권한 편집 체크박스 그리드
// ============================================================
function PermGrid({ perms, onChange }) {
  const rows = ['소유자', '그룹', '기타']
  const cols = ['읽기 (r)', '쓰기 (w)', '실행 (x)']

  return (
    <div>
      <div className="perm-octal-display">{permsToOctal(perms)}</div>
      <div className="perm-string-display">{permsToString(perms)}</div>
      <div className="perm-grid">
        {/* 헤더 행 */}
        <div className="perm-grid-cell header"></div>
        {cols.map(c => (
          <div key={c} className="perm-grid-cell header">{c}</div>
        ))}
        {/* 데이터 행 */}
        {rows.map((row, ri) => (
          [
            <div key={`label-${ri}`} className={`perm-grid-cell row-label${ri === 2 ? ' last-row' : ''}`}>{row}</div>,
            ...cols.map((_, ci) => {
              const idx = ri * 3 + ci
              return (
                <div key={`cell-${ri}-${ci}`} className={`perm-grid-cell${ri === 2 ? ' last-row' : ''}`}>
                  <input
                    type="checkbox"
                    className="perm-checkbox"
                    checked={perms[idx]}
                    onChange={e => {
                      const next = [...perms]
                      next[idx] = e.target.checked
                      onChange(next)
                    }}
                  />
                </div>
              )
            }),
          ]
        ))}
      </div>
    </div>
  )
}

// ============================================================
// 토스트 알림 컴포넌트
// ============================================================
function ToastContainer({ toasts, onRemove }) {
  return (
    <div className="fs-toast-container">
      {toasts.map(t => (
        <div key={t.id} className={`fs-toast${t.type === 'error' ? ' error' : ''}`}>
          <span className="fs-toast-icon">{t.type === 'error' ? 'X' : 'V'}</span>
          <span className="fs-toast-msg">{t.message}</span>
        </div>
      ))}
    </div>
  )
}

// ============================================================
// 트리 노드 재귀 컴포넌트
// ============================================================
function TreeNode({ path, fs, selectedPath, onSelect, onToggle, depth = 0, newPath }) {
  const node = fs[path]
  if (!node) return null

  const name = basename(path)
  const isDir = node.type === 'directory'
  const isSelected = selectedPath === path
  const isNew = newPath === path

  return (
    <div className="fs-tree-node">
      <div
        className={`fs-tree-row${isSelected ? ' selected' : ''}${isNew ? ' fade-in' : ''}`}
        style={{ paddingLeft: `${8 + depth * 16}px` }}
        onClick={() => {
          onSelect(path)
          if (isDir) onToggle(path)
        }}
      >
        {/* 폴더 토글 화살표 */}
        {isDir ? (
          <span className="fs-tree-toggle">
            {node.expanded ? '▼' : '▶'}
          </span>
        ) : (
          <span className="fs-tree-toggle empty">▶</span>
        )}

        {/* 아이콘 */}
        <span className={`fs-tree-icon ${isDir ? 'fs-tree-icon-dir' : 'fs-tree-icon-file'}`}>
          {isDir ? (node.expanded ? '[=]' : '[+]') : fileIcon({ ...node, _name: name })}
        </span>

        {/* 이름 */}
        <span className="fs-tree-name">{name}</span>
      </div>

      {/* 자식 노드 재귀 렌더링 */}
      {isDir && node.expanded && node.children && node.children.map(childName => {
        const childPath = path === '/' ? `/${childName}` : `${path}/${childName}`
        return (
          <TreeNode
            key={childPath}
            path={childPath}
            fs={fs}
            selectedPath={selectedPath}
            onSelect={onSelect}
            onToggle={onToggle}
            depth={depth + 1}
            newPath={newPath}
          />
        )
      })}
    </div>
  )
}

// ============================================================
// 메인 FilesystemPage 컴포넌트
// ============================================================
function FilesystemPage() {
  const [fs, setFs] = useState(buildInitialFS)
  const [selectedPath, setSelectedPath] = useState(null)
  const [newPath, setNewPath] = useState(null) // fade-in 대상
  const [logs, setLogs] = useState([
    { id: 1, time: '00:00:00', cmd: '# 파일시스템 탐색기 시작', result: '교육용 가상 파일시스템 로드 완료' },
  ])
  const [toasts, setToasts] = useState([])
  const [modal, setModal] = useState(null) // { type, ... }
  const logBodyRef = useRef(null)

  // 로그 자동 스크롤
  useEffect(() => {
    if (logBodyRef.current) {
      logBodyRef.current.scrollTop = logBodyRef.current.scrollHeight
    }
  }, [logs])

  // 새 경로 fade-in 타이머
  useEffect(() => {
    if (newPath) {
      const t = setTimeout(() => setNewPath(null), 600)
      return () => clearTimeout(t)
    }
  }, [newPath])

  // ---- 유틸 ----
  const addLog = useCallback((cmd, result = '완료') => {
    setLogs(prev => [
      ...prev,
      { id: Date.now() + Math.random(), time: nowTime(), cmd, result },
    ])
  }, [])

  const showToast = useCallback((message, type = 'success') => {
    const id = Date.now() + Math.random()
    setToasts(prev => [...prev, { id, message, type }])
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 3000)
  }, [])

  const closeModal = () => setModal(null)

  // 현재 선택된 노드
  const selectedNode = selectedPath ? fs[selectedPath] : null

  // 폴더 목록 (이동 목적지용)
  const allDirs = Object.entries(fs)
    .filter(([, n]) => n.type === 'directory')
    .map(([p]) => p)

  // ---- 파일시스템 조작 함수 ----

  // 폴더 토글
  const handleToggle = useCallback((path) => {
    setFs(prev => ({
      ...prev,
      [path]: { ...prev[path], expanded: !prev[path].expanded },
    }))
  }, [])

  // 폴더 생성
  const handleMkdir = (parentPath, name) => {
    if (!name.trim()) { showToast('이름을 입력하세요.', 'error'); return }
    const newFullPath = `${parentPath}/${name.trim()}`
    if (fs[newFullPath]) { showToast('이미 존재하는 이름입니다.', 'error'); return }
    const cmd = `mkdir -p ${newFullPath}`

    setFs(prev => {
      const parent = prev[parentPath]
      return {
        ...prev,
        [parentPath]: {
          ...parent,
          children: [...(parent.children || []), name.trim()],
          expanded: true,
        },
        [newFullPath]: {
          type: 'directory',
          permissions: [true, true, true, true, false, true, true, false, true],
          owner: 'user',
          children: [],
          expanded: false,
        },
      }
    })
    setNewPath(newFullPath)
    addLog(cmd)
    showToast(`폴더 '${name.trim()}' 생성 완료`)
    closeModal()
  }

  // 폴더/파일 삭제
  const handleDelete = (path) => {
    const node = fs[path]
    const isDir = node.type === 'directory'
    const cmd = isDir ? `rm -rf ${path}` : `rm ${path}`
    const parent = dirname(path)
    const name = basename(path)

    // 하위 경로 모두 수집
    const toDelete = Object.keys(fs).filter(p => p === path || p.startsWith(path + '/'))

    setFs(prev => {
      const next = { ...prev }
      toDelete.forEach(p => delete next[p])
      if (next[parent]) {
        next[parent] = {
          ...next[parent],
          children: (next[parent].children || []).filter(c => c !== name),
        }
      }
      return next
    })

    if (selectedPath && (selectedPath === path || selectedPath.startsWith(path + '/'))) {
      setSelectedPath(null)
    }
    addLog(cmd)
    showToast(`'${name}' 삭제 완료`)
    closeModal()
  }

  // 파일 생성
  const handleTouch = (parentPath, name) => {
    if (!name.trim()) { showToast('파일 이름을 입력하세요.', 'error'); return }
    const newFullPath = `${parentPath}/${name.trim()}`
    if (fs[newFullPath]) { showToast('이미 존재하는 이름입니다.', 'error'); return }
    const cmd = `touch ${newFullPath}`

    setFs(prev => {
      const parent = prev[parentPath]
      return {
        ...prev,
        [parentPath]: {
          ...parent,
          children: [...(parent.children || []), name.trim()],
          expanded: true,
        },
        [newFullPath]: {
          type: 'file',
          permissions: [true, true, false, true, false, false, true, false, false],
          owner: 'user',
          content: '',
        },
      }
    })
    setNewPath(newFullPath)
    addLog(cmd)
    showToast(`파일 '${name.trim()}' 생성 완료`)
    closeModal()
  }

  // 파일 편집
  const handleEdit = (path, content) => {
    const cmd = `nano ${path}`
    setFs(prev => ({
      ...prev,
      [path]: { ...prev[path], content },
    }))
    addLog(cmd)
    showToast(`'${basename(path)}' 저장 완료`)
    closeModal()
  }

  // 이동
  const handleMove = (srcPath, destDir) => {
    if (srcPath === destDir || destDir.startsWith(srcPath + '/')) {
      showToast('이동할 수 없는 경로입니다.', 'error'); return
    }
    const name = basename(srcPath)
    const destPath = `${destDir}/${name}`
    if (fs[destPath]) { showToast('목적지에 같은 이름이 존재합니다.', 'error'); return }
    const srcParent = dirname(srcPath)
    const cmd = `mv ${srcPath} ${destPath}`

    // 하위 경로 재작성
    const oldKeys = Object.keys(fs).filter(p => p === srcPath || p.startsWith(srcPath + '/'))

    setFs(prev => {
      const next = { ...prev }
      // 구 경로 삭제
      oldKeys.forEach(p => delete next[p])
      // 신 경로 추가
      oldKeys.forEach(p => {
        const newKey = destDir + p.slice(srcPath.length === 0 ? 0 : srcPath.length)
          .replace(/^/, p === srcPath ? '' : '')
        const adjusted = p === srcPath ? destPath : destPath + p.slice(srcPath.length)
        next[adjusted] = { ...prev[p] }
      })
      // 구 부모에서 제거
      if (next[srcParent]) {
        next[srcParent] = {
          ...next[srcParent],
          children: (next[srcParent].children || []).filter(c => c !== name),
        }
      }
      // 목적지 부모에 추가
      if (next[destDir]) {
        next[destDir] = {
          ...next[destDir],
          children: [...(next[destDir].children || []), name],
          expanded: true,
        }
      }
      return next
    })

    if (selectedPath === srcPath) setSelectedPath(destPath)
    setNewPath(destPath)
    addLog(cmd)
    showToast(`'${name}' 이동 완료`)
    closeModal()
  }

  // 권한 변경
  const handleChmod = (path, perms) => {
    const octal = permsToOctal(perms)
    const cmd = `chmod ${octal} ${path}`
    setFs(prev => ({
      ...prev,
      [path]: { ...prev[path], permissions: perms },
    }))
    addLog(cmd)
    showToast(`권한 변경 완료: chmod ${octal}`)
    closeModal()
  }

  // ---- 모달 렌더러 ----
  const renderModal = () => {
    if (!modal) return null

    // 폴더 생성
    if (modal.type === 'mkdir') {
      return (
        <MkdirModal
          parentPath={modal.path}
          onConfirm={(name) => handleMkdir(modal.path, name)}
          onClose={closeModal}
        />
      )
    }

    // 파일 생성
    if (modal.type === 'touch') {
      return (
        <TouchModal
          parentPath={modal.path}
          onConfirm={(name) => handleTouch(modal.path, name)}
          onClose={closeModal}
        />
      )
    }

    // 삭제 확인
    if (modal.type === 'delete') {
      const node = fs[modal.path]
      const isDir = node?.type === 'directory'
      return (
        <DeleteModal
          path={modal.path}
          isDir={isDir}
          onConfirm={() => handleDelete(modal.path)}
          onClose={closeModal}
        />
      )
    }

    // 파일 편집
    if (modal.type === 'edit') {
      const node = fs[modal.path]
      return (
        <EditModal
          path={modal.path}
          content={node?.content || ''}
          onConfirm={(content) => handleEdit(modal.path, content)}
          onClose={closeModal}
        />
      )
    }

    // 이동
    if (modal.type === 'move') {
      return (
        <MoveModal
          srcPath={modal.path}
          dirs={allDirs.filter(d => d !== modal.path)}
          onConfirm={(dest) => handleMove(modal.path, dest)}
          onClose={closeModal}
        />
      )
    }

    // 권한 변경
    if (modal.type === 'chmod') {
      const node = fs[modal.path]
      return (
        <ChmodModal
          path={modal.path}
          perms={node?.permissions || Array(9).fill(false)}
          onConfirm={(p) => handleChmod(modal.path, p)}
          onClose={closeModal}
        />
      )
    }

    return null
  }

  // ---- 툴바 버튼 클릭 핸들러 ----
  const handleBtnMkdir = () => {
    const targetDir = selectedNode?.type === 'directory' ? selectedPath : dirname(selectedPath)
    setModal({ type: 'mkdir', path: targetDir })
  }

  const handleBtnTouch = () => {
    const targetDir = selectedNode?.type === 'directory' ? selectedPath : dirname(selectedPath)
    setModal({ type: 'touch', path: targetDir })
  }

  const handleBtnDelete = () => {
    setModal({ type: 'delete', path: selectedPath })
  }

  const handleBtnEdit = () => {
    if (selectedNode?.type !== 'file') { showToast('파일을 선택해주세요.', 'error'); return }
    setModal({ type: 'edit', path: selectedPath })
  }

  const handleBtnMove = () => {
    setModal({ type: 'move', path: selectedPath })
  }

  const handleBtnChmod = () => {
    setModal({ type: 'chmod', path: selectedPath })
  }

  const isSelected = !!selectedPath
  const isFileSelected = isSelected && selectedNode?.type === 'file'

  return (
    <div className="filesystem-page">
      {/* 상단 툴바 */}
      <div className="fs-toolbar">
        <span className="fs-toolbar-title">파일시스템 탐색기</span>
        <div className="fs-toolbar-divider" />

        <button className="fs-btn success" disabled={!isSelected} onClick={handleBtnMkdir}>
          <span className="fs-btn-label">폴더 생성</span>
          <span className="fs-btn-cmd">mkdir</span>
        </button>

        <button className="fs-btn primary" disabled={!isSelected} onClick={handleBtnTouch}>
          <span className="fs-btn-label">파일 생성</span>
          <span className="fs-btn-cmd">touch</span>
        </button>

        <div className="fs-toolbar-divider" />

        <button className="fs-btn danger" disabled={!isSelected} onClick={handleBtnDelete}>
          <span className="fs-btn-label">{isFileSelected ? '파일 삭제' : '폴더 삭제'}</span>
          <span className="fs-btn-cmd">{isFileSelected ? 'rm' : 'rm -rf'}</span>
        </button>

        <button className="fs-btn warning" disabled={!isSelected} onClick={handleBtnMove}>
          <span className="fs-btn-label">이동</span>
          <span className="fs-btn-cmd">mv</span>
        </button>

        <div className="fs-toolbar-divider" />

        <button className="fs-btn primary" disabled={!isFileSelected} onClick={handleBtnEdit}>
          <span className="fs-btn-label">파일 수정</span>
          <span className="fs-btn-cmd">nano</span>
        </button>

        <button className="fs-btn warning" disabled={!isSelected} onClick={handleBtnChmod}>
          <span className="fs-btn-label">권한 수정</span>
          <span className="fs-btn-cmd">chmod</span>
        </button>
      </div>

      {/* 메인 영역: 트리 + 상세 */}
      <div className="fs-main">
        {/* 좌측 트리 패널 */}
        <div className="fs-tree-panel">
          <div className="fs-tree-panel-header">파일 트리</div>
          <div className="fs-tree-body">
            <TreeNode
              path="/home/user"
              fs={fs}
              selectedPath={selectedPath}
              onSelect={setSelectedPath}
              onToggle={handleToggle}
              depth={0}
              newPath={newPath}
            />
          </div>
        </div>

        {/* 우측 상세 패널 */}
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
          <button className="fs-log-clear-btn" onClick={() => setLogs([])}>clear</button>
        </div>
        <div className="fs-log-body" ref={logBodyRef}>
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

      {/* 모달 */}
      {renderModal()}

      {/* 토스트 */}
      <ToastContainer toasts={toasts} />
    </div>
  )
}

// ============================================================
// 상세 패널 컴포넌트
// ============================================================
function DetailPanel({ path, node }) {
  if (!node) return null
  const isDir = node.type === 'directory'
  const permStr = permsToString(node.permissions)
  const permOct = permsToOctal(node.permissions)

  return (
    <>
      <div className="fs-detail-section">
        <div className="fs-detail-section-title">항목 정보</div>
        <div className="fs-detail-info-grid">
          <span className="fs-detail-info-label">이름</span>
          <span className="fs-detail-info-value">{basename(path)}</span>
          <span className="fs-detail-info-label">경로</span>
          <span className="fs-detail-info-value">{path}</span>
          <span className="fs-detail-info-label">타입</span>
          <span className="fs-detail-info-value">{isDir ? '디렉토리' : '파일'}</span>
          <span className="fs-detail-info-label">권한</span>
          <span className="fs-detail-info-value perm">{permStr} ({permOct})</span>
          <span className="fs-detail-info-label">소유자</span>
          <span className="fs-detail-info-value">{node.owner}</span>
          {isDir && (
            <>
              <span className="fs-detail-info-label">항목 수</span>
              <span className="fs-detail-info-value">{(node.children || []).length}개</span>
            </>
          )}
        </div>
      </div>

      {!isDir && (
        <div className="fs-detail-section">
          <div className="fs-detail-section-title">파일 내용 미리보기</div>
          <div className="fs-detail-preview">
            {node.content || '(빈 파일)'}
          </div>
        </div>
      )}

      {isDir && node.children && node.children.length > 0 && (
        <div className="fs-detail-section">
          <div className="fs-detail-section-title">하위 항목</div>
          <div className="fs-detail-info-grid">
            {node.children.map((child, i) => (
              <span key={i} className="fs-detail-info-value" style={{ gridColumn: '1 / -1' }}>
                {child}
              </span>
            ))}
          </div>
        </div>
      )}
    </>
  )
}

// ============================================================
// 모달 컴포넌트들
// ============================================================

function MkdirModal({ parentPath, onConfirm, onClose }) {
  const [name, setName] = useState('')
  const inputRef = useRef(null)
  useEffect(() => inputRef.current?.focus(), [])

  const submit = () => onConfirm(name)

  return (
    <div className="fs-modal-overlay" onClick={onClose}>
      <div className="fs-modal" onClick={e => e.stopPropagation()}>
        <div className="fs-modal-header">
          <span className="fs-modal-title">
            폴더 생성
            <span className="fs-modal-cmd-badge">mkdir -p</span>
          </span>
          <button className="fs-modal-close" onClick={onClose}>x</button>
        </div>
        <div className="fs-modal-body">
          <div className="fs-modal-info">{parentPath}/</div>
          <div className="fs-modal-field">
            <label className="fs-modal-label">폴더 이름</label>
            <input
              ref={inputRef}
              className="fs-modal-input"
              placeholder="예: new-folder"
              value={name}
              onChange={e => setName(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && submit()}
            />
          </div>
        </div>
        <div className="fs-modal-footer">
          <button className="fs-action-btn cancel" onClick={onClose}>취소</button>
          <button className="fs-action-btn confirm" onClick={submit}>생성</button>
        </div>
      </div>
    </div>
  )
}

function TouchModal({ parentPath, onConfirm, onClose }) {
  const [name, setName] = useState('')
  const inputRef = useRef(null)
  useEffect(() => inputRef.current?.focus(), [])

  const submit = () => onConfirm(name)

  return (
    <div className="fs-modal-overlay" onClick={onClose}>
      <div className="fs-modal" onClick={e => e.stopPropagation()}>
        <div className="fs-modal-header">
          <span className="fs-modal-title">
            파일 생성
            <span className="fs-modal-cmd-badge">touch</span>
          </span>
          <button className="fs-modal-close" onClick={onClose}>x</button>
        </div>
        <div className="fs-modal-body">
          <div className="fs-modal-info">{parentPath}/</div>
          <div className="fs-modal-field">
            <label className="fs-modal-label">파일 이름</label>
            <input
              ref={inputRef}
              className="fs-modal-input"
              placeholder="예: newfile.txt"
              value={name}
              onChange={e => setName(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && submit()}
            />
          </div>
        </div>
        <div className="fs-modal-footer">
          <button className="fs-action-btn cancel" onClick={onClose}>취소</button>
          <button className="fs-action-btn confirm" onClick={submit}>생성</button>
        </div>
      </div>
    </div>
  )
}

function DeleteModal({ path, isDir, onConfirm, onClose }) {
  return (
    <div className="fs-modal-overlay" onClick={onClose}>
      <div className="fs-modal" onClick={e => e.stopPropagation()}>
        <div className="fs-modal-header">
          <span className="fs-modal-title">
            {isDir ? '폴더 삭제' : '파일 삭제'}
            <span className="fs-modal-cmd-badge">{isDir ? 'rm -rf' : 'rm'}</span>
          </span>
          <button className="fs-modal-close" onClick={onClose}>x</button>
        </div>
        <div className="fs-modal-body">
          <p className="fs-modal-warning">
            <strong>{path}</strong> {isDir ? '폴더와 모든 하위 항목을' : '파일을'} 삭제합니다.
            이 작업은 되돌릴 수 없습니다.
          </p>
        </div>
        <div className="fs-modal-footer">
          <button className="fs-action-btn cancel" onClick={onClose}>취소</button>
          <button className="fs-action-btn confirm danger" onClick={onConfirm}>삭제</button>
        </div>
      </div>
    </div>
  )
}

function EditModal({ path, content, onConfirm, onClose }) {
  const [text, setText] = useState(content)

  return (
    <div className="fs-modal-overlay" onClick={onClose}>
      <div className="fs-modal wide" onClick={e => e.stopPropagation()}>
        <div className="fs-modal-header">
          <span className="fs-modal-title">
            파일 수정
            <span className="fs-modal-cmd-badge">nano {basename(path)}</span>
          </span>
          <button className="fs-modal-close" onClick={onClose}>x</button>
        </div>
        <div className="fs-modal-body">
          <div className="fs-modal-info">{path}</div>
          <textarea
            className="fs-modal-textarea"
            value={text}
            onChange={e => setText(e.target.value)}
            rows={10}
          />
        </div>
        <div className="fs-modal-footer">
          <button className="fs-action-btn cancel" onClick={onClose}>취소</button>
          <button className="fs-action-btn confirm" onClick={() => onConfirm(text)}>저장</button>
        </div>
      </div>
    </div>
  )
}

function MoveModal({ srcPath, dirs, onConfirm, onClose }) {
  const [dest, setDest] = useState(dirs[0] || '')

  return (
    <div className="fs-modal-overlay" onClick={onClose}>
      <div className="fs-modal" onClick={e => e.stopPropagation()}>
        <div className="fs-modal-header">
          <span className="fs-modal-title">
            이동
            <span className="fs-modal-cmd-badge">mv</span>
          </span>
          <button className="fs-modal-close" onClick={onClose}>x</button>
        </div>
        <div className="fs-modal-body">
          <div className="fs-modal-info">원본: {srcPath}</div>
          <div className="fs-modal-field">
            <label className="fs-modal-label">이동할 폴더 선택</label>
            <select
              className="fs-modal-select"
              value={dest}
              onChange={e => setDest(e.target.value)}
            >
              {dirs.map(d => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>
        </div>
        <div className="fs-modal-footer">
          <button className="fs-action-btn cancel" onClick={onClose}>취소</button>
          <button className="fs-action-btn confirm" onClick={() => onConfirm(dest)}>이동</button>
        </div>
      </div>
    </div>
  )
}

function ChmodModal({ path, perms, onConfirm, onClose }) {
  const [localPerms, setLocalPerms] = useState([...perms])

  return (
    <div className="fs-modal-overlay" onClick={onClose}>
      <div className="fs-modal perm-modal" onClick={e => e.stopPropagation()}>
        <div className="fs-modal-header">
          <span className="fs-modal-title">
            권한 수정
            <span className="fs-modal-cmd-badge">chmod</span>
          </span>
          <button className="fs-modal-close" onClick={onClose}>x</button>
        </div>
        <div className="fs-modal-body">
          <div className="fs-modal-info">{path}</div>
          <PermGrid perms={localPerms} onChange={setLocalPerms} />
        </div>
        <div className="fs-modal-footer">
          <button className="fs-action-btn cancel" onClick={onClose}>취소</button>
          <button className="fs-action-btn confirm" onClick={() => onConfirm(localPerms)}>적용</button>
        </div>
      </div>
    </div>
  )
}

export default FilesystemPage
