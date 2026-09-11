import React from 'react';
import styles from './ResumeAnalysis.module.css';
import type { GrowthRoadmap, GrowthRecommendation } from '../../types';

interface GrowthRoadmapBoardProps {
  roadmap: GrowthRoadmap;
}

const PRIORITIES = ['High', 'Medium', 'Low'] as const;

function getPriorityColor(priority: string) {
  switch (priority.toLowerCase()) {
    case 'high': return 'var(--score-weak)';
    case 'medium': return 'var(--score-moderate)';
    case 'low': return 'var(--score-strong)';
    default: return 'var(--text-muted)';
  }
}

export function GrowthRoadmapBoard({ roadmap }: GrowthRoadmapBoardProps) {
  return (
    <div className={styles.section}>
      <h2 className={styles.sectionTitle}>Growth Roadmap</h2>
      <div className={`${styles.grid} ${styles.gridGroups}`}>
        {PRIORITIES.map(priority => {
          let items: GrowthRecommendation[] = [];
          if (priority === 'High') items = roadmap.high_priority || [];
          if (priority === 'Medium') items = roadmap.medium_priority || [];
          if (priority === 'Low') items = roadmap.low_priority || [];

          if (items.length === 0) return null;
          const color = getPriorityColor(priority);

          return (
            <div key={priority}>
              <div className={styles.headingGroup} style={{ color }}>{priority} Priority</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {items.map((item, i) => (
                  <div key={i} className={styles.card} style={{ padding: '0.75rem 1rem' }}>
                    <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.25rem' }}>{item.recommendation}</div>
                    <div className={styles.textSecondary} style={{ fontSize: '0.85rem', marginBottom: '0.5rem' }}>
                      {item.reason}
                    </div>
                    <div className={styles.textSecondary} style={{ fontSize: '0.8rem', fontStyle: 'italic', borderTop: '1px solid var(--border)', paddingTop: '0.5rem' }}>
                      <span style={{ fontWeight: 600 }}>Impact:</span> {item.expected_impact}
                    </div>
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
