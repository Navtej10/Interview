import type { ResumeBundle, NextQuestionResponse, FeedbackReport, InterviewPlan } from '../types'

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export async function analyzeResume(file: File): Promise<ResumeBundle> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE_URL}/resume/analyze`, { method: 'POST', body: form })
  if (!res.ok) throw new Error('Resume analysis failed')
  return res.json()
}

export async function startInterview(
  resume: ResumeBundle
): Promise<{ session_id: string; question: string; topic: string; section: string; plan: InterviewPlan; rationale: string }> {
  const res = await fetch(`${BASE_URL}/interview/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ resume }),
  })
  if (!res.ok) throw new Error('Failed to start interview')
  return res.json()
}

export async function submitTurn(
  sessionId: string,
  candidateAnswer: string
): Promise<NextQuestionResponse> {
  const res = await fetch(`${BASE_URL}/interview/turn`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, candidate_answer: candidateAnswer }),
  })
  if (!res.ok) throw new Error('Failed to submit turn')
  return res.json()
}

export async function endInterview(sessionId: string): Promise<void> {
  await fetch(`${BASE_URL}/interview/end/${sessionId}`, { method: 'POST' })
}

export async function getWrittenReport(sessionId: string): Promise<FeedbackReport> {
  const res = await fetch(`${BASE_URL}/feedback/report/${sessionId}`)
  if (!res.ok) throw new Error('Failed to fetch report')
  return res.json()
}

export async function debriefTurn(sessionId: string, message: string): Promise<string> {
  const res = await fetch(`${BASE_URL}/feedback/debrief`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, candidate_message: message }),
  })
  if (!res.ok) throw new Error('Failed debrief turn')
  const data = await res.json()
  return data.reply
}
