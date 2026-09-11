import React from 'react';
import styles from './ResumeAnalysis.module.css';
import type { ProjectReview } from '../../types';

interface ProjectReviewCardProps {
  project: ProjectReview;
}

function SectionList({ title, items }: { title: string, items: string[] }) {
  return (
    <div className={styles.rowItem}>
      <div className={styles.textSecondary} style={{ fontSize: '0.8rem', fontWeight: 600, textTransform: 'uppercase', marginBottom: '0.25rem' }}>{title}</div>
      {items.length === 0 ? (
        <div className={styles.emptyState}>No {title.toLowerCase()} found.</div>
      ) : (
        <ul className={`${styles.listUnstyled} ${styles.bulletList}`} style={{ fontSize: '0.9rem' }}>
          {items.map((item, i) => <li key={i}>• {item}</li>)}
        </ul>
      )}
    </div>
  );
}

export function ProjectReviewCard({ project }: ProjectReviewCardProps) {
  return (
    <div className={styles.card} style={{ marginBottom: '1.5rem' }}>
      <h3 style={{ fontSize: '1.1rem', fontWeight: 600, marginTop: 0, marginBottom: '1rem', color: 'var(--text-primary)' }}>{project.name}</h3>
      <div className={styles.grid} style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
        <SectionList title="Strengths" items={project.strengths} />
        <SectionList title="Weaknesses" items={project.weaknesses} />
        <SectionList title="Missing Information" items={project.missing_information} />
        <SectionList title="Suggested Improvements" items={project.improvements} />
      </div>
      
      {project.likely_interview_questions.length > 0 && (
        <>
          <div className={styles.divider} />
          <div className={styles.textSecondary} style={{ fontSize: '0.8rem', fontWeight: 600, textTransform: 'uppercase', marginBottom: '0.5rem' }}>Likely Interview Questions</div>
          {project.likely_interview_questions.map((q, i) => (
            <div key={i} className={styles.quotedText} style={{ fontSize: '0.9rem', marginBottom: '0.5rem' }}>
              "{q}"
            </div>
          ))}
        </>
      )}
    </div>
  );
}
