import { useCallback, useEffect, useRef, useState } from 'react'

// 현재 시각 HH:MM:SS 포맷
function nowTime() {
  const d = new Date()
  return [d.getHours(), d.getMinutes(), d.getSeconds()]
    .map(n => String(n).padStart(2, '0'))
    .join(':')
}

const INITIAL_ENTRY = {
  id: 'boot',
  time: '00:00:00',
  cmd: '# 파일시스템 탐색기 시작',
  result: '교육용 가상 파일시스템 로드 완료',
}

// 명령 기록 Hook.
// 실행된 것처럼 보여줄 명령 목록과, 새 항목이 추가될 때 바닥으로 따라가는
// 스크롤 ref를 관리한다.
export function useCommandLog() {
  const [logs, setLogs] = useState([INITIAL_ENTRY])
  const bodyRef = useRef(null)

  useEffect(() => {
    if (bodyRef.current) {
      bodyRef.current.scrollTop = bodyRef.current.scrollHeight
    }
  }, [logs])

  const addLog = useCallback((cmd, result = '완료') => {
    setLogs(prev => [
      ...prev,
      { id: `${Date.now()}-${prev.length}`, time: nowTime(), cmd, result },
    ])
  }, [])

  const clearLogs = useCallback(() => setLogs([]), [])

  return { logs, addLog, clearLogs, bodyRef }
}
