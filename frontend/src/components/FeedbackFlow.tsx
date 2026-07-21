import { useState } from 'react'
import { getWrittenReport, debriefTurn } from '../api/client'
import type { FeedbackReport } from '../types'

export function FeedbackFlow({ sessionId }: { sessionId: string }) {
  const [mode, setMode] = useState<'choice' | 'report' | 'debrief'>('choice')
  const [report, setReport] = useState<FeedbackReport | null>(null)
  const [debriefLog, setDebriefLog] = useState<{ role: string; content: string }[]>([])
  const [draft, setDraft] = useState('')

  async function chooseReport() {
    setMode('report')
    const r = await getWrittenReport(sessionId)
    setReport(r)
  }

  function chooseDebrief() {
    setMode('debrief')
    setDebriefLog([
      { role: 'interviewer', content: "Let's talk through how it went. What did you think?" },
    ])
  }

  async function sendDebriefMessage() {
    if (!draft.trim()) return
    const msg = draft
    setDraft('')
    setDebriefLog((l) => [...l, { role: 'candidate', content: msg }])
    const reply = await debriefTurn(sessionId, msg)
    setDebriefLog((l) => [...l, { role: 'interviewer', content: reply }])
  }

  if (mode === 'choice') {
    return (
      <div>
        <h2>How would you like your feedback?</h2>
        <button onClick={chooseDebrief}>Live debrief conversation</button>
        <button onClick={chooseReport}>Written report</button>
      </div>
    )
  }

  if (mode === 'report') {
    if (!report) return <p>Generating report…</p>
    return (
      <div>
        <h2>Feedback report</h2>
        <p>{report.overall_summary}</p>
        <h3>Strengths</h3>
        <ul>{report.strengths.map((s, i) => <li key={i}>{s}</li>)}</ul>
        <h3>Weaknesses</h3>
        <ul>{report.weaknesses.map((s, i) => <li key={i}>{s}</li>)}</ul>
        <h3>Specific moments</h3>
        <ul>{report.moment_highlights.map((s, i) => <li key={i}>{s}</li>)}</ul>
        <h3>Next steps</h3>
        <ul>{report.recommended_next_steps.map((s, i) => <li key={i}>{s}</li>)}</ul>
      </div>
    )
  }

  return (
    <div>
      <h2>Debrief</h2>
      {debriefLog.map((m, i) => (
        <p key={i}>
          <strong>{m.role === 'interviewer' ? 'Interviewer' : 'You'}:</strong> {m.content}
        </p>
      ))}
      <textarea value={draft} onChange={(e) => setDraft(e.target.value)} rows={3} />
      <button onClick={sendDebriefMessage}>Send</button>
    </div>
  )
}
