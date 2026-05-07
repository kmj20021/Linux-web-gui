import { useEffect, useRef, useImperativeHandle, forwardRef } from 'react'
import { Terminal as XTerm } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import '@xterm/xterm/css/xterm.css'

const Terminal = forwardRef(function Terminal({ onSessionId, onCwdChange, onUserChange, onConnected }, ref) {
  const containerRef = useRef(null)
  const termRef = useRef(null)
  const wsRef = useRef(null)
  const fitAddonRef = useRef(null)

  useImperativeHandle(ref, () => ({
    sendCommand(cmd) {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(cmd + '\r')
      }
    }
  }))

  useEffect(() => {
    const term = new XTerm({
      cursorBlink: true,
      fontSize: 13,
      fontFamily: "'SFMono-Regular', 'Consolas', 'Liberation Mono', 'Menlo', monospace",
      theme: {
        background: '#0d1117',
        foreground: '#c9d1d9',
        cursor: '#c9d1d9',
        cursorAccent: '#0d1117',
        black: '#484f58',
        red: '#ff7b72',
        green: '#3fb950',
        yellow: '#e3b341',
        blue: '#79c0ff',
        magenta: '#d2a8ff',
        cyan: '#56d364',
        white: '#b1bac4',
        brightBlack: '#6e7681',
        brightRed: '#ffa198',
        brightGreen: '#56d364',
        brightYellow: '#e3b341',
        brightBlue: '#79c0ff',
        brightMagenta: '#d2a8ff',
        brightCyan: '#39c5cf',
        brightWhite: '#ffffff',
        selectionBackground: '#264f78',
      },
      scrollback: 2000,
    })

    const fitAddon = new FitAddon()
    term.loadAddon(fitAddon)

    if (containerRef.current) {
      term.open(containerRef.current)
      fitAddon.fit()
    }

    termRef.current = term
    fitAddonRef.current = fitAddon

    const handleResize = () => {
      if (fitAddonRef.current) {
        try { fitAddonRef.current.fit() } catch (e) {}
      }
    }
    window.addEventListener('resize', handleResize)

    const token = localStorage.getItem('auth_token')
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/shell?token=${token}`

    term.write('\x1b[33m터미널에 연결 중...\x1b[0m\r\n')

    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      if (onConnected) onConnected(true)
      // 초기 터미널 크기 전송
      ws.send(JSON.stringify({ type: 'resize', cols: term.cols, rows: term.rows }))
    }

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        if (msg.type === 'data') {
          term.write(msg.data)
        } else if (msg.type === 'meta') {
          if (msg.session_id && onSessionId) onSessionId(msg.session_id)
          if (msg.cwd && onCwdChange) onCwdChange(msg.cwd)
          if (msg.user && onUserChange) onUserChange(msg.user)
        }
      } catch (e) {
        term.write(event.data)
      }
    }

    ws.onerror = () => {
      term.write('\r\n\x1b[31m웹소켓 연결 오류가 발생했습니다.\x1b[0m\r\n')
    }

    ws.onclose = (event) => {
      term.write(`\r\n\x1b[33m연결이 종료되었습니다. (코드: ${event.code})\x1b[0m\r\n`)
      if (onConnected) onConnected(false)
    }

    // 키보드 입력 → WebSocket (raw pass-through, bash가 처리)
    term.onData(data => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(data)
      }
    })

    // 터미널 리사이즈 → WebSocket
    term.onResize(({ cols, rows }) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'resize', cols, rows }))
      }
    })

    return () => {
      window.removeEventListener('resize', handleResize)
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
      if (termRef.current) {
        termRef.current.dispose()
        termRef.current = null
      }
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div
      ref={containerRef}
      className="xterm-container"
      style={{ width: '100%', height: '100%' }}
    />
  )
})

export default Terminal
