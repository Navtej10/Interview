import { useState, useRef, useEffect } from 'react'
import { startInterview, submitTurn, endInterview } from '../api/client'
import type { ResumeBundle, InterviewPlan } from '../types'
import * as vad from '@ricky0123/vad-web'
import { encodeWAV } from '../utils/wav'
import styles from './InterviewSession.module.css'
import { Home } from 'lucide-react'

interface Message {
  role: 'interviewer' | 'candidate'
  content: string
}

type UIState = 'listening' | 'processing' | 'ai_speaking' | 'idle' | 'ended' | 'completed'

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
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const [showTranscript, setShowTranscript] = useState(false)

  // Voice mode state
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
    if (sessionId && !wsRef.current && uiState !== 'ended') {
      setupVoiceMode(sessionId)
    }
  }, [sessionId, uiState])

  async function begin() {
    setLoading(true)
    try {
      const res = await startInterview(resume, companyId)
      setSessionId(res.session_id)
      setPlan(res.plan)
      setMessages([{ role: 'interviewer', content: res.question }])
      
      let stream: MediaStream;
      try {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
          throw new Error("getUserMedia is not supported in this browser.")
        }
        stream = await navigator.mediaDevices.getUserMedia({ audio: true })
        mediaStreamRef.current = stream
      } catch (e) {
        console.error('Microphone access denied or error:', e)
        alert("Microphone access was denied or is unavailable. Please allow microphone permissions to use Voice Mode.")
        setLoading(false)
        return
      }

      setUiState('processing') // Waiting for the first avatar video to arrive
      await startContinuousRecording(stream)
    } catch (e) {
      console.error(e)
      alert("Failed to start interview.")
    }
    setLoading(false)
  }

  async function startContinuousRecording(stream: MediaStream) {
    try {
      const myvad = await vad.MicVAD.new({
        // @ts-expect-error - 'stream' is used by MicVAD but missing in the type definitions
        stream,
        baseAssetPath: '/',
        onnxWASMBasePath: '/',
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
          try {
            if (wsRef.current?.readyState === WebSocket.OPEN) {
              const wavBlob = encodeWAV(audio)
              wsRef.current.send(wavBlob)
              wsRef.current.send(JSON.stringify({ type: 'END_OF_TURN' }))
            }
          } catch (error) {
            console.error('Error in onSpeechEnd processing:', error)
          } finally {
            setUiState('processing')
          }
        },
        onVADMisfire: () => {
          setUiState('listening')
        }
      })
      myvad.start()
      vadRef.current = myvad
      setUiState('listening') // Once VAD is started, we are listening
    } catch (e) {
      console.error('Voice mode failed to initialize:', e)
      alert("Voice mode failed to initialize. Please check your connection or try again.")
    }
  }

  function setupVoiceMode(id: string) {
    const wsUrl = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000').replace('http', 'ws')
    const ws = new WebSocket(`${wsUrl}/interview/voice_turn/${id}`)
    wsRef.current = ws

    ws.binaryType = 'arraybuffer'

    ws.onmessage = (event) => {
      if (typeof event.data === 'string') {
        if (event.data.startsWith('Error') || event.data.startsWith('Avatar error')) {
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
              if (payload.value === 'completed') {
                finish()
              } else {
                setUiState(payload.value)
              }
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
      if (uiStateRef.current !== 'ended') {
        setUiState('idle')
      }
    }
    ws.onerror = (e) => {
      console.error('WS error', e)
      if (uiStateRef.current !== 'ended') {
        setUiState('idle')
      }
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

  async function finish() {
    if (!sessionId) return
    setUiState('ended')
    cleanupMedia()
    await endInterview(sessionId)
  }

  function handleGoHome() {
    if (uiState === 'ended' && sessionId) {
      onComplete(sessionId)
    } else {
      // If we're midway through an interview, going home without saving could lose progress.
      // Assuming for this prototype we just navigate away or finish the session.
      if (sessionId) {
        finish().then(() => onComplete(sessionId))
      }
    }
  }

  const getStateColor = (state: UIState) => {
    switch (state) {
      case 'listening': return 'var(--state-listening)'
      case 'ai_speaking': return 'var(--state-speaking)'
      case 'processing': return 'var(--state-thinking)'
      default: return 'var(--state-idle)'
    }
  }

  const getStateLabel = (state: UIState) => {
    switch (state) {
      case 'listening': return 'Listening'
      case 'ai_speaking': return 'Speaking'
      case 'processing': return 'Thinking'
      case 'ended': return 'Ended'
      default: return 'Idle'
    }
  }

  const currentCaption = messages.length > 0 ? messages[messages.length - 1].content : ''

  if (!sessionId) {
    return (
      <div className={styles.container} style={{ justifyContent: 'center', alignItems: 'center' }}>
        <h2 style={{ marginBottom: '1.5rem', fontSize: '1.5rem', fontWeight: 600 }}>Ready for your mock interview</h2>
        <button className={styles.buttonPrimary} onClick={begin} disabled={loading}>
          {loading ? 'Connecting...' : 'Join Interview Session'}
        </button>
      </div>
    )
  }

  return (
    <div className={styles.container}>
      <header className={styles.topBar}>
        <div className={styles.wordmark}>MockInterview</div>
        <button className={styles.iconButton} onClick={handleGoHome} aria-label="Go home">
          <Home size={20} />
        </button>
      </header>

      {uiState === 'ended' ? (
        <div className={styles.endScreen}>
          <div className={styles.endMessage}>Interview complete</div>
          <button className={styles.buttonPrimary} onClick={() => onComplete(sessionId)}>
            View Results
          </button>
        </div>
      ) : (
        <>
          <div className={styles.avatarContainer}>
            <video 
              ref={videoRef}
              className={styles.videoElement}
              autoPlay 
              playsInline
            />
            <div className={`${styles.overlay} ${styles.nameplate}`}>
              Alex Chen · Senior engineering manager
            </div>
            <div className={`${styles.overlay} ${styles.stateOverlay}`}>
              <div 
                className={`${styles.stateDot} ${(uiState === 'listening' || uiState === 'ai_speaking' || uiState === 'processing') ? styles.pulse : ''}`}
                style={{ '--state-color': getStateColor(uiState) } as React.CSSProperties}
              />
              {getStateLabel(uiState)}
            </div>
          </div>

          <div className={styles.captionLine}>
            {uiState === 'processing' ? '…' : currentCaption}
          </div>

          <div className={styles.controlRow}>
            <div className={styles.controlState}>
              <div 
                className={`${styles.stateDot} ${(uiState === 'listening' || uiState === 'ai_speaking' || uiState === 'processing') ? styles.pulse : ''}`}
                style={{ '--state-color': getStateColor(uiState) } as React.CSSProperties}
              />
              {getStateLabel(uiState)}
            </div>
            
            <button className={styles.buttonOutline} onClick={finish}>
              End interview
            </button>
          </div>

          <button className={styles.transcriptToggle} onClick={() => setShowTranscript(!showTranscript)}>
            {showTranscript ? 'Hide transcript' : 'Show transcript'}
          </button>

          {showTranscript && (
            <div className={styles.transcriptPanel}>
              {messages.map((m, i) => (
                <div 
                  key={i} 
                  className={`${styles.message} ${m.role === 'interviewer' ? styles.interviewerMessage : styles.candidateMessage}`}
                >
                  {m.content}
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}

