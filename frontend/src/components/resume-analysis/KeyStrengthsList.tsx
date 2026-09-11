import React from 'react';
import styles from './ResumeAnalysis.module.css';

interface KeyStrengthsListProps {
  strengths: string[];
}

export function KeyStrengthsList({ strengths }: KeyStrengthsListProps) {
  return (
    <div className={styles.section}>
      <h2 className={styles.sectionTitle}>Key Strengths</h2>
      {strengths.length === 0 ? (
        <div className={styles.emptyState}>No key strengths identified.</div>
      ) : (
        <div className={styles.grid}>
          {strengths.map((s, i) => (
            <div key={i} className={styles.rowItem} style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
              <div style={{
                flexShrink: 0,
                width: '1.5rem',
                height: '1.5rem',
                borderRadius: '50%',
                backgroundColor: 'var(--surface-muted)',
                color: 'var(--text-secondary)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '0.75rem',
                fontWeight: 600,
                marginTop: '0.1rem'
              }}>
                {i + 1}
              </div>
              <div>{s}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
