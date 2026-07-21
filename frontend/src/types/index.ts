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

export interface ResumeAnalysis {
  summary: string
  strengths: string[]
  gaps: ResumeGap[]
  ats_issues: string[]
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
