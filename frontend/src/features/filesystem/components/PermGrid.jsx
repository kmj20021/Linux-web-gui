import { permsToOctal, permsToString } from '../permissions'

const ROWS = ['소유자', '그룹', '기타']
const COLS = ['읽기 (r)', '쓰기 (w)', '실행 (x)']

// 권한 편집 체크박스 그리드
function PermGrid({ perms, onChange }) {
  return (
    <div>
      <div className="perm-octal-display">{permsToOctal(perms)}</div>
      <div className="perm-string-display">{permsToString(perms)}</div>
      <div className="perm-grid">
        {/* 헤더 행 */}
        <div className="perm-grid-cell header"></div>
        {COLS.map(c => (
          <div key={c} className="perm-grid-cell header">{c}</div>
        ))}
        {/* 데이터 행 */}
        {ROWS.map((row, ri) => (
          [
            <div key={`label-${ri}`} className={`perm-grid-cell row-label${ri === 2 ? ' last-row' : ''}`}>{row}</div>,
            ...COLS.map((col, ci) => {
              const idx = ri * 3 + ci
              return (
                <div key={`cell-${ri}-${ci}`} className={`perm-grid-cell${ri === 2 ? ' last-row' : ''}`}>
                  <input
                    type="checkbox"
                    className="perm-checkbox"
                    aria-label={`${row} ${col}`}
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

export default PermGrid
