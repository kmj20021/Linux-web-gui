// 가상 파일시스템 경로 유틸리티.
// 실제 OS 경로가 아니라 교육용 트리의 키를 다룬다.

// 경로에서 파일/폴더 이름 추출
export function basename(path) {
  return path.split('/').filter(Boolean).pop() || '/'
}

// 경로에서 부모 경로 추출
export function dirname(path) {
  const parts = path.split('/').filter(Boolean)
  parts.pop()
  return parts.length === 0 ? '/' : '/' + parts.join('/')
}

// 부모 경로와 이름을 연결
export function joinPath(parentPath, name) {
  return parentPath === '/' ? `/${name}` : `${parentPath}/${name}`
}

// path가 ancestor 자신이거나 그 하위인지 판정
export function isWithin(path, ancestor) {
  return path === ancestor || path.startsWith(ancestor + '/')
}
