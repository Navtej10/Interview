import { useState, useRef, useEffect } from 'react'
import { startInterview, submitTurn, endInterview } from '../api/client'
import type { ResumeBundle, InterviewPlan } from '../types'
import * as vad from '@ricky0123/vad-web'
import { encodeWAV } from '../utils/wav'

interface Message {
  role: 'interviewer' | 'candidate'
  content: string
}

type UIState = 'listening' | 'processing' | 'ai_speaking' | 'idle'

export function InterviewSession({
  resume,
  companyId,
  onComplete,
}: {
  resume: ResumeBundle
  companyId?: string
  onComplete: (sessionId: string) => void
}) {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [plan, setPlan] = useState<InterviewPlan | null>(null)
  const [currentSection, setCurrentSection] = useState<string>('')
  const [messages, setMessages] = useState<Message[]>([])
  const [draft, setDraft] = useState('')
  const [loading, setLoading] = useState(false)

  // Voice mode state
  const [mode, setMode] = useState<'text' | 'voice' | null>(null)
  const [uiState, setUiState] = useState<UIState>('idle')
  const uiStateRef = useRef<UIState>('idle')
  
  useEffect(() => {
    uiStateRef.current = uiState
  }, [uiState])

  // Refs for voice mode
  const wsRef = useRef<WebSocket | null>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  const vadRef = useRef<vad.MicVAD | null>(null)
  const mediaStreamRef = useRef<MediaStream | null>(null)
  const lastInterruptTimeRef = useRef<number>(0)
  
  // Video accumulation
  const videoChunksRef = useRef<Uint8Array[]>([])
  const videoReceiveTimeoutRef = useRef<number | null>(null)
  const currentBlobUrlRef = useRef<string | null>(null)
  
  // Pending text for delayed display
  const pendingInterviewerMessageRef = useRef<string | null>(null)

  // Cleanup WebSocket and Streams
  useEffect(() => {
    return () => {
      cleanupMedia()
      if (wsRef.current) wsRef.current.close()
    }
  }, [])

  function cleanupMedia() {
    if (vadRef.current) {
      vadRef.current.destroy()
      vadRef.current = null
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(t => t.stop())
      mediaStreamRef.current = null
    }
    if (currentBlobUrlRef.current) {
      URL.revokeObjectURL(currentBlobUrlRef.current)
      currentBlobUrlRef.current = null
    }
    if (videoReceiveTimeoutRef.current) {
      window.clearTimeout(videoReceiveTimeoutRef.current)
    }
  }

  // Connect WebSocket after the DOM has updated and the video element exists
  useEffect(() => {
    if (sessionId && mode === 'voice' && !wsRef.current) {
      setupVoiceMode(sessionId)
    }
  }, [sessionId, mode])

  async function begin(selectedMode: 'text' | 'voice') {
    setMode(selectedMode)
    setLoading(true)
    try {
      const res = await startInterview(resume, companyId)
      setSessionId(res.session_id)
      setPlan(res.plan)
      setCurrentSection(res.section)
      setMessages([{ role: 'interviewer', content: res.question }])
      
      if (selectedMode === 'voice') {
        setUiState('processing') // Waiting for the first avatar video to arrive
        await startContinuousRecording()
      }
    } catch (e) {
      console.error(e)
      alert("Failed to start interview.")
    }
    setLoading(false)
  }

  async function startContinuousRecording() {
    try {
      const myvad = await vad.MicVAD.new({
        onSpeechStart: () => {
          const now = Date.now()
          if (uiStateRef.current === 'ai_speaking') {
             // Guard against rapid-fire interrupts (1-second cooldown)
             if (now - lastInterruptTimeRef.current < 1000) return;
             lastInterruptTimeRef.current = now;
             
             if (videoRef.current) {
                videoRef.current.pause()
             }
             if (wsRef.current?.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify({ type: 'interrupt' }))
             }
             setUiState('listening') // Immediately transition
          } else {
             if (videoRef.current) {
                videoRef.current.pause()
             }
             if (wsRef.current?.readyState === WebSocket.OPEN) {
               wsRef.current.send(JSON.stringify({ type: 'SPEECH_START' }))
             }
             // The backend will now tell us when state changes, but we can optimistically set it
             setUiState('listening')
          }
        },
        onSpeechEnd: (audio) => {
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            const wavBlob = encodeWAV(audio)
            wsRef.current.send(wavBlob)
            wsRef.current.send(JSON.stringify({ type: 'END_OF_TURN' }))
          }
          setUiState('processing')
        },
        onVADMisfire: () => {
          setUiState('listening')
        }
      })
      myvad.start()
      vadRef.current = myvad
      setUiState('listening') // Once VAD is started, we are listening
    } catch (e) {
      console.error('Microphone access denied or error:', e)
      alert("Microphone access is required for Voice Mode.")
    }
  }

  function setupVoiceMode(id: string) {
    const wsUrl = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000').replace('http', 'ws')
    const ws = new WebSocket(`${wsUrl}/interview/voice_turn/${id}`)
    wsRef.current = ws

    ws.binaryType = 'arraybuffer'

    ws.onmessage = (event) => {
      if (typeof event.data === 'string') {
        if (event.data === 'Interview complete.') {
          finish()
        } else if (event.data.startsWith('Error') || event.data.startsWith('Avatar error')) {
          console.error('Backend error:', event.data)
          setUiState('listening')
        } else {
          try {
            const payload = JSON.parse(event.data)
            if (payload.type === 'transcript') {
              setMessages(m => [
                ...m,
                { role: 'candidate', content: payload.candidate }
              ])
              pendingInterviewerMessageRef.current = payload.interviewer
            } else if (payload.type === 'state') {
              setUiState(payload.value)
            }
          } catch (e) {
            console.log('WS Message:', event.data)
          }
        }
      } else {
        const chunk = new Uint8Array(event.data)
        videoChunksRef.current.push(chunk)
        
        if (videoReceiveTimeoutRef.current) {
          window.clearTimeout(videoReceiveTimeoutRef.current)
        }
        
        videoReceiveTimeoutRef.current = window.setTimeout(() => {
          finalizeVideo()
        }, 200)
      }
    }
    
    ws.onclose = () => {
      console.log('WS closed')
      setUiState('idle')
    }
    ws.onerror = (e) => {
      console.error('WS error', e)
      setUiState('idle')
    }
  }

  function finalizeVideo() {
    if (videoChunksRef.current.length === 0) return
    
    if (currentBlobUrlRef.current) {
      URL.revokeObjectURL(currentBlobUrlRef.current)
    }
    
    const blob = new Blob(videoChunksRef.current as BlobPart[], { type: 'video/mp4' })
    videoChunksRef.current = [] 
    
    const url = URL.createObjectURL(blob)
    currentBlobUrlRef.current = url
    
    if (videoRef.current) {
       videoRef.current.src = url
       videoRef.current.play().catch(e => console.error("Playback failed:", e))
       setUiState('ai_speaking')
       
       const textToAppend = pendingInterviewerMessageRef.current;
       if (textToAppend) {
         setMessages(m => [
           ...m,
           { role: 'interviewer', content: textToAppend }
         ])
         pendingInterviewerMessageRef.current = null
       }
       
       videoRef.current.onended = () => {
         setUiState('listening')
       }
    }
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
    cleanupMedia()
    onComplete(sessionId)
  }

  if (!sessionId) {
    return (
      <div>
        <h2>Ready for your mock interview</h2>
        <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
          <button onClick={() => begin('text')} disabled={loading}>
            Begin Text Interview
          </button>
          <button onClick={() => begin('voice')} disabled={loading} style={{ background: '#4CAF50', color: 'white' }}>
            Begin Voice/Avatar Interview
          </button>
        </div>
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
      <div style={{ display: 'flex', gap: '2rem' }}>
        <div style={{ flex: 1 }}>
          <div style={{ maxHeight: '400px', overflowY: 'auto', border: '1px solid #ccc', padding: '1rem', marginBottom: '1rem' }}>
            {messages.map((m, i) => (
              <p key={i}>
                <strong>{m.role === 'interviewer' ? 'Interviewer' : 'You'}:</strong> {m.content}
              </p>
            ))}
          </div>
          
          {mode === 'text' ? (
            <>
              <textarea
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                placeholder="Type your answer…"
                disabled={loading}
                rows={4}
                style={{ width: '100%', marginBottom: '1rem' }}
              />
              <div style={{ display: 'flex', gap: '1rem' }}>
                <button onClick={sendAnswer} disabled={loading || !draft.trim()}>
                  Submit answer
                </button>
                <button onClick={finish} disabled={loading}>
                  End interview
                </button>
              </div>
            </>
          ) : (
            <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
              <span>
                {uiState === 'listening' && 'Listening...'}
                {uiState === 'processing' && 'Processing...'}
                {uiState === 'ai_speaking' && 'Interviewer speaking...'}
                {uiState === 'idle' && 'Idle...'}
              </span>
              <button onClick={finish} style={{ marginLeft: 'auto' }}>
                End interview
              </button>
            </div>
          )}
        </div>

        {mode === 'voice' && (
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-start' }}>
            <div style={{ width: '100%', aspectRatio: '16/9', background: '#000', borderRadius: '8px', overflow: 'hidden' }}>
              <video 
                ref={videoRef}
                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                autoPlay 
                playsInline
              />
            </div>
            <p style={{ color: '#666', marginTop: '0.5rem', textTransform: 'capitalize' }}>
              State: {uiState}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

