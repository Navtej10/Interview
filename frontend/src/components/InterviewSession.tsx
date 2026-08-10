import { useState, useRef, useEffect } from 'react'
import { startInterview, submitTurn, endInterview } from '../api/client'
import type { ResumeBundle, InterviewPlan } from '../types'

interface Message {
  role: 'interviewer' | 'candidate'
  content: string
}

type UIState = 'idle' | 'listening' | 'thinking' | 'speaking'

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

  // Voice mode state
  const [mode, setMode] = useState<'text' | 'voice' | null>(null)
  const [uiState, setUiState] = useState<UIState>('idle')
  
  // Refs for voice mode
  const wsRef = useRef<WebSocket | null>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  
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
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop()
      mediaRecorderRef.current.stream.getTracks().forEach(t => t.stop())
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
      const res = await startInterview(resume)
      setSessionId(res.session_id)
      setPlan(res.plan)
      setCurrentSection(res.section)
      setMessages([{ role: 'interviewer', content: res.question }])
      
      if (selectedMode === 'voice') {
        setUiState('thinking') // Waiting for the first avatar video to arrive
      }
    } catch (e) {
      console.error(e)
      alert("Failed to start interview.")
    }
    setLoading(false)
  }

  function setupVoiceMode(id: string) {
    const wsUrl = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000').replace('http', 'ws')
    const ws = new WebSocket(`${wsUrl}/interview/voice_turn/${id}`)
    wsRef.current = ws

    ws.binaryType = 'arraybuffer'

    ws.onmessage = (event) => {
      if (typeof event.data === 'string') {
        // Backend text messages (errors or status)
        if (event.data === 'Interview complete.') {
          finish()
        } else if (event.data.startsWith('Error') || event.data.startsWith('Avatar error')) {
          console.error('Backend error:', event.data)
          setUiState('idle')
        } else {
          try {
            const payload = JSON.parse(event.data)
            if (payload.type === 'transcript') {
              setMessages(m => [
                ...m,
                { role: 'candidate', content: payload.candidate }
              ])
              pendingInterviewerMessageRef.current = payload.interviewer
            }
          } catch (e) {
            console.log('WS Message:', event.data)
          }
        }
      } else {
        // We received a binary chunk of the video.
        // Because the backend reads the file and streams it rapidly in a tight loop,
        // we accumulate the chunks and use a short timeout to detect the end.
        const chunk = new Uint8Array(event.data)
        videoChunksRef.current.push(chunk)
        
        if (videoReceiveTimeoutRef.current) {
          window.clearTimeout(videoReceiveTimeoutRef.current)
        }
        
        videoReceiveTimeoutRef.current = window.setTimeout(() => {
          finalizeVideo()
        }, 200) // 200ms without chunks means the file is fully transferred
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
    
    // Revoke old URL if exists to avoid memory leaks
    if (currentBlobUrlRef.current) {
      URL.revokeObjectURL(currentBlobUrlRef.current)
    }
    
    // Treat every interviewer response as one complete video
    const blob = new Blob(videoChunksRef.current, { type: 'video/mp4' })
    videoChunksRef.current = [] // reset queue
    
    const url = URL.createObjectURL(blob)
    currentBlobUrlRef.current = url
    
    if (videoRef.current) {
       videoRef.current.src = url
       videoRef.current.play().catch(e => console.error("Playback failed:", e))
       setUiState('speaking')
       
       // Append the delayed interviewer message exactly when the video starts
       const textToAppend = pendingInterviewerMessageRef.current;
       if (textToAppend) {
         setMessages(m => [
           ...m,
           { role: 'interviewer', content: textToAppend }
         ])
         pendingInterviewerMessageRef.current = null
       }
       
       // When video finishes playing, go back to idle so the user can speak
       videoRef.current.onended = () => {
         setUiState('idle')
       }
    }
  }

  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        }
      })
      const mr = new MediaRecorder(stream)
      mediaRecorderRef.current = mr
      
      mr.ondataavailable = (e) => {
        if (e.data.size > 0 && wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current?.send(e.data)
        }
      }
      
      // Stop any playing avatar video if we interrupt
      if (videoRef.current) {
         videoRef.current.pause()
      }
      
      // Capture chunks every 250ms for the backend to accumulate
      mr.start(250)
      setUiState('listening')
    } catch (e) {
      console.error('Microphone access denied or error:', e)
      alert("Microphone access is required for Voice Mode.")
    }
  }

  function stopRecording() {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.onstop = () => {
        // Send END_OF_TURN control message so the backend stops waiting for audio
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({ type: 'END_OF_TURN' }))
        }
      }
      mediaRecorderRef.current.stop()
      mediaRecorderRef.current.stream.getTracks().forEach(t => t.stop())
    } else {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'END_OF_TURN' }))
      }
    }
    
    setUiState('thinking') // Waiting for backend to transcribe and generate next avatar video
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
        {/* Left Column: Chat History */}
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
              <button 
                onClick={uiState === 'listening' ? stopRecording : startRecording}
                disabled={uiState === 'thinking'}
                style={{ 
                  background: uiState === 'listening' ? '#f44336' : (uiState === 'thinking' ? '#9e9e9e' : '#4CAF50'),
                  color: 'white',
                  padding: '1rem',
                  borderRadius: '50%',
                  cursor: uiState === 'thinking' ? 'not-allowed' : 'pointer'
                }}
              >
                {uiState === 'listening' ? '⏹ Stop' : '🎤 Speak'}
              </button>
              <span>
                {uiState === 'listening' && 'Listening...'}
                {uiState === 'thinking' && 'Thinking...'}
                {uiState === 'speaking' && 'Avatar speaking...'}
                {uiState === 'idle' && 'Click to talk'}
              </span>
              <button onClick={finish} style={{ marginLeft: 'auto' }}>
                End interview
              </button>
            </div>
          )}
        </div>

        {/* Right Column: Avatar Video (Only visible in Voice mode) */}
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
