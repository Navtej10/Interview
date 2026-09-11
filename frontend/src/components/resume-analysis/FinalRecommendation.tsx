import React from 'react';
import styles from './ResumeAnalysis.module.css';

interface FinalRecommendationProps {
  recommendation: string;
}

export function FinalRecommendation({ recommendation }: FinalRecommendationProps) {
  return (
    <div className={styles.section}>
      <h2 className={styles.sectionTitle}>Final Recommendation</h2>
      <div className={styles.mutedCard}>
        {recommendation || 'No final recommendation provided.'}
      </div>
    </div>
  );
}
