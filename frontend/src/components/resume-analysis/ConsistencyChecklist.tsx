import React from 'react';
import styles from './ResumeAnalysis.module.css';
import type { ResumeConsistency } from '../../types';

interface ConsistencyChecklistProps {
  consistency: ResumeConsistency;
}

function CheckRow({ label, isConsistent }: { label: string, isConsistent: boolean }) {
  return (
    <div className={styles.checklistRow}>
      <div className={styles.checklistIcon} style={{ color: isConsistent ? 'var(--score-strong)' : 'var(--score-weak)' }}>
        {isConsistent ? '✓' : '✗'}
      </div>
      <div>
        <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{label}</span>
      </div>
    </div>
  );
}

export function ConsistencyChecklist({ consistency }: ConsistencyChecklistProps) {
  return (
    <div className={styles.section}>
      <h2 className={styles.sectionTitle}>Consistency Checklist</h2>
      <div className={styles.card}>
        <CheckRow label="Summary alignment with projects" isConsistent={consistency.summary_aligns_with_projects} />
        <CheckRow label="Skills alignment with projects" isConsistent={consistency.skills_align_with_projects} />
        <CheckRow label="Technology consistency" isConsistent={consistency.technologies_consistent} />
        <CheckRow label="Date formatting and gaps" isConsistent={consistency.dates_consistent} />
        <CheckRow label="Duplicate content detection" isConsistent={consistency.no_duplicates} />
      </div>
    </div>
  );
}
