import { useState } from 'react'
import { analyzeResume } from '../api/client'
import type { ResumeBundle } from '../types'

export function ResumeUpload({ onAnalyzed }: { onAnalyzed: (r: ResumeBundle) => void }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)

  async function handleFile(file: File) {
    setLoading(true)
    setError(null)
    try {
      const resume = await analyzeResume(file)
      onAnalyzed(resume)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h2>Upload your resume</h2>
      <input
        type="file"
        accept=".pdf,.docx,.txt"
        onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
        disabled={loading}
      />
      {selectedFile && (
        <button 
          onClick={() => handleFile(selectedFile)} 
          disabled={loading}
          style={{ marginLeft: '1rem', padding: '0.25rem 0.5rem', cursor: 'pointer' }}
        >
          Start analysis
        </button>
      )}
      {loading && <p>Analyzing resume…</p>}
      {error && <p role="alert">{error}</p>}
    </div>
  )
}
