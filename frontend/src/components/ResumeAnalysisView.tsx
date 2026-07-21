import type { ResumeBundle } from '../types'

export function ResumeAnalysisView({
  resume,
  onContinue,
}: {
  resume: ResumeBundle
  onContinue: () => void
}) {
  const { parsed, analysis, graph } = resume
  const unsupported = graph.nodes
    .filter((n) => n.type === 'skill')
    .filter((n) => !graph.edges.some((e) => e.relation === 'demonstrates' && e.target === n.id))
    .map((n) => n.label)

  return (
    <div>
      <h2>Resume analysis</h2>
      <p>{analysis.summary}</p>

      <h3>Extracted</h3>
      <p>
        {parsed.projects.length} projects · {parsed.experience.length} experience entries ·{' '}
        {parsed.skills.length} skills listed
      </p>

      <h3>Strengths</h3>
      <ul>
        {analysis.strengths.map((s, i) => (
          <li key={i}>{s}</li>
        ))}
      </ul>

      <h3>Gaps to consider</h3>
      <ul>
        {analysis.gaps.map((g, i) => (
          <li key={i}>
            <strong>{g.location}</strong>: {g.issue} — <em>{g.suggestion}</em>
          </li>
        ))}
      </ul>

      {analysis.ats_issues.length > 0 && (
        <>
          <h3>ATS issues</h3>
          <ul>
            {analysis.ats_issues.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
        </>
      )}

      {unsupported.length > 0 && (
        <>
          <h3>Skills with no backing project/experience</h3>
          <ul>
            {unsupported.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </>
      )}

      <button onClick={onContinue}>Start mock interview</button>
    </div>
  )
}
