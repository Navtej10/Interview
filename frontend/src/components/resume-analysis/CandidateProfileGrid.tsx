import React from 'react';
import styles from './ResumeAnalysis.module.css';
import type { CandidateProfile } from '../../types';

interface CandidateProfileGridProps {
  profile: CandidateProfile;
}

export function CandidateProfileGrid({ profile }: CandidateProfileGridProps) {
  return (
    <div className={styles.section}>
      <h2 className={styles.sectionTitle}>Candidate Profile</h2>
      <div className={`${styles.grid} ${styles.gridGroups}`}>
        <div className={styles.card}>
          <div className={styles.textSecondary} style={{ fontSize: '0.8rem', fontWeight: 600, textTransform: 'uppercase', marginBottom: '0.25rem' }}>Career Stage</div>
          <div style={{ fontWeight: 500 }}>{profile.career_stage}</div>
        </div>
        <div className={styles.card}>
          <div className={styles.textSecondary} style={{ fontSize: '0.8rem', fontWeight: 600, textTransform: 'uppercase', marginBottom: '0.25rem' }}>Primary Domain</div>
          <div style={{ fontWeight: 500 }}>{profile.primary_domain}</div>
        </div>
        <div className={styles.card}>
          <div className={styles.textSecondary} style={{ fontSize: '0.8rem', fontWeight: 600, textTransform: 'uppercase', marginBottom: '0.25rem' }}>Secondary Domain</div>
          <div style={{ fontWeight: 500 }}>{profile.secondary_domain}</div>
        </div>
        <div className={styles.card}>
          <div className={styles.textSecondary} style={{ fontSize: '0.8rem', fontWeight: 600, textTransform: 'uppercase', marginBottom: '0.25rem' }}>Technical Maturity</div>
          <div style={{ fontWeight: 500 }}>{profile.technical_maturity}</div>
        </div>
        <div className={styles.card}>
          <div className={styles.textSecondary} style={{ fontSize: '0.8rem', fontWeight: 600, textTransform: 'uppercase', marginBottom: '0.25rem' }}>Interview Readiness</div>
          <div style={{ fontWeight: 500 }}>{profile.interview_readiness}</div>
        </div>
        <div className={styles.card}>
          <div className={styles.textSecondary} style={{ fontSize: '0.8rem', fontWeight: 600, textTransform: 'uppercase', marginBottom: '0.25rem' }}>Resume Quality</div>
          <div style={{ fontWeight: 500 }}>{profile.resume_quality}</div>
        </div>
      </div>
      <div className={styles.mutedCard} style={{ marginTop: '1rem', borderLeft: '4px solid var(--accent)' }}>
        <div className={styles.textSecondary} style={{ fontSize: '0.8rem', fontWeight: 600, textTransform: 'uppercase', marginBottom: '0.25rem' }}>Overall Recommendation</div>
        <div style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{profile.overall_recommendation}</div>
      </div>
    </div>
  );
}
