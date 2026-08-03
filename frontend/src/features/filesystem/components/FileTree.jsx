import { basename } from '../paths'

// 파일 타입에 따른 아이콘 텍스트
function fileIcon(name) {
  if (name.endsWith('.md')) return 'M'
  if (name.endsWith('.jpg') || name.endsWith('.png') || name.endsWith('.jpeg')) return 'I'
  if (name.endsWith('.tar.gz') || name.endsWith('.zip') || name.endsWith('.gz')) return 'Z'
  return 'F'
}

// 트리 노드 재귀 컴포넌트
function TreeNode({ path, fs, selectedPath, onSelect, onToggle, depth, newPath }) {
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
          {isDir ? (node.expanded ? '[=]' : '[+]') : fileIcon(name)}
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

// 트리 패널 진입점
function FileTree({ rootPath, fs, selectedPath, onSelect, onToggle, newPath }) {
  return (
    <TreeNode
      path={rootPath}
      fs={fs}
      selectedPath={selectedPath}
      onSelect={onSelect}
      onToggle={onToggle}
      depth={0}
      newPath={newPath}
    />
  )
}

export default FileTree
