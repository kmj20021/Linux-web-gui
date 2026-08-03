import { useState } from 'react'
import '../styles/NetworkDiagnostics.css'

import { findTool } from '../features/network-diagnostics/tools'
import { useSimulationLog } from '../features/network-diagnostics/useSimulationLog'
import SimulationLog from '../features/network-diagnostics/components/SimulationLog'
import ToolDetail from '../features/network-diagnostics/components/ToolDetail'
import ToolList from '../features/network-diagnostics/components/ToolList'
import CurlModal from '../features/network-diagnostics/components/modals/CurlModal'
import NslookupModal from '../features/network-diagnostics/components/modals/NslookupModal'
import PingModal from '../features/network-diagnostics/components/modals/PingModal'
import SsModal from '../features/network-diagnostics/components/modals/SsModal'
import TracerouteModal from '../features/network-diagnostics/components/modals/TracerouteModal'

const MODALS = {
  ping: PingModal,
  traceroute: TracerouteModal,
  ss: SsModal,
  nslookup: NslookupModal,
  curl: CurlModal,
}

const LOG_START_TEXT = '# 네트워크 진단 도구 시작 (시뮬레이션)'
const LOG_CLEARED_TEXT = '# 기록 지움'

// 네트워크 진단 학습 페이지.
// 모든 출력은 features/network-diagnostics/simulators.js가 만든 예시이며,
// 이 페이지는 어떤 네트워크 요청도 보내지 않는다.
function NetworkDiagnostics() {
  const [selectedTool, setSelectedTool] = useState(null)
  const [results, setResults] = useState({})
  const [openModal, setOpenModal] = useState(null)

  const { entries, addCommand, resetLog, bodyRef } = useSimulationLog(LOG_START_TEXT)

  const tool = findTool(selectedTool)
  const ActiveModal = openModal ? MODALS[openModal] : null

  const handleRun = (toolId, command, lines) => {
    addCommand(command)
    setResults(prev => ({ ...prev, [toolId]: lines }))
    setOpenModal(null)
  }

  const handleClearResult = () => {
    if (!selectedTool) return
    setResults(prev => {
      const next = { ...prev }
      delete next[selectedTool]
      return next
    })
  }

  return (
    <div className="nd-page">
      {/* 시뮬레이션 고지: 항상 표시한다 */}
      <div className="nd-simulation-notice" data-testid="nd-simulation-notice">
        교육용 시뮬레이션입니다. 아래 결과는 미리 준비된 예시 출력이며 실제
        네트워크 요청을 보내지 않습니다.
      </div>

      {/* 상단 툴바 */}
      <div className="nd-toolbar">
        <span className="nd-toolbar-title">네트워크 진단</span>
        <div className="nd-toolbar-divider" />

        <button
          className="nd-btn primary"
          disabled={!selectedTool}
          onClick={() => selectedTool && setOpenModal(selectedTool)}
        >
          <span className="nd-btn-label">시뮬레이션</span>
          {tool && <span className="nd-btn-cmd">{tool.cmd}</span>}
        </button>

        <button
          className="nd-btn warning"
          disabled={!selectedTool}
          onClick={handleClearResult}
        >
          <span className="nd-btn-label">결과 지우기</span>
        </button>

        <div className="nd-toolbar-divider" />

        <button className="nd-btn" onClick={() => resetLog(LOG_CLEARED_TEXT)}>
          <span className="nd-btn-label">기록 지우기</span>
        </button>
      </div>

      {/* 메인 영역 */}
      <div className="nd-main">
        <ToolList selectedTool={selectedTool} onSelect={setSelectedTool} />
        <ToolDetail tool={tool} result={selectedTool ? results[selectedTool] : null} />
      </div>

      {/* 하단 명령 기록 */}
      <SimulationLog
        entries={entries}
        bodyRef={bodyRef}
        onClear={() => resetLog(LOG_CLEARED_TEXT)}
      />

      {ActiveModal && (
        <ActiveModal onRun={handleRun} onClose={() => setOpenModal(null)} />
      )}
    </div>
  )
}

export default NetworkDiagnostics
