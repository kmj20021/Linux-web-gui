import { useCallback, useEffect, useRef, useState } from 'react'

const TOAST_TTL_MS = 3000

// 토스트 알림 Hook.
// 3초 뒤 자동으로 사라지며, 언마운트 시 남은 타이머를 정리한다.
export function useToasts() {
  const [toasts, setToasts] = useState([])
  const timersRef = useRef(new Set())

  useEffect(() => {
    const timers = timersRef.current
    return () => {
      timers.forEach(clearTimeout)
      timers.clear()
    }
  }, [])

  const showToast = useCallback((message, type = 'success') => {
    const id = `${Date.now()}-${Math.random()}`
    setToasts(prev => [...prev, { id, message, type }])

    const timer = setTimeout(() => {
      timersRef.current.delete(timer)
      setToasts(prev => prev.filter(t => t.id !== id))
    }, TOAST_TTL_MS)
    timersRef.current.add(timer)
  }, [])

  return { toasts, showToast }
}
