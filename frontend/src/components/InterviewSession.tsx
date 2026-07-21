import { useState } from 'react'
import { startInterview, submitTurn, endInterview } from '../api/client'
import type { ResumeBundle, InterviewPlan } from '../types'

interface Message {
  role: 'interviewer' | 'candidate'
  content: string
}

export function InterviewSession({
  resume,
  onComplete,
}: {
  resume: ResumeBundle
  onComplete: (sessionId: string) => void
}) {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [plan, setPlan] = useState<InterviewPlan | null>(null)
  const [currentSection, setCurrentSection] = useState<string>('')
  const [messages, setMessages] = useState<Message[]>([])
  const [draft, setDraft] = useState('')
  const [loading, setLoading] = useState(false)

  async function begin() {
    setLoading(true)
    const res = await startInterview(resume)
    setSessionId(res.session_id)
    setPlan(res.plan)
    setCurrentSection(res.section)
    setMessages([{ role: 'interviewer', content: res.question }])
    setLoading(false)
  }

  async function sendAnswer() {
    if (!sessionId || !draft.trim()) return
    const answer = draft
    setDraft('')
    setMessages((m) => [...m, { role: 'candidate', content: answer }])
    setLoading(true)
    const next = await submitTurn(sessionId, answer)
    setCurrentSection(next.section)
    setMessages((m) => [...m, { role: 'interviewer', content: next.question }])
    setLoading(false)
  }

  async function finish() {
    if (!sessionId) return
    await endInterview(sessionId)
    onComplete(sessionId)
  }

  if (!sessionId) {
    return (
      <div>
        <h2>Ready for your mock interview</h2>
        <button onClick={begin} disabled={loading}>
          Begin
        </button>
      </div>
    )
  }

  return (
    <div>
      <h2>Mock interview</h2>
      {plan && (
        <p>
          <em>
            Section: {currentSection} (~{plan.total_estimated_turns} turns planned across{' '}
            {plan.sections.length} sections)
          </em>
        </p>
      )}
      <div>
        {messages.map((m, i) => (
          <p key={i}>
            <strong>{m.role === 'interviewer' ? 'Interviewer' : 'You'}:</strong> {m.content}
          </p>
        ))}
      </div>
      <textarea
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        placeholder="Type your answer…"
        disabled={loading}
        rows={4}
      />
      <div>
        <button onClick={sendAnswer} disabled={loading || !draft.trim()}>
          Submit answer
        </button>
        <button onClick={finish} disabled={loading}>
          End interview
        </button>
      </div>
    </div>
  )
}
