import React from 'react';
import styles from './ResumeAnalysis.module.css';

interface SummaryCardProps {
  summary: string;
}

export function SummaryCard({ summary }: SummaryCardProps) {
  return (
    <div className={styles.section}>
      <div className={styles.mutedCard}>
        {summary}
      </div>
    </div>
  );
}
