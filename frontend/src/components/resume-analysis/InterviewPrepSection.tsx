import React from 'react';
import styles from './ResumeAnalysis.module.css';
import type { PredictedQuestion } from '../../types';

interface InterviewPrepSectionProps {
  questions: PredictedQuestion[];
}

function getDifficultyBadgeColor(difficulty: string) {
  switch (difficulty.toLowerCase()) {
    case 'hard': return { bg: 'var(--score-weak-bg)', fg: 'var(--score-weak)' };
    case 'medium': return { bg: 'var(--score-moderate-bg)', fg: 'var(--score-moderate)' };
    case 'easy': return { bg: 'var(--score-strong-bg)', fg: 'var(--score-strong)' };
    default: return { bg: 'var(--surface-muted)', fg: 'var(--text-secondary)' };
  }
}

export function InterviewPrepSection({ questions }: InterviewPrepSectionProps) {
  const grouped = questions.reduce((acc, q) => {
    if (!acc[q.category]) acc[q.category] = [];
    acc[q.category].push(q);
    return acc;
  }, {} as Record<string, PredictedQuestion[]>);

  if (questions.length === 0) {
    return (
      <div className={styles.section}>
        <h2 className={styles.sectionTitle}>Interview Preparation</h2>
        <div className={styles.emptyState}>No predicted questions available.</div>
      </div>
    );
  }

  return (
    <div className={styles.section}>
      <h2 className={styles.sectionTitle}>Interview Preparation</h2>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
        {Object.entries(grouped).map(([category, catQuestions]) => (
          <div key={category}>
            <div className={styles.headingGroup} style={{ color: 'var(--text-primary)' }}>{category}</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {catQuestions.map((q, i) => {
                const diffStyle = getDifficultyBadgeColor(q.difficulty);
                return (
                  <div key={i} className={styles.leftAccentLine} style={{ borderLeftColor: diffStyle.fg, paddingBottom: '0.5rem' }}>
                    <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.25rem', fontSize: '1rem' }}>
                      {q.question}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                      <span className={styles.badge} style={{ backgroundColor: diffStyle.bg, color: diffStyle.fg }}>
                        {q.difficulty}
                      </span>
                      <span className={styles.textSecondary} style={{ fontSize: '0.8rem', fontStyle: 'italic' }}>
                        Triggered by: {q.triggered_by}
                      </span>
                    </div>
                    <div className={styles.textSecondary} style={{ fontSize: '0.85rem' }}>
                      <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Why:</span> {q.reason}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
