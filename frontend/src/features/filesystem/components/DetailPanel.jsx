import { basename } from '../paths'
import { permsToOctal, permsToString } from '../permissions'

// 선택된 항목의 상세 정보 패널
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
            {node.children.map(child => (
              <span key={child} className="fs-detail-info-value" style={{ gridColumn: '1 / -1' }}>
                {child}
              </span>
            ))}
          </div>
        </div>
      )}
    </>
  )
}

export default DetailPanel
