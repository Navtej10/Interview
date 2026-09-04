import pytest
from app.models.schemas import Difficulty, InterviewState, PerformanceNote, ResumeBundle, ParsedResume, ResumeAnalysis, KnowledgeGraph, InterviewPlan, AnswerEvaluation, AnswerQuality

from app.services.adaptive_difficulty import next_difficulty

def create_eval(quality: AnswerQuality) -> AnswerEvaluation:
    return AnswerEvaluation(
        overall_quality=quality,
        relevance=1.0,
        technical_correctness=1.0,
        technical_depth=1.0,
        specificity=1.0,
        communication=1.0,
        reasoning=1.0,
        completeness=1.0,
        confidence=1.0
    )

@pytest.fixture
def mock_state():
    resume = ResumeBundle(
        parsed=ParsedResume(skills=[], projects=[], experience=[], education=[], certifications=[], achievements=[], raw_text=""),
        analysis=ResumeAnalysis(
                candidate_profile={"career_stage":"","primary_domain":"","secondary_domain":"","technical_maturity":"","experience_level":"","interview_readiness":"","resume_quality":"","overall_recommendation":""},
                scores={"overall_resume":{"title":"","score":0,"reason":""},"ats_compatibility":{"title":"","score":0,"reason":""},"technical_skills":{"title":"","score":0,"reason":""},"project_quality":{"title":"","score":0,"reason":""},"resume_writing":{"title":"","score":0,"reason":""},"interview_readiness":{"title":"","score":0,"reason":""},"confidence_score":{"title":"","score":0,"reason":""}},
                summary="A test candidate", gaps=[], strengths=[], skill_matrix=[], project_reviews=[],
                experience_review={"is_student":False,"projects_evaluation":"","hackathons_evaluation":"","research_evaluation":"","open_source_evaluation":""},
                resume_consistency={"summary_aligns_with_projects":True,"skills_align_with_projects":True,"projects_align_with_career_objective":True,"education_supports_domain":True,"dates_consistent":True,"no_duplicates":True,"technologies_consistent":True},
                ats_analysis={"ats_score":0,"formatting":"","keyword_coverage":"","section_detection":"","date_formatting":"","bullet_quality":"","missing_keywords":[],"parseability":"","recommendations":[]},
                technical_risks=[], predicted_questions=[]
            ),
        graph=KnowledgeGraph(nodes=[], edges=[])
    )
    plan = InterviewPlan(sections=[], total_estimated_turns=0, scoring_criteria=[])
    return InterviewState(
        session_id="test",
        resume=resume,
        plan=plan,
        transcript=[],
        performance_notes=[],
        current_difficulty=Difficulty.medium,
        turn_count=0
    )

def test_strong_candidate(mock_state):
    # Medium -> Strong -> Hard (Target: Hard)
    eval = create_eval(AnswerQuality.strong)
    new_diff, _ = next_difficulty(Difficulty.medium, eval, Difficulty.hard, mock_state)
    assert new_diff == Difficulty.hard

def test_average_candidate(mock_state):
    # Medium -> Adequate -> Medium
    eval = create_eval(AnswerQuality.adequate)
    new_diff, _ = next_difficulty(Difficulty.medium, eval, Difficulty.hard, mock_state)
    assert new_diff == Difficulty.medium

def test_struggling_candidate(mock_state):
    # Medium -> Weak -> Easy
    eval = create_eval(AnswerQuality.weak)
    new_diff, _ = next_difficulty(Difficulty.medium, eval, Difficulty.hard, mock_state)
    assert new_diff == Difficulty.easy

def test_alternating_performance_anti_oscillation(mock_state):
    # Simulate a drop from Medium to Easy in history
    mock_state.performance_notes.append(PerformanceNote(topic="t", difficulty=Difficulty.medium, evaluation=create_eval(AnswerQuality.weak)))
    mock_state.performance_notes.append(PerformanceNote(topic="t", difficulty=Difficulty.easy, evaluation=create_eval(AnswerQuality.strong)))
    
    # Normally, strong from easy would go to medium. But because we just dropped from medium to easy,
    # anti-oscillation should hold us at Easy.
    eval = create_eval(AnswerQuality.strong)
    new_diff, _ = next_difficulty(Difficulty.easy, eval, Difficulty.hard, mock_state)
    assert new_diff == Difficulty.easy

def test_section_target_cap(mock_state):
    # Easy -> Strong -> Medium (Target: Easy)
    # The cap should prevent exceeding target_difficulty + 1, so easy + 1 = medium.
    # If target is easy, we can reach medium. If target is easy, we cannot reach hard.
    eval = create_eval(AnswerQuality.strong)
    # If current is medium and target is easy, it shouldn't increase.
    new_diff, _ = next_difficulty(Difficulty.medium, eval, Difficulty.easy, mock_state)
    assert new_diff == Difficulty.medium

def test_maximum_difficulty(mock_state):
    # Hard -> Strong -> stays Hard
    eval = create_eval(AnswerQuality.strong)
    new_diff, _ = next_difficulty(Difficulty.hard, eval, Difficulty.hard, mock_state)
    assert new_diff == Difficulty.hard

def test_minimum_difficulty(mock_state):
    # Easy -> Weak -> stays Easy
    eval = create_eval(AnswerQuality.weak)
    new_diff, _ = next_difficulty(Difficulty.easy, eval, Difficulty.hard, mock_state)
    assert new_diff == Difficulty.easy
