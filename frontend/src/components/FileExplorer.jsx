import { useState, useEffect, useCallback, useRef } from 'react'
import { apiFetch } from '../api/client'

function mergeNodeAtPath(node, replacement) {
  if (!node) return replacement
  if (node.path === replacement.path) {
    const previousChildren = new Map((node.children || []).map(child => [child.path, child]))
    return {
      ...replacement,
      children: (replacement.children || []).map(child => {
        const previous = previousChildren.get(child.path)
        return previous?.children ? { ...child, children: previous.children } : child
      })
    }
  }
  if (!node.children) return node
  return { ...node, children: node.children.map(child => mergeNodeAtPath(child, replacement)) }
}

/** 파일탐색기 컴포넌트 */
function FileExplorer({ sessionId, currentCwd, onNavigate, onFileClick, refreshTrigger }) {
  const [tree, setTree] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [expandedPaths, setExpandedPaths] = useState(new Set(['/home/user']))
  const loadedPathsRef = useRef(new Set())
  const pendingPathsRef = useRef(new Set())
  const requestVersionRef = useRef(0)

  const fetchNode = useCallback(async (path) => {
    if (!sessionId || pendingPathsRef.current.has(path)) return
    const requestVersion = requestVersionRef.current
    const pendingPaths = pendingPathsRef.current
    pendingPaths.add(path)
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams({ session_id: sessionId, path })
      const data = await apiFetch(`/shell/fs?${params}`)
      if (requestVersion !== requestVersionRef.current) return
      setTree(previous => mergeNodeAtPath(previous, data.tree))
      loadedPathsRef.current.add(path)
    } catch (err) {
      // 401 은 apiFetch 가 전역 인증 만료 처리로 넘긴다. 여기서는 표시만 한다.
      if (requestVersion === requestVersionRef.current) {
        setError(err.isAuthExpired ? '세션이 만료되었습니다. 다시 로그인하세요.' : err.message)
      }
    } finally {
      pendingPaths.delete(path)
      if (requestVersion === requestVersionRef.current) setLoading(false)
    }
  }, [sessionId])

  // A new shell session owns an independent, lazily-loaded tree.
  useEffect(() => {
    requestVersionRef.current += 1
    loadedPathsRef.current = new Set()
    pendingPathsRef.current = new Set()
    setTree(null)
    setExpandedPaths(new Set(['/home/user']))
    setError(null)
    if (sessionId) fetchNode('/home/user')
    return () => { requestVersionRef.current += 1 }
  }, [sessionId, fetchNode])

  // Explicit refreshes re-fetch only the root; already loaded descendants are retained.
  useEffect(() => {
    if (sessionId && refreshTrigger !== undefined) fetchNode('/home/user')
  }, [sessionId, refreshTrigger, fetchNode])

  const retry = () => {
    fetchNode('/home/user')
  }

  const handleNodeClick = (node) => {
    if (node.type !== 'directory') {
      if (onFileClick) onFileClick(node.path)
      return
    }

    const isExpanded = expandedPaths.has(node.path)
    setExpandedPaths(previous => {
      const next = new Set(previous)
      if (isExpanded) next.delete(node.path)
      else next.add(node.path)
      return next
    })
    if (!isExpanded && !loadedPathsRef.current.has(node.path)) fetchNode(node.path)
    if (onNavigate) onNavigate(node.path)
  }

  if (!sessionId) return <div className="file-explorer-loading" role="status"><div className="file-explorer-spinner" /><span>세션 대기 중...</span></div>
  if (loading && !tree) return <div className="file-explorer-loading" role="status"><div className="file-explorer-spinner" /><span>파일시스템 로딩 중...</span></div>
  if (error) {
    return <div className="file-explorer-error" role="alert"><span>로드 실패</span><span className="file-explorer-error-text">{error}</span><button onClick={retry} style={{ background: '#21262d', border: '1px solid #30363d', color: '#c9d1d9', padding: '4px 10px', borderRadius: '4px', cursor: 'pointer', fontSize: '11px', marginTop: '4px' }}>다시 시도</button></div>
  }
  if (!tree) return <div className="file-explorer-empty"><span>파일시스템 정보 없음</span></div>

  return <div className="file-explorer-body" role="tree" aria-label="파일 탐색기"><TreeNode node={tree} depth={0} expandedPaths={expandedPaths} currentCwd={currentCwd} onNodeClick={handleNodeClick} /></div>
}

function TreeNode({ node, depth, expandedPaths, currentCwd, onNodeClick }) {
  const isDir = node.type === 'directory'
  const isExpanded = expandedPaths.has(node.path)
  const isActive = currentCwd && (node.path === currentCwd || currentCwd.startsWith(node.path + '/'))
  const children = node.children || []

  // Enter 와 Space 는 마우스 클릭과 같은 동작을 한다.
  const handleKeyDown = (event) => {
    if (event.key !== 'Enter' && event.key !== ' ') return
    event.preventDefault()
    onNodeClick(node)
  }

  return <div className="tree-node">
    <div
      className={`tree-node-row${isActive ? ' active' : ''}`}
      role="treeitem"
      tabIndex={0}
      aria-expanded={isDir ? isExpanded : undefined}
      aria-selected={!!isActive}
      aria-level={depth + 1}
      onClick={() => onNodeClick(node)}
      onKeyDown={handleKeyDown}
      title={node.path}
    >
      <span className="tree-node-indent" style={{ width: depth * 12, flexShrink: 0 }} />
      <span className={`tree-node-toggle${isDir ? '' : ' empty'}`}>
        {isDir && (isExpanded ? <svg width="8" height="8" viewBox="0 0 8 8" fill="currentColor"><path d="M1 2.5L4 5.5L7 2.5" stroke="currentColor" strokeWidth="1.2" fill="none" strokeLinecap="round" strokeLinejoin="round" /></svg> : <svg width="8" height="8" viewBox="0 0 8 8" fill="currentColor"><path d="M2.5 1L5.5 4L2.5 7" stroke="currentColor" strokeWidth="1.2" fill="none" strokeLinecap="round" strokeLinejoin="round" /></svg>)}
      </span>
      <span className={`tree-node-icon ${isDir ? 'dir' : 'file'}`}>{isDir ? <svg width="12" height="12" viewBox="0 0 14 14" fill="none"><path d="M1 4a1 1 0 0 1 1-1h3l1.5 1.5H12a1 1 0 0 1 1 1v5.5a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1V4z" fill="currentColor" opacity="0.85" /></svg> : <svg width="12" height="12" viewBox="0 0 14 14" fill="none"><path d="M3 1h5.5L11 3.5V13a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1z" stroke="currentColor" strokeWidth="1.1" fill="none" /><path d="M8.5 1v3h2.5" stroke="currentColor" strokeWidth="1.1" fill="none" /></svg>}</span>
      <span className={`tree-node-name${!isDir ? ' file-clickable' : ''}`}>{node.name}</span>
    </div>
    {isDir && isExpanded && children.length > 0 && <div className="tree-node-children" role="group">{children.slice().sort((a, b) => (a.type === b.type ? a.name.localeCompare(b.name) : a.type === 'directory' ? -1 : 1)).map(child => <TreeNode key={child.path} node={child} depth={depth + 1} expandedPaths={expandedPaths} currentCwd={currentCwd} onNodeClick={onNodeClick} />)}</div>}
  </div>
}

export default FileExplorer
