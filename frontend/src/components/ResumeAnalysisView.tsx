import React from 'react'
import type { ResumeBundle } from '../types'

const styles = {
  container: {
    maxWidth: '800px',
    margin: '0 auto',
    padding: '2rem',
    fontFamily: '"Georgia", "Times New Roman", serif', // More document-like, or standard sans-serif
    color: '#333',
    backgroundColor: '#fff',
    lineHeight: '1.6',
    fontSize: '16px',
  },
  pageTitle: {
    fontSize: '2rem',
    fontWeight: 'bold',
    marginBottom: '0.5rem',
    textAlign: 'center' as const,
  },
  pageSubtitle: {
    fontSize: '1.5rem',
    color: '#555',
    textAlign: 'center' as const,
    marginBottom: '1rem',
  },
  headerText: {
    textAlign: 'center' as const,
    marginBottom: '2rem',
    fontStyle: 'italic',
    color: '#666',
  },
  sectionTitle: {
    fontSize: '1.5rem',
    borderBottom: '1px solid #ccc',
    paddingBottom: '0.5rem',
    marginTop: '2.5rem',
    marginBottom: '1rem',
    fontWeight: 'bold',
  },
  subsectionTitle: {
    fontSize: '1.25rem',
    marginTop: '1.5rem',
    marginBottom: '0.5rem',
    fontWeight: 'bold',
  },
  groupTitle: {
    fontSize: '1.1rem',
    marginTop: '1rem',
    marginBottom: '0.5rem',
    fontWeight: 'bold',
    textDecoration: 'underline',
  },
  paragraph: {
    marginBottom: '1rem',
  },
  list: {
    marginBottom: '1rem',
    paddingLeft: '2rem',
  },
  listItem: {
    marginBottom: '0.5rem',
  },
  bold: {
    fontWeight: 'bold',
  },
  button: {
    display: 'block',
    width: '100%',
    padding: '1rem',
    fontSize: '1.25rem',
    fontWeight: 'bold',
    color: '#fff',
    backgroundColor: '#0056b3',
    border: 'none',
    borderRadius: '4px',
    marginTop: '3rem',
    cursor: 'pointer',
    textAlign: 'center' as const,
  }
}

export function ResumeAnalysisView({
  resume,
  onContinue,
}: {
  resume: ResumeBundle
  onContinue: () => void
}) {
  const { analysis } = resume
  
  if (!analysis.candidate_profile) {
    return <div style={styles.container}>Loading analysis...</div>
  }

  const {
    candidate_profile,
    scores,
    summary,
    strengths,
    skill_matrix,
    project_reviews,
    resume_consistency,
    technical_risks,
    ats_analysis,
    growth_roadmap,
    predicted_questions,
    final_recommendation
  } = analysis

  // Group skills by confidence
  const skillsByConfidence = skill_matrix.reduce((acc, skill) => {
    acc[skill.confidence] = acc[skill.confidence] || []
    acc[skill.confidence].push(skill)
    return acc
  }, {} as Record<string, typeof skill_matrix>)

  // Group risks
  const risksByLevel = technical_risks.reduce((acc, risk) => {
    acc[risk.risk_level] = acc[risk.risk_level] || []
    acc[risk.risk_level].push(risk)
    return acc
  }, {} as Record<string, typeof technical_risks>)

  // Group questions by category
  const questionsByCategory = predicted_questions.reduce((acc, q) => {
    acc[q.category] = acc[q.category] || []
    acc[q.category].push(q)
    return acc
  }, {} as Record<string, typeof predicted_questions>)

  return (
    <div style={styles.container}>
      <h1 style={styles.pageTitle}>InterviewAI</h1>
      <h2 style={styles.pageSubtitle}>Candidate Analysis Report</h2>
      <p style={styles.headerText}>
        This report summarizes your resume, identifies strengths and improvement areas, and predicts what an interviewer is most likely to ask. Review it before starting your mock interview.
      </p>

      <h2 style={styles.sectionTitle}>Candidate Analysis</h2>
      <p style={styles.paragraph}>{summary}</p>

      <h2 style={styles.sectionTitle}>Candidate Profile</h2>
      <ul style={styles.list}>
        <li style={styles.listItem}><span style={styles.bold}>Career Stage:</span> {candidate_profile.career_stage}</li>
        <li style={styles.listItem}><span style={styles.bold}>Primary Domain:</span> {candidate_profile.primary_domain}</li>
        <li style={styles.listItem}><span style={styles.bold}>Secondary Domain:</span> {candidate_profile.secondary_domain}</li>
        <li style={styles.listItem}><span style={styles.bold}>Technical Maturity:</span> {candidate_profile.technical_maturity}</li>
        <li style={styles.listItem}><span style={styles.bold}>Interview Readiness:</span> {candidate_profile.interview_readiness}</li>
        <li style={styles.listItem}><span style={styles.bold}>Resume Quality:</span> {candidate_profile.resume_quality}</li>
        <li style={styles.listItem}><span style={styles.bold}>Overall Recommendation:</span> {candidate_profile.overall_recommendation}</li>
      </ul>

      <h2 style={styles.sectionTitle}>Resume Scores</h2>
      <ul style={styles.list}>
        <li style={styles.listItem}>
          <span style={styles.bold}>Overall Resume: {scores.overall_resume.score}/100</span><br/>
          {scores.overall_resume.reason}
        </li>
        <li style={styles.listItem}>
          <span style={styles.bold}>ATS Compatibility: {scores.ats_compatibility.score}/100</span><br/>
          {scores.ats_compatibility.reason}
        </li>
        <li style={styles.listItem}>
          <span style={styles.bold}>Technical Skills: {scores.technical_skills.score}/100</span><br/>
          {scores.technical_skills.reason}
        </li>
        <li style={styles.listItem}>
          <span style={styles.bold}>Project Quality: {scores.project_quality.score}/100</span><br/>
          {scores.project_quality.reason}
        </li>
        <li style={styles.listItem}>
          <span style={styles.bold}>Resume Writing: {scores.resume_writing.score}/100</span><br/>
          {scores.resume_writing.reason}
        </li>
        <li style={styles.listItem}>
          <span style={styles.bold}>Interview Readiness: {scores.interview_readiness.score}/100</span><br/>
          {scores.interview_readiness.reason}
        </li>
        <li style={styles.listItem}>
          <span style={styles.bold}>Confidence Score: {scores.confidence_score.score}/100</span><br/>
          {scores.confidence_score.reason}
        </li>
      </ul>

      <h2 style={styles.sectionTitle}>Key Strengths</h2>
      <ol style={styles.list}>
        {strengths.map((s, i) => (
          <li key={i} style={styles.listItem}>{s}</li>
        ))}
      </ol>

      <h2 style={styles.sectionTitle}>Skill Evidence Analysis</h2>
      {['High', 'Medium', 'Low', 'Unverified'].map((level) => {
        const skills = skillsByConfidence[level]
        if (!skills || skills.length === 0) return null
        return (
          <div key={level}>
            <h3 style={styles.groupTitle}>{level} Confidence</h3>
            <ul style={{ ...styles.list, listStyleType: 'none', paddingLeft: 0 }}>
              {skills.map((s, i) => (
                <li key={i} style={{ ...styles.listItem, marginBottom: '1rem' }}>
                  <span style={styles.bold}>• {s.skill}</span><br />
                  <span style={styles.bold}>Evidence:</span> {s.evidence}<br />
                  <span style={styles.bold}>Reason:</span> {s.reason}
                </li>
              ))}
            </ul>
          </div>
        )
      })}

      <h2 style={styles.sectionTitle}>Project Reviews</h2>
      {project_reviews.map((project, i) => (
        <div key={i}>
          <h3 style={styles.subsectionTitle}>{project.name}</h3>
          
          <h4 style={styles.bold}>Strengths</h4>
          <ul style={styles.list}>
            {project.strengths.map((s, j) => <li key={j}>{s}</li>)}
          </ul>

          <h4 style={styles.bold}>Weaknesses</h4>
          <ul style={styles.list}>
            {project.weaknesses.map((w, j) => <li key={j}>{w}</li>)}
          </ul>

          <h4 style={styles.bold}>Missing Information</h4>
          <ul style={styles.list}>
            {project.missing_information.map((m, j) => <li key={j}>{m}</li>)}
          </ul>

          <h4 style={styles.bold}>Suggested Improvements</h4>
          <ul style={styles.list}>
            {project.improvements.map((imp, j) => <li key={j}>{imp}</li>)}
          </ul>

          <h4 style={styles.bold}>Likely Interview Questions</h4>
          <ul style={styles.list}>
            {project.likely_interview_questions.map((q, j) => <li key={j}>{q}</li>)}
          </ul>
        </div>
      ))}

      <h2 style={styles.sectionTitle}>Resume Consistency</h2>
      <ul style={styles.list}>
        <li style={styles.listItem}><span style={styles.bold}>Summary alignment:</span> {resume_consistency.summary_aligns_with_projects ? 'Consistent' : 'Inconsistent'}</li>
        <li style={styles.listItem}><span style={styles.bold}>Skills vs Projects:</span> {resume_consistency.skills_align_with_projects ? 'Consistent' : 'Inconsistent'}</li>
        <li style={styles.listItem}><span style={styles.bold}>Technologies:</span> {resume_consistency.technologies_consistent ? 'Consistent' : 'Inconsistent'}</li>
        <li style={styles.listItem}><span style={styles.bold}>Dates:</span> {resume_consistency.dates_consistent ? 'Consistent' : 'Inconsistent'}</li>
        <li style={styles.listItem}><span style={styles.bold}>Formatting (No Duplicates):</span> {resume_consistency.no_duplicates ? 'Consistent' : 'Inconsistent'}</li>
      </ul>

      <h2 style={styles.sectionTitle}>ATS Analysis</h2>
      <ul style={styles.list}>
        <li style={styles.listItem}><span style={styles.bold}>ATS Score:</span> {ats_analysis.ats_score}/100</li>
        <li style={styles.listItem}><span style={styles.bold}>Formatting observations:</span> {ats_analysis.formatting}</li>
        <li style={styles.listItem}><span style={styles.bold}>Keyword coverage:</span> {ats_analysis.keyword_coverage}</li>
        <li style={styles.listItem}>
          <span style={styles.bold}>Missing keywords:</span> 
          <ul style={styles.list}>
            {ats_analysis.missing_keywords.map((kw, i) => <li key={i}>{kw}</li>)}
          </ul>
        </li>
        <li style={styles.listItem}>
          <span style={styles.bold}>Suggestions:</span>
          <ul style={styles.list}>
            {ats_analysis.recommendations.map((r, i) => <li key={i}>{r}</li>)}
          </ul>
        </li>
      </ul>

      <h2 style={styles.sectionTitle}>Technical Interview Risks</h2>
      {['High', 'Medium', 'Low'].map((level) => {
        const risks = risksByLevel[level]
        if (!risks || risks.length === 0) return null
        return (
          <div key={level}>
            <h3 style={styles.groupTitle}>{level} Risk</h3>
            <ul style={styles.list}>
              {risks.map((r, i) => (
                <li key={i} style={styles.listItem}>
                  <span style={styles.bold}>{r.technology}</span> - {r.reason}
                </li>
              ))}
            </ul>
          </div>
        )
      })}

      <h2 style={styles.sectionTitle}>Interview Preparation</h2>
      {Object.entries(questionsByCategory).map(([category, questions]) => (
        <div key={category}>
          <h3 style={styles.subsectionTitle}>{category}</h3>
          <ul style={styles.list}>
            {questions.map((q, i) => (
              <li key={i} style={{ ...styles.listItem, marginBottom: '1rem' }}>
                <span style={styles.bold}>Q: {q.question}</span><br />
                <span style={{ fontStyle: 'italic' }}>Triggered by: {q.triggered_by} | Difficulty: {q.difficulty}</span><br />
                <span style={styles.bold}>Why:</span> {q.reason}
              </li>
            ))}
          </ul>
        </div>
      ))}

      <h2 style={styles.sectionTitle}>Growth Roadmap</h2>
      {['High', 'Medium', 'Low'].map((priority) => {
        const roadmaps = 
          priority === 'High' ? growth_roadmap.high_priority :
          priority === 'Medium' ? growth_roadmap.medium_priority :
          growth_roadmap.low_priority

        if (!roadmaps || roadmaps.length === 0) return null
        return (
          <div key={priority}>
            <h3 style={styles.groupTitle}>{priority} Priority</h3>
            <ul style={styles.list}>
              {roadmaps.map((r, i) => (
                <li key={i} style={{ ...styles.listItem, marginBottom: '1rem' }}>
                  <span style={styles.bold}>{r.recommendation}</span><br />
                  <span style={styles.bold}>Why:</span> {r.reason}<br />
                  <span style={styles.bold}>Expected improvement:</span> {r.expected_impact}
                </li>
              ))}
            </ul>
          </div>
        )
      })}

      <h2 style={styles.sectionTitle}>Final Recommendation</h2>
      <p style={styles.paragraph}>{final_recommendation || 'No final recommendation generated.'}</p>

      <button style={styles.button} onClick={onContinue}>
        Start Mock Interview
      </button>
    </div>
  )
}
