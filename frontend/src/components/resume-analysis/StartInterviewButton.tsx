import React from 'react';
import styles from './ResumeAnalysis.module.css';

interface StartInterviewButtonProps {
  onClick: () => void;
}

export function StartInterviewButton({ onClick }: StartInterviewButtonProps) {
  return (
    <div style={{ marginTop: '3rem', marginBottom: '1rem' }}>
      <button className={styles.buttonPrimary} onClick={onClick}>
        Start mock interview
      </button>
    </div>
  );
}
