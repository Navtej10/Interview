export interface ResumeProject {
  name: string
  description: string
  technologies: string[]
  role?: string | null
}

export interface ResumeExperience {
  company: string
  title: string
  duration?: string | null
  bullets: string[]
  technologies: string[]
}

export interface ResumeEducation {
  institution: string
  degree: string
  field?: string | null
  duration?: string | null
}

export interface ParsedResume {
  raw_text: string
  skills: string[]
  projects: ResumeProject[]
  experience: ResumeExperience[]
  education: ResumeEducation[]
  certifications: string[]
  achievements: string[]
}

export type Severity = 'low' | 'medium' | 'high'

export interface ResumeGap {
  category: 'vague_description' | 'missing_metric' | 'unsupported_skill' | 'ats_issue' | 'formatting'
  location: string
  issue: string
  suggestion: string
  severity: Severity
}

export interface CandidateProfile {
  career_stage: string
  primary_domain: string
  secondary_domain: string
  technical_maturity: string
  experience_level: string
  interview_readiness: string
  resume_quality: string
  overall_recommendation: string
}

export interface ScoreCard {
  title: string
  score: number
  reason: string
}

export interface Scores {
  overall_resume: ScoreCard
  ats_compatibility: ScoreCard
  technical_skills: ScoreCard
  project_quality: ScoreCard
  resume_writing: ScoreCard
  interview_readiness: ScoreCard
  confidence_score: ScoreCard
}

export interface SkillEvidence {
  skill: string
  confidence: string
  evidence: string
  reason: string
  confidence_score: number
}

export interface ProjectReview {
  name: string
  complexity: number
  innovation: number
  technical_depth: number
  architecture: number
  ownership: number
  documentation: number
  resume_quality: number
  impact: number
  role_clarity: number
  metrics_present: boolean
  strengths: string[]
  weaknesses: string[]
  missing_information: string[]
  improvements: string[]
  likely_interview_questions: string[]
}

export interface ExperienceReview {
  is_student: boolean
  projects_evaluation: string
  hackathons_evaluation: string
  research_evaluation: string
  open_source_evaluation: string
  work_experience_evaluation?: string | null
}

export interface ResumeConsistency {
  summary_aligns_with_projects: boolean
  skills_align_with_projects: boolean
  projects_align_with_career_objective: boolean
  education_supports_domain: boolean
  dates_consistent: boolean
  no_duplicates: boolean
  technologies_consistent: boolean
}

export interface ATSAnalysis {
  ats_score: number
  formatting: string
  keyword_coverage: string
  section_detection: string
  date_formatting: string
  bullet_quality: string
  missing_keywords: string[]
  parseability: string
  recommendations: string[]
}

export interface TechnicalRisk {
  technology: string
  risk_level: string
  reason: string
  suggested_preparation: string
}

export interface PredictedQuestion {
  question: string
  category: string
  difficulty: string
  reason: string
  triggered_by: string
  probability: number
}

export interface GrowthRecommendation {
  recommendation: string
  priority: string
  reason: string
  expected_impact: string
  estimated_effort: string
}

export interface GrowthRoadmap {
  high_priority: GrowthRecommendation[]
  medium_priority: GrowthRecommendation[]
  low_priority: GrowthRecommendation[]
}

export interface ResumeAnalysis {
  candidate_profile: CandidateProfile
  scores: Scores
  summary: string
  strengths: string[]
  skill_matrix: SkillEvidence[]
  project_reviews: ProjectReview[]
  experience_review: ExperienceReview
  resume_consistency: ResumeConsistency
  ats_analysis: ATSAnalysis
  technical_risks: TechnicalRisk[]
  predicted_questions: PredictedQuestion[]
  growth_roadmap: GrowthRoadmap
  gaps: ResumeGap[]
  final_recommendation: string
}

export interface GraphNode {
  id: string
  label: string
  type: 'skill' | 'project' | 'technology' | 'experience'
}

export interface GraphEdge {
  source: string
  target: string
  relation: 'uses' | 'used_in' | 'demonstrates'
}

export interface KnowledgeGraph {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export interface ResumeBundle {
  parsed: ParsedResume
  analysis: ResumeAnalysis
  graph: KnowledgeGraph
}

export type Difficulty = 'easy' | 'medium' | 'hard'

export interface InterviewSection {
  name: string
  objective: string
  target_topics: string[]
  target_difficulty: Difficulty
  estimated_turns: number
}

export interface ScoringCriterion {
  name: string
  weight: number
  description: string
}

export interface InterviewPlan {
  sections: InterviewSection[]
  total_estimated_turns: number
  scoring_criteria: ScoringCriterion[]
}

export interface NextQuestionResponse {
  question: string
  topic: string
  section: string
  difficulty: Difficulty
  rationale: string
}

export interface FeedbackReport {
  overall_summary: string
  strengths: string[]
  weaknesses: string[]
  moment_highlights: string[]
  recommended_next_steps: string[]
}
