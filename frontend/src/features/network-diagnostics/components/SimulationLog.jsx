// 하단 커맨드 로그. 시뮬레이션한 명령만 남는다.
function SimulationLog({ entries, bodyRef, onClear }) {
  return (
    <div className="nd-log-panel">
      <div className="nd-log-header">
        <span className="nd-log-header-title">시뮬레이션한 명령 기록</span>
        <button className="nd-log-clear-btn" onClick={onClear}>지우기</button>
      </div>
      <div className="nd-log-body" ref={bodyRef} data-testid="nd-log">
        {entries.map(entry => (
          <div key={entry.id} className="nd-log-entry">
            <span className="nd-log-time">{entry.time}</span>
            {entry.type === 'comment' ? (
              <span className="nd-log-comment">{entry.text}</span>
            ) : (
              <>
                <span className="nd-log-prompt">$</span>
                <span className="nd-log-cmd">{entry.text}</span>
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

export default SimulationLog
