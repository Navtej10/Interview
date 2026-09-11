import React from 'react';
import styles from './ResumeAnalysis.module.css';
import type { ATSAnalysis } from '../../types';

interface AtsAnalysisCardProps {
  analysis: ATSAnalysis;
}

function getAtsColor(score: number) {
  if (score >= 70) return 'var(--score-strong)';
  if (score >= 40) return 'var(--score-moderate)';
  return 'var(--score-weak)';
}

export function AtsAnalysisCard({ analysis }: AtsAnalysisCardProps) {
  const color = getAtsColor(analysis.ats_score);

  return (
    <div className={styles.section}>
      <h2 className={styles.sectionTitle}>ATS Analysis</h2>
      <div className={styles.card}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '0.25rem' }}>
          <div className={styles.textSecondary} style={{ fontSize: '0.8rem', fontWeight: 600, textTransform: 'uppercase' }}>ATS Match Score</div>
          <div className={styles.scoreNumber} style={{ color, fontSize: '1.25rem' }}>{analysis.ats_score}/100</div>
        </div>
        <div className={styles.progressBarContainer} style={{ marginBottom: '1.5rem' }}>
          <div className={styles.progressBarFill} style={{ width: `${analysis.ats_score}%`, backgroundColor: color }}></div>
        </div>

        <div className={styles.grid} style={{ gap: '1.5rem' }}>
          <div>
            <div className={styles.textSecondary} style={{ fontSize: '0.8rem', fontWeight: 600, textTransform: 'uppercase', marginBottom: '0.25rem' }}>Formatting</div>
            <div style={{ fontSize: '0.9rem' }}>{analysis.formatting}</div>
          </div>
          
          <div>
            <div className={styles.textSecondary} style={{ fontSize: '0.8rem', fontWeight: 600, textTransform: 'uppercase', marginBottom: '0.25rem' }}>Keyword Coverage</div>
            <div style={{ fontSize: '0.9rem', marginBottom: '0.5rem' }}>{analysis.keyword_coverage}</div>
            
            {analysis.missing_keywords.length > 0 ? (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '0.5rem' }}>
                {analysis.missing_keywords.map((kw, i) => (
                  <span key={i} className={styles.badge} style={{ backgroundColor: 'var(--score-weak-bg)', color: 'var(--score-weak)' }}>
                    {kw}
                  </span>
                ))}
              </div>
            ) : (
              <div className={styles.emptyState}>No missing keywords found.</div>
            )}
          </div>

          <div>
            <div className={styles.textSecondary} style={{ fontSize: '0.8rem', fontWeight: 600, textTransform: 'uppercase', marginBottom: '0.25rem' }}>Suggestions</div>
            {analysis.recommendations.length > 0 ? (
              <ul className={`${styles.listUnstyled} ${styles.bulletList}`} style={{ fontSize: '0.9rem' }}>
                {analysis.recommendations.map((r, i) => <li key={i}>• {r}</li>)}
              </ul>
            ) : (
              <div className={styles.emptyState}>No suggestions.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
