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
        {report.company_style && (
          <div style={{ marginBottom: '1.5rem', padding: '1rem', backgroundColor: '#f8f9fa', borderLeft: '4px solid #0056b3' }}>
            <strong>Interview Style:</strong> {report.company_style}
            {report.company_disclaimer && (
              <p style={{ fontSize: '0.85rem', color: '#666', marginTop: '0.5rem', fontStyle: 'italic' }}>
                {report.company_disclaimer}
              </p>
            )}
          </div>
        )}
        
        {report.early_termination_context && report.early_termination_context.termination_reason !== 'normal_completion' && (
          <div style={{ marginBottom: '1.5rem', padding: '1rem', backgroundColor: '#fff3cd', borderLeft: '4px solid #ffc107' }}>
            <strong>Note:</strong> Interview ended early ({report.early_termination_context.termination_reason}).
          </div>
        )}

        <p>{report.overall_performance?.summary}</p>
        
        <h3>Strongest Areas</h3>
        <ul>{report.overall_performance?.strongest_areas?.map((s, i) => <li key={i}>{s}</li>)}</ul>
        
        <h3>Weakest Areas</h3>
        <ul>{report.overall_performance?.weakest_areas?.map((s, i) => <li key={i}>{s}</li>)}</ul>

        <h3>Technical Weaknesses</h3>
        <ul>{report.technical_weaknesses?.map((w, i) => (
          <li key={i}><strong>{w.description}:</strong> {w.evidence}</li>
        ))}</ul>

        <h3>Communication Weaknesses</h3>
        <ul>{report.communication_weaknesses?.map((w, i) => (
          <li key={i}><strong>{w.description}:</strong> {w.evidence}</li>
        ))}</ul>

        <h3>Scores (Weighted Overall: {(report.weighted_overall * 100).toFixed(0)}%)</h3>
        <ul>
          {report.scores?.map((score, i) => (
            <li key={i}>
              <strong>{score.criterion_name}:</strong> {(score.score * 10).toFixed(1)}/10
              <p style={{ margin: '0.2rem 0 0.5rem 0', fontSize: '0.9rem', color: '#555' }}>{score.justification}</p>
            </li>
          ))}
        </ul>
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
