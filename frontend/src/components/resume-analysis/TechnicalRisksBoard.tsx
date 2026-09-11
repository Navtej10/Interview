import React from 'react';
import styles from './ResumeAnalysis.module.css';
import type { TechnicalRisk } from '../../types';

interface TechnicalRisksBoardProps {
  risks: TechnicalRisk[];
}

const RISK_LEVELS = ['High', 'Medium', 'Low'] as const;

function getRiskColor(level: string) {
  switch (level.toLowerCase()) {
    case 'high': return 'var(--score-weak)';
    case 'medium': return 'var(--score-moderate)';
    case 'low': return 'var(--score-strong)';
    default: return 'var(--text-muted)';
  }
}

export function TechnicalRisksBoard({ risks }: TechnicalRisksBoardProps) {
  const grouped = risks.reduce((acc, risk) => {
    const level = RISK_LEVELS.find(l => l.toLowerCase() === risk.risk_level.toLowerCase()) || 'Low';
    if (!acc[level]) acc[level] = [];
    acc[level].push(risk);
    return acc;
  }, {} as Record<string, TechnicalRisk[]>);

  if (risks.length === 0) {
    return (
      <div className={styles.section}>
        <h2 className={styles.sectionTitle}>Technical Risks</h2>
        <div className={styles.emptyState}>No technical risks identified.</div>
      </div>
    );
  }

  return (
    <div className={styles.section}>
      <h2 className={styles.sectionTitle}>Technical Risks</h2>
      <div className={`${styles.grid} ${styles.gridGroups}`}>
        {RISK_LEVELS.map(level => {
          const levelRisks = grouped[level];
          if (!levelRisks || levelRisks.length === 0) return null;
          const color = getRiskColor(level);
          return (
            <div key={level}>
              <div className={styles.headingGroup} style={{ color }}>{level} Risk</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {levelRisks.map((r, i) => (
                  <div key={i} className={styles.card} style={{ padding: '0.75rem 1rem' }}>
                    <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.25rem' }}>{r.technology}</div>
                    <div className={styles.textSecondary} style={{ fontSize: '0.85rem' }}>{r.reason}</div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
