from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator, AliasChoices


# ---------- Module 1: Resume Parser (structured extraction, no judgment) ----------

class ResumeProject(BaseModel):
    name: str
    description: str
    technologies: list[str] = Field(default_factory=list)
    role: Optional[str] = None

    @field_validator("technologies", mode="before")
    @classmethod
    def none_to_empty(cls, v):
        return v or []


class ResumeExperience(BaseModel):
    company: str
    title: str
    duration: Optional[str] = None
    bullets: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)

    @field_validator("bullets", "technologies", mode="before")
    @classmethod
    def none_to_empty(cls, v):
        return v or []


class ResumeEducation(BaseModel):
    institution: str
    degree: str
    field: Optional[str] = Field(None, validation_alias=AliasChoices("field", "specialization"))
    duration: Optional[str] = None


class ResumeCertification(BaseModel):
    name: str = Field(validation_alias=AliasChoices("name", "certification name", "certification_name", "certification"))
    issuer: Optional[str] = None
    year: Optional[str] = None
    url: Optional[str] = Field(None, validation_alias=AliasChoices("url", "credential URL", "credential_url", "credential url", "link"))


class ParsedResume(BaseModel):
    """Pure extraction — no opinions. Judgment lives in ResumeAnalysis."""
    raw_text: str
    skills: list[str]
    projects: list[ResumeProject]
    experience: list[ResumeExperience]
    education: list[ResumeEducation]
    certifications: list[ResumeCertification]
    achievements: list[str]
    low_confidence: bool = False
    parse_quality_notes: list[str] = Field(default_factory=list)


# ---------- Module 2: Resume Analysis Engine (judgment, on top of ParsedResume) ----------

class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"

class ResumeGap(BaseModel):
    category: str  # "vague_description" | "missing_metric" | "unsupported_skill" | "ats_issue" | "formatting"
    location: str  # e.g. "Experience > Acme Corp > bullet 2"
    issue: str
    suggestion: str
    severity: Severity = Severity.medium

class CandidateProfile(BaseModel):
    career_stage: str
    primary_domain: str
    secondary_domain: str
    technical_maturity: str
    experience_level: str
    interview_readiness: str
    resume_quality: str
    overall_recommendation: str

class ScoreCard(BaseModel):
    title: str
    score: int
    reason: str

class Scores(BaseModel):
    overall_resume: ScoreCard
    ats_compatibility: ScoreCard
    technical_skills: ScoreCard
    project_quality: ScoreCard
    resume_writing: ScoreCard
    interview_readiness: ScoreCard
    confidence_score: ScoreCard

class SkillEvidence(BaseModel):
    skill: str
    confidence: str # High, Medium, Low, Unverified
    evidence: str # Project, Experience, Certification, Coursework, Hackathon, Summary
    reason: str
    confidence_score: int

class ProjectReview(BaseModel):
    name: str
    complexity: int
    innovation: int
    technical_depth: int
    architecture: int
    ownership: int
    documentation: int
    resume_quality: int
    impact: int
    role_clarity: int
    metrics_present: bool
    strengths: list[str]
    weaknesses: list[str]
    missing_information: list[str]
    improvements: list[str]
    likely_interview_questions: list[str]

class ExperienceReview(BaseModel):
    is_student: bool
    projects_evaluation: str
    hackathons_evaluation: str
    research_evaluation: str
    open_source_evaluation: str
    work_experience_evaluation: Optional[str] = None

class ResumeConsistency(BaseModel):
    summary_aligns_with_projects: bool
    skills_align_with_projects: bool
    projects_align_with_career_objective: bool
    education_supports_domain: bool
    dates_consistent: bool
    no_duplicates: bool
    technologies_consistent: bool

class ATSAnalysis(BaseModel):
    ats_score: int
    formatting: str
    keyword_coverage: str
    section_detection: str
    date_formatting: str
    bullet_quality: str
    missing_keywords: list[str]
    parseability: str
    recommendations: list[str]

class TechnicalRisk(BaseModel):
    technology: str
    risk_level: str # High, Medium, Low
    reason: str
    suggested_preparation: str

class PredictedQuestion(BaseModel):
    question: str
    category: str # Resume Walkthrough, Projects, Programming, CS Fundamentals, Behavioral, Scenario Based
    difficulty: str # Easy, Medium, Hard
    reason: str
    triggered_by: str
    probability: int

class GrowthRecommendation(BaseModel):
    recommendation: str
    priority: str # High, Medium, Low
    reason: str
    expected_impact: str
    estimated_effort: str

class GrowthRoadmap(BaseModel):
    high_priority: list[GrowthRecommendation] = Field(default_factory=list)
    medium_priority: list[GrowthRecommendation] = Field(default_factory=list)
    low_priority: list[GrowthRecommendation] = Field(default_factory=list)

class ResumeAnalysis(BaseModel):
    candidate_profile: CandidateProfile
    scores: Scores
    summary: str
    strengths: list[str]
    skill_matrix: list[SkillEvidence]
    project_reviews: list[ProjectReview]
    experience_review: ExperienceReview
    resume_consistency: ResumeConsistency
    ats_analysis: ATSAnalysis
    technical_risks: list[TechnicalRisk]
    predicted_questions: list[PredictedQuestion]
    growth_roadmap: Optional[GrowthRoadmap] = None
    gaps: list[ResumeGap] = Field(default_factory=list)
    final_recommendation: str = ""


# ---------- Module 3: Resume Knowledge Graph ----------

class GraphNode(BaseModel):
    id: str
    label: str
    type: str  # "skill" | "project" | "technology" | "experience"


class GraphEdge(BaseModel):
    source: str  # node id
    target: str  # node id
    relation: str  # "uses" | "used_in" | "demonstrates"


class KnowledgeGraph(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]

    def technologies_for_project(self, project_node_id: str) -> list[str]:
        return [e.target for e in self.edges if e.source == project_node_id and e.relation == "uses"]

    def unsupported_skills(self) -> list[str]:
        """Skills with no 'demonstrates' edge pointing at them — i.e. claimed
        but never tied to a project/experience technology. Fast, deterministic
        cross-check that complements the LLM-driven gap analysis."""
        demonstrated = {e.target for e in self.edges if e.relation == "demonstrates"}
        return [n.label for n in self.nodes if n.type == "skill" and n.id not in demonstrated]

    def demonstrated_projects_for_skill(self, skill_id: str) -> list[str]:
        """Inverse of unsupported_skills(): given a skill node ID, return the
        labels of every project or experience node that backs it.

        Walk: skill ←[demonstrates]— tech ←[uses]— project/experience.

        Returns labels (not IDs) so callers can use them directly in prompts
        or display.  Returns an empty list if the skill is unsupported."""
        # Step 1: find all technology node IDs that 'demonstrate' this skill
        tech_ids = {
            e.source for e in self.edges
            if e.target == skill_id and e.relation == "demonstrates"
        }
        # Step 2: find all project/experience nodes that 'use' those techs
        parent_ids = {
            e.source for e in self.edges
            if e.target in tech_ids and e.relation == "uses"
        }
        # Step 3: resolve IDs → labels
        node_map = {n.id: n for n in self.nodes}
        return [
            node_map[pid].label for pid in parent_ids
            if pid in node_map and node_map[pid].type in ("project", "experience")
        ]


class ResumeBundle(BaseModel):
    """What the rest of the app actually works with — parser + analysis + graph combined."""
    parsed: ParsedResume
    analysis: ResumeAnalysis
    graph: KnowledgeGraph


# ---------- Interview ----------

class Difficulty(str, Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


# ---------- Module 5: Interview Planner ----------

class InterviewSection(BaseModel):
    name: str  # e.g. "Project Deep Dive: AssetFlow"
    objective: str  # what this section is trying to establish
    target_topics: list[str]  # specific projects/skills/experience entries to cover
    target_difficulty: Difficulty
    estimated_turns: int  # number of question/answer turns allotted


class ScoringCriterion(BaseModel):
    name: str  # e.g. "Technical depth", "Communication clarity"
    weight: float  # 0-1, should sum to ~1 across all criteria
    description: str


class InterviewPlan(BaseModel):
    sections: list[InterviewSection]
    total_estimated_turns: int
    scoring_criteria: list[ScoringCriterion]


class TranscriptTurn(BaseModel):
    role: str  # "interviewer" | "candidate"
    content: str
    topic: Optional[str] = None  # which resume item / concept this turn targets


class InterviewPhase(str, Enum):
    in_progress = "in_progress"
    final_section = "final_section"
    wrapping_up = "wrapping_up"
    complete = "complete"


class PerformanceNote(BaseModel):
    topic: str
    difficulty: Difficulty
    quality: str


class InterviewState(BaseModel):
    session_id: str
    resume: ResumeBundle
    plan: InterviewPlan
    transcript: list[TranscriptTurn] = Field(default_factory=list)
    covered_topics: list[str] = Field(default_factory=list)
    performance_notes: list[PerformanceNote] = Field(default_factory=list)
    current_difficulty: Difficulty = Difficulty.medium
    turn_count: int = 0
    is_complete: bool = False
    final_scores: Optional['ScoringResult'] = None


class NextQuestionResponse(BaseModel):
    question: str
    topic: str
    section: str  # which plan section this question belongs to
    difficulty: Difficulty
    rationale: str  # internal-only: why this question was chosen (deepen/pivot/simplify/follow-up)


# ---------- Module 17: Behavior Engine ----------

class BehaviorCues(BaseModel):
    emphasis_points: list[str] = Field(default_factory=list)
    expression: str
    blink_rate: float
    gaze_pattern: str


# ---------- Feedback ----------

class CriterionScore(BaseModel):
    criterion_name: str
    score: float
    justification: str
    location: str

class ScoringResult(BaseModel):
    scores: list[CriterionScore]
    weighted_overall: float


class FeedbackMode(str, Enum):
    live_debrief = "live_debrief"
    written_report = "written_report"


class FeedbackReport(BaseModel):
    overall_summary: str
    scores: list[CriterionScore]
    weighted_overall: float
    strengths: list[str]
    weaknesses: list[str]
    moment_highlights: list[str]  # specific callouts tied to transcript moments
    recommended_next_steps: list[str]
