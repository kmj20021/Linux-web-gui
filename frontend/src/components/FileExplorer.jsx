import { useState, useEffect, useCallback, useRef } from 'react'

function getAllDirPaths(node) {
  if (!node || node.type !== 'directory') return []
  const paths = [node.path]
  if (node.children) {
    for (const child of node.children) {
      paths.push(...getAllDirPaths(child))
    }
  }
  return paths
}

/**
 * 파일탐색기 컴포넌트
 *
 * Props:
 *   sessionId       - 세션 ID (null이면 로딩 표시)
 *   currentCwd      - 현재 터미널 cwd (해당 경로 하이라이트)
 *   onNavigate(path) - 폴더 클릭 시 호출
 *   refreshTrigger  - 변경 시 트리 재조회
 */
function FileExplorer({ sessionId, currentCwd, onNavigate, onFileClick, refreshTrigger }) {
  const [tree, setTree] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [expandedPaths, setExpandedPaths] = useState(new Set(['/']))
  const [sessionExpired, setSessionExpired] = useState(false)
  const initializedRef = useRef(false)

  const fetchTree = useCallback(async () => {
    if (!sessionId || sessionExpired) return
    setLoading(true)
    setError(null)
    try {
      const token = localStorage.getItem('auth_token')
      const response = await fetch(`/api/shell/fs?session_id=${sessionId}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (response.status === 401) {
        setSessionExpired(true)
        setError('세션이 만료되었습니다. 페이지를 새로고침하세요.')
        return
      }
      if (!response.ok) {
        throw new Error(`파일시스템 조회 실패: ${response.status}`)
      }
      const data = await response.json()
      setTree(data.tree)
      if (!initializedRef.current && data.tree) {
        const allPaths = getAllDirPaths(data.tree)
        setExpandedPaths(new Set(allPaths))
        initializedRef.current = true
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [sessionId])

  // sessionId 또는 refreshTrigger 변경 시 재조회
  useEffect(() => {
    fetchTree()
  }, [fetchTree, refreshTrigger])

  // 3초마다 자동 갱신 (OSC 7 보조 수단)
  useEffect(() => {
    if (!sessionId) return
    const interval = setInterval(fetchTree, 3000)
    return () => clearInterval(interval)
  }, [sessionId, fetchTree])

  // currentCwd 변경 시 상위 경로 자동 펼치기
  useEffect(() => {
    if (!currentCwd) return
    const parts = currentCwd.split('/').filter(Boolean)
    const pathsToExpand = ['/']
    let accumulated = ''
    for (const part of parts) {
      accumulated += '/' + part
      pathsToExpand.push(accumulated)
    }
    setExpandedPaths(prev => {
      const next = new Set(prev)
      pathsToExpand.forEach(p => next.add(p))
      return next
    })
  }, [currentCwd])

  const toggleExpand = (path) => {
    setExpandedPaths(prev => {
      const next = new Set(prev)
      if (next.has(path)) {
        next.delete(path)
      } else {
        next.add(path)
      }
      return next
    })
  }

  const handleNodeClick = (node) => {
    if (node.type === 'directory') {
      toggleExpand(node.path)
      if (onNavigate) {
        onNavigate(node.path)
      }
    } else {
      if (onFileClick) {
        onFileClick(node.path)
      }
    }
  }

  if (!sessionId) {
    return (
      <div className="file-explorer-loading">
        <div className="file-explorer-spinner" />
        <span>세션 대기 중...</span>
      </div>
    )
  }

  if (loading && !tree) {
    return (
      <div className="file-explorer-loading">
        <div className="file-explorer-spinner" />
        <span>파일시스템 로딩 중...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="file-explorer-error">
        <span>로드 실패</span>
        <span className="file-explorer-error-text">{error}</span>
        <button
          onClick={fetchTree}
          style={{
            background: '#21262d',
            border: '1px solid #30363d',
            color: '#c9d1d9',
            padding: '4px 10px',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '11px',
            marginTop: '4px'
          }}
        >
          다시 시도
        </button>
      </div>
    )
  }

  if (!tree) {
    return (
      <div className="file-explorer-empty">
        <span>파일시스템 정보 없음</span>
      </div>
    )
  }

  return (
    <div className="file-explorer-body">
      <TreeNode
        node={tree}
        depth={0}
        expandedPaths={expandedPaths}
        currentCwd={currentCwd}
        onNodeClick={handleNodeClick}
      />
    </div>
  )
}

/**
 * 재귀적 트리 노드 컴포넌트
 */
function TreeNode({ node, depth, expandedPaths, currentCwd, onNodeClick }) {
  const isDir = node.type === 'directory'
  const isExpanded = expandedPaths.has(node.path)
  const isActive = currentCwd && (node.path === currentCwd || currentCwd.startsWith(node.path + '/'))
  const hasChildren = isDir && node.children && node.children.length > 0
  const indentWidth = depth * 12

  return (
    <div className="tree-node">
      <div
        className={`tree-node-row${isActive ? ' active' : ''}`}
        onClick={() => onNodeClick(node)}
        title={node.path}
      >
        {/* 들여쓰기 */}
        <span className="tree-node-indent" style={{ width: indentWidth, flexShrink: 0 }} />

        {/* 펼치기/접기 토글 */}
        <span className={`tree-node-toggle${hasChildren ? '' : ' empty'}`}>
          {hasChildren ? (
            isExpanded ? (
              <svg width="8" height="8" viewBox="0 0 8 8" fill="currentColor">
                <path d="M1 2.5L4 5.5L7 2.5" stroke="currentColor" strokeWidth="1.2" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            ) : (
              <svg width="8" height="8" viewBox="0 0 8 8" fill="currentColor">
                <path d="M2.5 1L5.5 4L2.5 7" stroke="currentColor" strokeWidth="1.2" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            )
          ) : null}
        </span>

        {/* 아이콘 */}
        <span className={`tree-node-icon ${isDir ? 'dir' : 'file'}`}>
          {isDir ? (
            <svg width="12" height="12" viewBox="0 0 14 14" fill="none">
              <path d="M1 4a1 1 0 0 1 1-1h3l1.5 1.5H12a1 1 0 0 1 1 1v5.5a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1V4z" fill="currentColor" opacity="0.85"/>
            </svg>
          ) : (
            <svg width="12" height="12" viewBox="0 0 14 14" fill="none">
              <path d="M3 1h5.5L11 3.5V13a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1z" stroke="currentColor" strokeWidth="1.1" fill="none"/>
              <path d="M8.5 1v3h2.5" stroke="currentColor" strokeWidth="1.1" fill="none"/>
            </svg>
          )}
        </span>

        {/* 이름 */}
        <span className={`tree-node-name${!isDir ? ' file-clickable' : ''}`}>{node.name}</span>
      </div>

      {/* 자식 노드 */}
      {isDir && isExpanded && hasChildren && (
        <div className="tree-node-children">
          {node.children
            .slice()
            .sort((a, b) => {
              // 디렉토리 먼저, 그 다음 이름순
              if (a.type === 'directory' && b.type !== 'directory') return -1
              if (a.type !== 'directory' && b.type === 'directory') return 1
              return a.name.localeCompare(b.name)
            })
            .map((child, idx) => (
              <TreeNode
                key={child.path || idx}
                node={child}
                depth={depth + 1}
                expandedPaths={expandedPaths}
                currentCwd={currentCwd}
                onNodeClick={onNodeClick}
              />
            ))
          }
        </div>
      )}
    </div>
  )
}

export default FileExplorer
