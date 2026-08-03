import { useCallback, useEffect, useRef, useState } from 'react'

const MAX_ENTRIES = 50

function now() {
  return new Date().toLocaleTimeString('ko-KR', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function commentEntry(text) {
  return { id: `${Date.now()}-comment`, time: now(), type: 'comment', text }
}

// 시뮬레이션한 명령 기록 Hook. 최근 50건만 유지한다.
export function useSimulationLog(initialText) {
  const [entries, setEntries] = useState(() => [commentEntry(initialText)])
  const bodyRef = useRef(null)

  useEffect(() => {
    if (bodyRef.current) {
      bodyRef.current.scrollTop = bodyRef.current.scrollHeight
    }
  }, [entries])

  const addCommand = useCallback((text) => {
    setEntries(prev => {
      const next = [...prev, { id: `${Date.now()}-${prev.length}`, time: now(), type: 'cmd', text }]
      return next.length > MAX_ENTRIES ? next.slice(next.length - MAX_ENTRIES) : next
    })
  }, [])

  const resetLog = useCallback((text) => {
    setEntries([commentEntry(text)])
  }, [])

  return { entries, addCommand, resetLog, bodyRef }
}
