import React, { useState } from 'react'

const COMPANIES = [
  { id: 'Google', name: 'Google', philosophy: "Optimizes for General Cognitive Ability (GCA), role-related knowledge, and 'Googleyness'.", disclaimer: "Styled after publicly known Google interview patterns — not an official, affiliated, or verified simulation of Google's actual interview process." },
  { id: 'Amazon', name: 'Amazon', philosophy: "Strictly anchors all assessment to the 16 Leadership Principles with heavy focus on past data-driven impact.", disclaimer: "Styled after publicly known Amazon interview patterns — not an official, affiliated, or verified simulation of Amazon's actual interview process." },
  { id: 'Meta', name: 'Meta', philosophy: "Optimizes for raw coding speed, bug-free implementation, and scalable product sense.", disclaimer: "Styled after publicly known Meta interview patterns — not an official, affiliated, or verified simulation of Meta's actual interview process." },
  { id: 'Apple', name: 'Apple', philosophy: "Optimizes for deep domain expertise, passion for the product, and extreme attention to detail.", disclaimer: "Styled after publicly known Apple interview patterns — not an official, affiliated, or verified simulation of Apple's actual interview process." },
  { id: 'Microsoft', name: 'Microsoft', philosophy: "Optimizes for strong fundamentals, inclusive collaboration, and architectural pragmatism.", disclaimer: "Styled after publicly known Microsoft interview patterns — not an official, affiliated, or verified simulation of Microsoft's actual interview process." },
  { id: 'generic_faang', name: 'Generic FAANG', philosophy: "A balanced mix of standard big-tech interview practices: algorithmic rigor and structured behavioral.", disclaimer: "A composite style based on commonly reported big-tech interview patterns — not modeled on any single company." },
  { id: 'default', name: 'Default AI Interviewer', philosophy: "A balanced, human-centric interview style focused on discovering candidate strengths rather than rigid filtering.", disclaimer: "InterviewAI's standard interview style." },
]

const styles = {
  container: {
    maxWidth: '800px',
    margin: '0 auto',
    padding: '2rem',
    fontFamily: '"Georgia", "Times New Roman", serif',
    color: '#333',
    backgroundColor: '#fff',
  },
  pageTitle: {
    fontSize: '2rem',
    fontWeight: 'bold',
    marginBottom: '0.5rem',
    textAlign: 'center' as const,
  },
  pageSubtitle: {
    fontSize: '1.2rem',
    color: '#555',
    textAlign: 'center' as const,
    marginBottom: '2rem',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
    gap: '1rem',
    marginBottom: '2rem',
  },
  card: (isSelected: boolean) => ({
    padding: '1.5rem',
    border: isSelected ? '2px solid #0056b3' : '1px solid #ccc',
    borderRadius: '8px',
    cursor: 'pointer',
    backgroundColor: isSelected ? '#f0f7ff' : '#fff',
    transition: 'all 0.2s',
  }),
  cardTitle: {
    fontSize: '1.25rem',
    fontWeight: 'bold',
    marginBottom: '0.5rem',
  },
  cardDesc: {
    fontSize: '0.95rem',
    color: '#666',
    lineHeight: 1.4,
    marginBottom: '1rem',
  },
  disclaimer: {
    fontSize: '0.8rem',
    color: '#888',
    fontStyle: 'italic',
    lineHeight: 1.2,
    borderTop: '1px solid #eee',
    paddingTop: '0.5rem',
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
    cursor: 'pointer',
    textAlign: 'center' as const,
  }
}

export function CompanySelectionView({
  onSelect
}: {
  onSelect: (companyId: string) => void
}) {
  const [selectedId, setSelectedId] = useState<string>('default')

  return (
    <div style={styles.container}>
      <h1 style={styles.pageTitle}>Select Interview Style</h1>
      <p style={styles.pageSubtitle}>
        Choose a target company. The interviewer's tone, questions, pacing, and evaluation rubric will dynamically adapt to match their known interview philosophy.
      </p>

      <div style={styles.grid}>
        {COMPANIES.map(company => (
          <div 
            key={company.id} 
            style={styles.card(selectedId === company.id)}
            onClick={() => setSelectedId(company.id)}
          >
            <div style={styles.cardTitle}>{company.name}</div>
            <div style={styles.cardDesc}>{company.philosophy}</div>
            <div style={styles.disclaimer}>{company.disclaimer}</div>
          </div>
        ))}
      </div>

      <button style={styles.button} onClick={() => onSelect(selectedId)}>
        Start Interview as {COMPANIES.find(c => c.id === selectedId)?.name}
      </button>
    </div>
  )
}
