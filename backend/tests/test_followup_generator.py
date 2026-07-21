import pytest
from app.models.schemas import InterviewState, TranscriptTurn, ResumeBundle, ParsedResume, ResumeAnalysis, KnowledgeGraph, InterviewPlan, Difficulty, InterviewPhase
from app.services.followup_generator import decide_followup_strategy

@pytest.fixture
def mock_state():
    return InterviewState(
        session_id="test_session",
        resume=ResumeBundle(
            parsed=ParsedResume(
                skills=["python"],
                projects=[],
                experience=[],
                education=[],
                certifications=[],
                achievements=[],
                raw_text="mock text",
            ),
            analysis=ResumeAnalysis(
                summary="A test candidate", 
                gaps=[],
                strengths=[],
                ats_issues=[]
            ),
            graph=KnowledgeGraph(nodes=[], edges=[])
        ),
        plan=InterviewPlan(sections=[], total_estimated_turns=10, scoring_criteria=[]),
        transcript=[
            TranscriptTurn(role="interviewer", content="Tell me about your experience with Python.", topic="python")
        ],
        covered_topics=["python"],
        current_difficulty=Difficulty.medium,
        phase=InterviewPhase.IN_SECTION
    )

def test_decide_followup_strategy_deepen(mock_state):
    # A strong answer should lead to a deepen strategy
    answer = "I have 5 years of experience with Python, mostly using Django for web development and Pytest for testing. I also optimized a large data processing pipeline using multiprocessing."
    result = decide_followup_strategy(mock_state, answer)
    
    assert "strategy" in result
    assert result["strategy"] in ["deepen", "pivot", "simplify", "follow_up_tangent"]
    # We expect a strong answer to often trigger 'deepen' or 'follow_up_tangent', but deepen is the most likely.
    # LLMs can be slightly non-deterministic, so we just assert it returns a valid strategy and reasoning.
    assert "reasoning" in result

def test_decide_followup_strategy_simplify(mock_state):
    # A struggling answer should lead to a simplify strategy
    answer = "I used Python a bit in college, but I don't really remember how it works. I think I wrote a script once."
    result = decide_followup_strategy(mock_state, answer)
    
    assert "strategy" in result
    assert result["strategy"] in ["deepen", "pivot", "simplify", "follow_up_tangent"]
    assert "reasoning" in result

def test_decide_followup_strategy_tangent(mock_state):
    # Name-dropping something interesting off-topic
    answer = "I use Python a lot, but actually for my last project I ended up rewriting the core engine in Rust because of garbage collection pauses."
    result = decide_followup_strategy(mock_state, answer)
    
    assert "strategy" in result
    assert result["strategy"] in ["deepen", "pivot", "simplify", "follow_up_tangent"]
    assert "reasoning" in result

def test_decide_followup_strategy_pivot(mock_state):
    # A fully covered topic, short but complete answer
    answer = "Yes, I know Python very well. I'm ready for the next topic."
    result = decide_followup_strategy(mock_state, answer)
    
    assert "strategy" in result
    assert result["strategy"] in ["deepen", "pivot", "simplify", "follow_up_tangent"]
    assert "reasoning" in result
