from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# ---------- Module 1: Resume Parser (structured extraction, no judgment) ----------

class ResumeProject(BaseModel):
    name: str
    description: str
    technologies: list[str]
    role: Optional[str] = None


class ResumeExperience(BaseModel):
    company: str
    title: str
    duration: Optional[str] = None
    bullets: list[str]
    technologies: list[str]


class ResumeEducation(BaseModel):
    institution: str
    degree: str
    field: Optional[str] = None
    duration: Optional[str] = None


class ParsedResume(BaseModel):
    """Pure extraction — no opinions. Judgment lives in ResumeAnalysis."""
    raw_text: str
    skills: list[str]
    projects: list[ResumeProject]
    experience: list[ResumeExperience]
    education: list[ResumeEducation]
    certifications: list[str]
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


class ResumeAnalysis(BaseModel):
    summary: str
    strengths: list[str]
    gaps: list[ResumeGap]
    ats_issues: list[str]


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
