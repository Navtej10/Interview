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

    @field_validator("score", mode="before")
    @classmethod
    def parse_score(cls, v):
        if isinstance(v, (int, float)):
            return int(v)
        if isinstance(v, str):
            import re
            match = re.search(r'\d+', v)
            if match:
                return int(match.group())
            val = 0
            w = v.lower()
            if 'hundred' in w: return 100
            for k, n in {'twenty': 20, 'thirty': 30, 'forty': 40, 'fifty': 50, 'sixty': 60, 'seventy': 70, 'eighty': 80, 'ninety': 90}.items():
                if k in w:
                    val += n
                    break
            for k, n in {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10, 'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14, 'fifteen': 15, 'sixteen': 16, 'seventeen': 17, 'eighteen': 18, 'nineteen': 19}.items():
                if k in w:
                    val += n
                    break
            if val > 0: return val
        return 0

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

    @field_validator("high_priority", "medium_priority", "low_priority", mode="before")
    @classmethod
    def parse_string_to_dict(cls, v):
        if not v:
            return []
        parsed = []
        for item in v:
            if isinstance(item, str):
                try:
                    import json
                    parsed.append(json.loads(item))
                except Exception:
                    pass # skip invalid strings
            else:
                parsed.append(item)
        return parsed

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


class QuestionMix(BaseModel):
    behavioral: float
    technical: float
    case_or_system_design: float
    culture_fit: float

class QuestionMixShift(BaseModel):
    behavioral: Optional[float] = 0.0
    technical: Optional[float] = 0.0
    case_or_system_design: Optional[float] = 0.0
    culture_fit: Optional[float] = 0.0

class SeniorityModifier(BaseModel):
    question_mix_shift: QuestionMixShift
    difficulty_start: str
    evaluation_emphasis: list[str]

class VocabularyCues(BaseModel):
    phrases: list[str]
    avoid: list[str]

class InterviewerPersona(BaseModel):
    tone: str
    follow_up_style: str
    pacing: str

class CompanyStyleProfile(BaseModel):
    company: str
    interview_philosophy: str
    question_mix: QuestionMix
    signature_formats: list[str]
    evaluation_dimensions: list[str]
    interviewer_persona: InterviewerPersona
    difficulty_curve: str
    red_flags: list[str]
    distinctive_mechanism: str
    closing_style: str  # Note: Internal generation cue only; do not expose to users.
    seniority_modifiers: dict[str, SeniorityModifier]
    vocabulary_cues: VocabularyCues
    disclaimer: str
    profile_version: str
    last_reviewed: str
    review_notes: str


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
    introduction = "introduction"
    background = "background"
    technical = "technical"
    behavioral = "behavioral"
    closing = "closing"
    complete = "complete"


class TerminationReason(str, Enum):
    normal_completion = "normal_completion"
    early_insufficient_evidence = "early_insufficient_evidence"
    early_repeated_non_answers = "early_repeated_non_answers"
    user_ended = "user_ended"


class AnswerQuality(str, Enum):
    excellent = "excellent"
    strong = "strong"
    adequate = "adequate"
    partial = "partial"
    weak = "weak"
    irrelevant = "irrelevant"
    filler = "filler"
    evasive = "evasive"
    incorrect = "incorrect"
    no_answer = "no_answer"

class AnswerEvaluation(BaseModel):
    overall_quality: AnswerQuality
    relevance: float = Field(ge=0, le=1)
    technical_correctness: float = Field(ge=0, le=1)
    technical_depth: float = Field(ge=0, le=1)
    specificity: float = Field(ge=0, le=1)
    communication: float = Field(ge=0, le=1)
    reasoning: float = Field(ge=0, le=1)
    completeness: float = Field(ge=0, le=1)
    
    is_filler: bool = False
    is_evasive: bool = False
    is_irrelevant: bool = False
    is_incorrect: bool = False
    
    evidence: list[str] = Field(default_factory=list)
    missing_points: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    
    confidence: float = Field(ge=0, le=1)


class PerformanceNote(BaseModel):
    topic: str
    difficulty: Difficulty
    evaluation: AnswerEvaluation


class InterviewState(BaseModel):
    session_id: str
    resume: ResumeBundle
    plan: InterviewPlan
    company_profile: Optional[CompanyStyleProfile] = None
    transcript: list[TranscriptTurn] = Field(default_factory=list)
    covered_topics: list[str] = Field(default_factory=list)
    performance_notes: list[PerformanceNote] = Field(default_factory=list)
    current_difficulty: Difficulty = Difficulty.medium
    turn_count: int = 0
    current_section_index: int = 0
    consecutive_weak_answers: int = 0
    consecutive_irrelevant_answers: int = 0
    consecutive_non_answers: int = 0
    recovery_attempts: int = 0
    termination_reason: Optional[TerminationReason] = None
    is_complete: bool = False
    final_scores: Optional['ScoringResult'] = None
    inferred_seniority: Optional[str] = None


class NextQuestionResponse(BaseModel):
    question: str
    topic: str
    section: str  # which plan section this question belongs to
    difficulty: Difficulty
    rationale: str  # internal-only: why this question was chosen (deepen/pivot/simplify/follow-up)
    strategy: str
    evaluation: Optional[AnswerEvaluation] = None
    relationship_to_answer: str
    difficulty_adjustment: str
    phase: Optional[str] = None
    isFinalTurn: bool = False


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


class OverallPerformance(BaseModel):
    summary: str
    completion_status: str
    strongest_areas: list[str]
    weakest_areas: list[str]

class TechnicalKnowledge(BaseModel):
    technical_correctness: str
    depth_of_understanding: str
    implementation_details: str
    fundamentals: str
    tradeoffs: str
    debugging_problem_solving: str
    system_design: str

class CommunicationAssessment(BaseModel):
    clarity: str
    structure: str
    conciseness: str
    directness: str
    explanation_ability: str
    concrete_examples: str

class ReasoningAbility(BaseModel):
    problem_breakdown: str
    explaining_reasoning: str
    evaluating_alternatives: str
    reasoning_tradeoffs: str
    handling_followups: str
    adaptability: str

class ProjectOwnership(BaseModel):
    what_built: str
    responsibilities: str
    technical_decisions: str
    challenges: str
    outcomes: str

class ResumeCredibility(BaseModel):
    supported_claims: list[str]
    partially_supported_claims: list[str]
    unverified_claims: list[str]
    inconsistencies: list[str]

class WeaknessEvidence(BaseModel):
    description: str
    evidence: str

class InterviewBehavior(BaseModel):
    patterns: list[str]

class ConfidenceLevels(BaseModel):
    high_confidence: list[str]
    medium_confidence: list[str]
    low_confidence: list[str]
    unassessed: list[str]

class EarlyTerminationContext(BaseModel):
    termination_reason: str
    meaningful_answers_collected: int
    unassessed_dimensions: list[str]
    assessment_reliability: str

class FeedbackReport(BaseModel):
    overall_performance: OverallPerformance
    technical_knowledge: TechnicalKnowledge
    communication: CommunicationAssessment
    reasoning_ability: ReasoningAbility
    project_ownership: ProjectOwnership
    resume_credibility: ResumeCredibility
    technical_weaknesses: list[WeaknessEvidence]
    communication_weaknesses: list[WeaknessEvidence]
    interview_behavior: InterviewBehavior
    confidence_levels: ConfidenceLevels
    early_termination_context: Optional[EarlyTerminationContext] = None
    scores: list[CriterionScore]
    weighted_overall: float
    company_style: Optional[str] = None
    company_disclaimer: Optional[str] = None
