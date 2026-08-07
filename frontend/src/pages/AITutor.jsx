import { useEffect, useRef, useState } from 'react'
import { aiTutorAPI, AITutorAPIError } from '../api/aiTutor'
import '../styles/AITutor.css'

// AI 리눅스 학습 페이지.
// 명령은 실제로 실행되지 않고 backend/services/virtual_linux.py 의 결정적
// 시뮬레이터가 채점 가능한 성공/실패를 결정한다. 미지원/무관한 명령을 치면
// 터미널에는 원문(unsupported_syntax)이 그대로 남고, 백그라운드에서 Bedrock이
// 현재 상태를 참고해 만든 설명이 AI 도우미 패널에 별도로 추가된다 — 이 설명은
// 절대 virtual_state나 채점에 영향을 주지 않는다(narrateCommand 참고).
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

  // Fire-and-forget: never awaited by runGuarded, never surfaces as a page
  // error. On success it adds a standalone entry to the AI 도우미 panel; on
  // failure or degradation it adds nothing, leaving the terminal untouched
  // (see docs: AI 튜터 narrate 계획).
  const narrateInBackground = (sessionId, attemptId, commandTextValue) => {
    aiTutorAPI.narrateCommand(sessionId, attemptId)
      .then((result) => {
        if (result.narration.degraded) return
        setChatLog(prev => [...prev,
          { type: 'narration', text: result.narration.terminal_output, command: commandTextValue },
        ])
      })
      .catch(() => { /* nothing to show */ })
  }

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
      if (result.result_code !== 'success') {
        narrateInBackground(session.id, result.attempt_id, text)
      }
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
        const isReview = refreshed.current_problem.task_id.startsWith('review_')
        const text = isReview
          ? `복습 라운드입니다: ${refreshed.current_problem.title}`
          : `다음 문제: ${refreshed.current_problem.title}`
        setCommandLog(prev => [...prev, { type: 'system', text }])
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
        기반 로직이 결정합니다. 미지원하거나 문제와 무관한 명령을 치면 AI가 참고용 설명을
        오른쪽 AI 도우미 패널에 추가로 보여줄 수 있지만, 이는 항상 표시용일 뿐 실제 상태나
        채점에는 영향을 주지 않습니다.
      </div>

      <div className="ai-main">
        <aside className="ai-curriculum">
          <h2 className="ai-section-title">커리큘럼</h2>
          {curriculumError && <div className="ai-error">{curriculumError}</div>}
          <ul className="ai-problem-list">
            {curriculum.map((problem) => {
              // The catalog's final slot is a generic preview: the real
              // problem (task_id "review_<id>") is only chosen once a
              // session completes the first five, so it can't be started
              // directly here.
              const isReviewPlaceholder = problem.task_id === 'review'
              const isActive = session?.current_problem?.task_id === problem.task_id
                || (isReviewPlaceholder && session?.current_problem?.task_id?.startsWith('review_'))
              return (
                <li key={`${problem.scenario_id}:${problem.task_id}`}>
                  <button
                    className={`ai-problem-item ${isActive ? 'active' : ''} ${isReviewPlaceholder ? 'ai-review-locked' : ''}`}
                    onClick={() => !isReviewPlaceholder && startProblem(problem)}
                    disabled={busy || isReviewPlaceholder}
                    title={isReviewPlaceholder ? '앞의 5문제를 모두 완료하면 자동으로 진행됩니다.' : undefined}
                  >
                    <span className="ai-problem-title">{problem.title}</span>
                    {isReviewPlaceholder ? (
                      <span className="ai-problem-difficulty ai-review-badge">복습</span>
                    ) : (
                      <span className={`ai-problem-difficulty ai-diff-${problem.difficulty}`}>{problem.difficulty}</span>
                    )}
                  </button>
                </li>
              )
            })}
          </ul>
        </aside>

        {!session ? (
          <div className="ai-empty">왼쪽에서 문제를 선택해 학습을 시작하세요.</div>
        ) : (
          <div className="ai-workspace">
            <div className="ai-problem-card">
              <h3>
                {session.current_problem.title}
                {session.current_problem.task_id.startsWith('review_') && (
                  <span className="ai-review-badge ai-review-badge-card">복습 라운드</span>
                )}
              </h3>
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
                      {entry.type === 'narration' && (
                        <span className="ai-narration-label">$ {entry.command}</span>
                      )}
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
