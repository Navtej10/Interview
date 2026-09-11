import React from 'react';
import styles from './ResumeAnalysis.module.css';
import type { Scores, ScoreCard as ScoreCardType } from '../../types';

interface ResumeScoresGridProps {
  scores: Scores;
}

function getScoreColor(score: number) {
  if (score >= 70) return 'var(--score-strong)';
  if (score >= 40) return 'var(--score-moderate)';
  return 'var(--score-weak)';
}

function ScoreCard({ data }: { data: ScoreCardType }) {
  const color = getScoreColor(data.score);
  return (
    <div className={styles.card}>
      <div className={styles.textSecondary} style={{ fontSize: '0.8rem', fontWeight: 600, textTransform: 'uppercase', marginBottom: '0.25rem' }}>
        {data.title}
      </div>
      <div className={styles.scoreNumber} style={{ color }}>
        {data.score}
      </div>
      <div className={styles.progressBarContainer}>
        <div className={styles.progressBarFill} style={{ width: `${data.score}%`, backgroundColor: color }}></div>
      </div>
      <div className={styles.textSecondary} style={{ fontSize: '0.8rem', marginTop: '0.5rem', lineHeight: 1.4 }}>
        {data.reason}
      </div>
    </div>
  );
}

export function ResumeScoresGrid({ scores }: ResumeScoresGridProps) {
  const scoreKeys: (keyof Scores)[] = [
    'overall_resume',
    'ats_compatibility',
    'technical_skills',
    'project_quality',
    'resume_writing',
    'interview_readiness',
    'confidence_score'
  ];

  return (
    <div className={styles.section}>
      <h2 className={styles.sectionTitle}>Resume Scores</h2>
      <div className={`${styles.grid} ${styles.gridScores}`}>
        {scoreKeys.map(key => (
          <ScoreCard key={key} data={scores[key]} />
        ))}
      </div>
    </div>
  );
}
