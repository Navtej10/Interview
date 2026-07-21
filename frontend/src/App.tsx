import { useState } from 'react'
import { ResumeUpload } from './components/ResumeUpload'
import { ResumeAnalysisView } from './components/ResumeAnalysisView'
import { InterviewSession } from './components/InterviewSession'
import { FeedbackFlow } from './components/FeedbackFlow'
import type { ResumeBundle } from './types'

type Stage = 'upload' | 'analysis' | 'interview' | 'feedback'

export default function App() {
  const [stage, setStage] = useState<Stage>('upload')
  const [resume, setResume] = useState<ResumeBundle | null>(null)
  const [sessionId, setSessionId] = useState<string | null>(null)

  return (
    <main style={{ maxWidth: 720, margin: '2rem auto', fontFamily: 'sans-serif' }}>
      <h1>InterviewAI</h1>

      {stage === 'upload' && (
        <ResumeUpload
          onAnalyzed={(r) => {
            setResume(r)
            setStage('analysis')
          }}
        />
      )}

      {stage === 'analysis' && resume && (
        <ResumeAnalysisView resume={resume} onContinue={() => setStage('interview')} />
      )}

      {stage === 'interview' && resume && (
        <InterviewSession
          resume={resume}
          onComplete={(id) => {
            setSessionId(id)
            setStage('feedback')
          }}
        />
      )}

      {stage === 'feedback' && sessionId && <FeedbackFlow sessionId={sessionId} />}
    </main>
  )
}
