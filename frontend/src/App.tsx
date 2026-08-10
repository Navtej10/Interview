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

  const goHome = () => {
    if (confirm('Are you sure you want to go home? Current progress will be lost.')) {
      setStage('upload')
      setResume(null)
      setSessionId(null)
    }
  }

  return (
    <main style={{ maxWidth: 720, margin: '2rem auto', fontFamily: 'sans-serif' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h1 style={{ margin: 0 }}>InterviewAI</h1>
        {stage !== 'upload' && (
          <button onClick={goHome} style={{ padding: '0.5rem 1rem', cursor: 'pointer' }}>
            🏠 Home
          </button>
        )}
      </header>

      {stage === 'upload' && (
        <ResumeUpload
          onAnalyzed={(r) => {
            setResume(r)
            setStage('analysis')
          }}
        />
      )}

      {stage === 'analysis' && resume && (
        <div>
          <button onClick={() => setStage('upload')} style={{ marginBottom: '1rem', padding: '0.5rem 1rem', cursor: 'pointer' }}>
            ← Back to Upload
          </button>
          <ResumeAnalysisView resume={resume} onContinue={() => setStage('interview')} />
        </div>
      )}

      {stage === 'interview' && resume && (
        <div>
          <button onClick={() => setStage('analysis')} style={{ marginBottom: '1rem', padding: '0.5rem 1rem', cursor: 'pointer' }}>
            ← Back to Analysis
          </button>
          <InterviewSession
            resume={resume}
            onComplete={(id) => {
              setSessionId(id)
              setStage('feedback')
            }}
          />
        </div>
      )}

      {stage === 'feedback' && sessionId && (
        <div>
          <button onClick={() => setStage('interview')} style={{ marginBottom: '1rem', padding: '0.5rem 1rem', cursor: 'pointer' }}>
            ← Back to Interview
          </button>
          <FeedbackFlow sessionId={sessionId} />
        </div>
      )}
    </main>
  )
}
