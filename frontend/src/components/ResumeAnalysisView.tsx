import React from 'react';
import type { ResumeBundle } from '../types';
import styles from './resume-analysis/ResumeAnalysis.module.css';

import { ReportHeader } from './resume-analysis/ReportHeader';
import { SummaryCard } from './resume-analysis/SummaryCard';
import { CandidateProfileGrid } from './resume-analysis/CandidateProfileGrid';
import { ResumeScoresGrid } from './resume-analysis/ResumeScoresGrid';
import { KeyStrengthsList } from './resume-analysis/KeyStrengthsList';
import { SkillEvidenceSection } from './resume-analysis/SkillEvidenceSection';
import { ProjectReviewCard } from './resume-analysis/ProjectReviewCard';
import { ConsistencyChecklist } from './resume-analysis/ConsistencyChecklist';
import { AtsAnalysisCard } from './resume-analysis/AtsAnalysisCard';
import { TechnicalRisksBoard } from './resume-analysis/TechnicalRisksBoard';
import { InterviewPrepSection } from './resume-analysis/InterviewPrepSection';
import { GrowthRoadmapBoard } from './resume-analysis/GrowthRoadmapBoard';
import { FinalRecommendation } from './resume-analysis/FinalRecommendation';
import { StartInterviewButton } from './resume-analysis/StartInterviewButton';

export function ResumeAnalysisView({
  resume,
  onContinue,
}: {
  resume: ResumeBundle;
  onContinue: () => void;
}) {
  const { analysis } = resume;
  
  if (!analysis.candidate_profile) {
    return <div className={styles.container}>Loading analysis...</div>;
  }

  return (
    <div className={styles.container}>
      <ReportHeader />
      <SummaryCard summary={analysis.summary} />
      <CandidateProfileGrid profile={analysis.candidate_profile} />
      <ResumeScoresGrid scores={analysis.scores} />
      <KeyStrengthsList strengths={analysis.strengths} />
      <SkillEvidenceSection skills={analysis.skill_matrix} />
      
      <div className={styles.section}>
        <h2 className={styles.sectionTitle}>Project Reviews</h2>
        {analysis.project_reviews.length === 0 ? (
          <div className={styles.emptyState}>No projects analyzed.</div>
        ) : (
          analysis.project_reviews.map((project, i) => (
            <ProjectReviewCard key={i} project={project} />
          ))
        )}
      </div>

      <ConsistencyChecklist consistency={analysis.resume_consistency} />
      <AtsAnalysisCard analysis={analysis.ats_analysis} />
      <TechnicalRisksBoard risks={analysis.technical_risks} />
      <InterviewPrepSection questions={analysis.predicted_questions} />
      <GrowthRoadmapBoard roadmap={analysis.growth_roadmap} />
      <FinalRecommendation recommendation={analysis.final_recommendation} />
      
      <StartInterviewButton onClick={onContinue} />
    </div>
  );
}
