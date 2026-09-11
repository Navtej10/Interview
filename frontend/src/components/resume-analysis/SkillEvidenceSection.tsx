import React from 'react';
import styles from './ResumeAnalysis.module.css';
import type { SkillEvidence } from '../../types';

interface SkillEvidenceSectionProps {
  skills: SkillEvidence[];
}

const CONFIDENCE_LEVELS = ['High', 'Medium', 'Low', 'Unverified'] as const;

function getConfidenceColor(level: string) {
  switch (level.toLowerCase()) {
    case 'high': return 'var(--confidence-high)';
    case 'medium': return 'var(--confidence-medium)';
    case 'low': return 'var(--confidence-low)';
    case 'unverified': return 'var(--confidence-unverified)';
    default: return 'var(--text-muted)';
  }
}

export function SkillEvidenceSection({ skills }: SkillEvidenceSectionProps) {
  const grouped = skills.reduce((acc, skill) => {
    const level = CONFIDENCE_LEVELS.find(l => l.toLowerCase() === skill.confidence.toLowerCase()) || 'Unverified';
    if (!acc[level]) acc[level] = [];
    acc[level].push(skill);
    return acc;
  }, {} as Record<string, SkillEvidence[]>);

  return (
    <div className={styles.section}>
      <h2 className={styles.sectionTitle}>Skill Evidence Analysis</h2>
      <div className={`${styles.grid} ${styles.gridGroups}`}>
        {CONFIDENCE_LEVELS.map(level => {
          const levelSkills = grouped[level];
          if (!levelSkills || levelSkills.length === 0) return null;
          const color = getConfidenceColor(level);
          return (
            <div key={level}>
              <div className={styles.headingGroup} style={{ color }}>{level} Confidence</div>
              <div>
                {levelSkills.map((s, i) => (
                  <div key={i} className={styles.leftAccentLine} style={{ borderLeftColor: color }}>
                    <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.25rem' }}>{s.skill}</div>
                    <div className={styles.quotedText} style={{ fontSize: '0.85rem', marginBottom: '0.25rem' }}>"{s.evidence}"</div>
                    <div className={styles.textSecondary} style={{ fontSize: '0.85rem' }}>{s.reason}</div>
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
