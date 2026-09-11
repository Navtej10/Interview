import React from 'react';
import styles from './ResumeAnalysis.module.css';

export function ReportHeader() {
  return (
    <div style={{ textAlign: 'center', marginBottom: '2.5rem' }}>
      <div style={{ fontSize: '0.8rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)' }}>
        InterviewAI
      </div>
      <h1 style={{ fontSize: '1.75rem', fontWeight: 700, margin: '0.5rem 0', color: 'var(--text-primary)' }}>
        Candidate analysis report
      </h1>
      <p style={{ color: 'var(--text-secondary)', fontStyle: 'italic', margin: 0 }}>
        Review this readiness report before starting your mock interview.
      </p>
    </div>
  );
}
