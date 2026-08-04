import { useEffect, useRef, useState } from 'react'
import { aiTutorAPI, AITutorAPIError } from '../api/aiTutor'
import '../styles/AITutor.css'

// AI 리눅스 학습 페이지.
// 명령은 실제로 실행되지 않고 backend/services/virtual_linux.py 의 결정적
// 시뮬레이터가 처리한다. Bedrock 은 명령 실행 결과에는 관여하지 않고,
// 오직 "AI 도우미" 패널의 질문/힌트 응답에만 쓰인다 — 터미널과 채팅은
// 서로 다른 영역이라 섞이지 않는다.
function AITutor() {
  const [curriculum, setCurriculum] = useState([])
  const [curriculumError, setCurriculumError] = useState(null)
  const [session, setSession] = useState(null)
  const [commandLog, setCommandLog] = useState([])
  const [chatLog, setChatLog] = useState([])
  const [commandText, setCommandText] = useState('')
  const [chatText, setChatText] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const commandLogRef = useRef(null)
  const chatLogRef = useRef(null)

  useEffect(() => {
    aiTutorAPI.curriculum()
      .then(res => setCurriculum(res.items))
      .catch(err => setCurriculumError(err.message))
  }, [])

  useEffect(() => {
    if (commandLogRef.current) commandLogRef.current.scrollTop = commandLogRef.current.scrollHeight
  }, [commandLog])

  useEffect(() => {
    if (chatLogRef.current) chatLogRef.current.scrollTop = chatLogRef.current.scrollHeight
  }, [chatLog])

  const describeError = (err) => {
    if (err instanceof AITutorAPIError) {
      if (err.status === 429) {
        return `AI 요청이 너무 잦습니다. ${err.retryAfter || 1}초 후 다시 시도해 주세요.`
      }
      if (err.status === 409) {
        return '세션 상태가 바뀌었습니다. 문제를 다시 불러옵니다.'
      }
      return err.message
    }
    return '알 수 없는 오류가 발생했습니다.'
  }

  const refreshSession = async (sessionId) => {
    const refreshed = await aiTutorAPI.getSession(sessionId)
    setSession(refreshed)
    return refreshed
  }

  const runGuarded = async (fn) => {
    setBusy(true)
    setError(null)
    try {
      await fn()
    } catch (err) {
      setError(describeError(err))
      if (err instanceof AITutorAPIError && err.status === 409 && session) {
        try { await refreshSession(session.id) } catch { /* keep original error */ }
      }
    } finally {
      setBusy(false)
    }
  }

  const startProblem = (problem) => runGuarded(async () => {
    const created = await aiTutorAPI.createSession(problem)
    setSession(created)
    setCommandLog([{ type: 'system', text: `[${created.current_problem.title}] 학습을 시작합니다.` }])
    setChatLog([])
  })

  const submitCommand = () => {
    const text = commandText.trim()
    if (!text || !session) return
    runGuarded(async () => {
      const result = await aiTutorAPI.command(session.id, text, session.virtual_state.version)
      setCommandText('')
      setCommandLog(prev => [...prev,
        { type: 'command', text },
        { type: 'output', text: result.output },
      ])
      setSession(prev => ({ ...prev, virtual_state: { ...prev.virtual_state, version: result.version } }))
    })
  }

  const submitChat = () => {
    const text = chatText.trim()
    if (!text || !session) return
    runGuarded(async () => {
      const result = await aiTutorAPI.chat(session.id, text)
      setChatText('')
      setChatLog(prev => [...prev,
        { type: 'user', text },
        { type: 'assistant', text: result.bedrock.message, degraded: result.bedrock.degraded },
      ])
      setSession(prev => ({ ...prev, virtual_state: { ...prev.virtual_state, version: result.version } }))
    })
  }

  const requestHint = () => {
    if (!session) return
    runGuarded(async () => {
      const result = await aiTutorAPI.hint(session.id, session.virtual_state.version)
      setChatLog(prev => [...prev,
        { type: 'hint', text: `힌트 ${result.hint_level}: ${result.hint}` },
        { type: 'assistant', text: result.bedrock.message, degraded: result.bedrock.degraded },
      ])
      setSession(prev => ({ ...prev, virtual_state: { ...prev.virtual_state, version: result.version } }))
    })
  }

  const requestGrade = () => {
    if (!session) return
    runGuarded(async () => {
      const result = await aiTutorAPI.grade(session.id, session.virtual_state.version)
      const gradeLabel = { success: '성공', partial: '부분 성공', failure: '실패' }[result.grade]
      setCommandLog(prev => [...prev, { type: 'grade', text: `채점: ${gradeLabel} - ${result.description}` }])
      const refreshed = await refreshSession(session.id)
      if (result.progress.completed) {
        setCommandLog(prev => [...prev, { type: 'system', text: '커리큘럼을 모두 완료했습니다.' }])
      } else if (result.grade === 'success') {
        setCommandLog(prev => [...prev, { type: 'system', text: `다음 문제: ${refreshed.current_problem.title}` }])
      }
    })
  }

  const resetProblem = () => {
    if (!session) return
    runGuarded(async () => {
      const result = await aiTutorAPI.reset(session.id, session.virtual_state.version)
      setSession(result)
      setCommandLog(prev => [...prev, { type: 'system', text: '가상 상태를 초기화했습니다.' }])
    })
  }

  return (
    <div className="ai-page">
      <div className="ai-simulation-notice">
        교육용 시뮬레이션입니다. 명령은 실제로 실행되지 않으며, 채점은 항상 서버의 규칙
        기반 로직이 결정합니다. AI는 명령 결과에 대해 자동으로 코멘트하지 않고,
        오른쪽 "AI 도우미"에서 직접 물어볼 때만 답합니다.
      </div>

      <div className="ai-main">
        <aside className="ai-curriculum">
          <h2 className="ai-section-title">커리큘럼</h2>
          {curriculumError && <div className="ai-error">{curriculumError}</div>}
          <ul className="ai-problem-list">
            {curriculum.map((problem) => (
              <li key={`${problem.scenario_id}:${problem.task_id}`}>
                <button
                  className={`ai-problem-item ${session?.current_problem?.task_id === problem.task_id ? 'active' : ''}`}
                  onClick={() => startProblem(problem)}
                  disabled={busy}
                >
                  <span className="ai-problem-index">{problem.task_index}/{problem.total_tasks}</span>
                  <span className="ai-problem-title">{problem.title}</span>
                  <span className={`ai-problem-difficulty ai-diff-${problem.difficulty}`}>{problem.difficulty}</span>
                </button>
              </li>
            ))}
          </ul>
        </aside>

        {!session ? (
          <div className="ai-empty">왼쪽에서 문제를 선택해 학습을 시작하세요.</div>
        ) : (
          <div className="ai-workspace">
            <div className="ai-problem-card">
              <h3>{session.current_problem.title}</h3>
              <p>{session.current_problem.description}</p>
              <div className="ai-problem-meta">
                <span>학습 목표: {session.current_problem.learning_goal}</span>
                <span>버전: {session.virtual_state.version}</span>
                <span>상태: {session.status === 'completed' ? '완료' : '진행 중'}</span>
              </div>
              <div className="ai-actions">
                <button onClick={requestHint} disabled={busy || session.status === 'completed'}>힌트</button>
                <button onClick={requestGrade} disabled={busy || session.status === 'completed'}>채점</button>
                <button onClick={resetProblem} disabled={busy}>초기화</button>
              </div>
            </div>

            {error && <div className="ai-error">{error}</div>}

            <div className="ai-panels">
              <section className="ai-panel">
                <h4 className="ai-panel-title">터미널</h4>
                <div className="ai-log ai-log-terminal" ref={commandLogRef}>
                  {commandLog.map((entry, index) => (
                    <div key={index} className={`ai-log-entry ai-log-${entry.type}`}>
                      {entry.type === 'command' && <span className="ai-prompt">$ </span>}
                      {entry.text}
                    </div>
                  ))}
                </div>
                <form className="ai-input-row" onSubmit={(e) => { e.preventDefault(); submitCommand() }}>
                  <input
                    type="text"
                    placeholder="명령 입력 (예: systemctl status nginx)"
                    value={commandText}
                    onChange={(e) => setCommandText(e.target.value)}
                    disabled={busy || session.status === 'completed'}
                  />
                  <button type="submit" disabled={busy || !commandText.trim() || session.status === 'completed'}>실행</button>
                </form>
              </section>

              <section className="ai-panel">
                <h4 className="ai-panel-title">AI 도우미</h4>
                <div className="ai-log ai-log-chat" ref={chatLogRef}>
                  {chatLog.map((entry, index) => (
                    <div key={index} className={`ai-log-entry ai-log-${entry.type}`}>
                      {entry.text}
                      {entry.degraded && <span className="ai-degraded-badge">규칙 기반</span>}
                    </div>
                  ))}
                </div>
                <form className="ai-input-row" onSubmit={(e) => { e.preventDefault(); submitChat() }}>
                  <input
                    type="text"
                    placeholder="AI에게 질문하기"
                    value={chatText}
                    onChange={(e) => setChatText(e.target.value)}
                    disabled={busy || session.status === 'completed'}
                  />
                  <button type="submit" disabled={busy || !chatText.trim() || session.status === 'completed'}>질문</button>
                </form>
              </section>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default AITutor
