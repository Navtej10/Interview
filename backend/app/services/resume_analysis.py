"""
Module 2: Resume Analysis Engine — takes a ParsedResume and passes judgment:
weaknesses, missing details, unsupported claims, ATS issues, formatting
problems, improvement suggestions. Deliberately separate from parsing
(module 1) so extraction stays factual and analysis stays opinionated —
you'll want to tune/re-prompt these independently.

This is a *hybrid* module: the LLM provides judgment-heavy analysis, and
a deterministic cross-check via KnowledgeGraph.unsupported_skills() catches
any claimed-but-undemonstrated skills the LLM overlooked.
"""

from app.services.llm_client import llm
from app.models.schemas import (
    ParsedResume, ResumeAnalysis, ResumeGap, KnowledgeGraph, Severity,
)

SYSTEM_PROMPT = """\
You are an experienced Senior Engineering Manager, Technical Interviewer, Recruiter, ATS Reviewer, and Resume Coach.

You are NOT parsing a resume.

You are reviewing already extracted structured resume information.

Your job is to evaluate the candidate exactly like an interviewer preparing for a technical interview.

Never invent information.

Never assume something happened unless supported by the extracted data.

Always distinguish between

• Explicit Evidence
• Supporting Evidence
• Weak Evidence
• Missing Evidence

----------------------------------

Evaluate the following areas.

1. Candidate Profile

Determine

- Career Stage
- Primary Domain
- Secondary Domain
- Overall Technical Maturity
- Interview Readiness
- Resume Quality

----------------------------------

2. Resume Scores

Generate scores from 0-100.

Overall Resume Score

ATS Compatibility

Technical Strength

Project Quality

Resume Writing

Interview Readiness

Confidence Score

Explain each score briefly.

----------------------------------

3. Strength Analysis

Identify

Top Technical Strengths

Top Soft Strengths

Strongest Technologies

Strongest Projects

Strongest Domain

Rank strengths from strongest to weakest.

----------------------------------

4. Skill Evidence Analysis

Every skill belongs to exactly one category.

HIGH CONFIDENCE

Demonstrated repeatedly through

Experience

Projects

Research

Open Source

Internships

MEDIUM CONFIDENCE

Supported by

Certifications

Coursework

Hackathons

LOW CONFIDENCE

Mentioned only once

UNVERIFIED

Listed without any supporting evidence.

Do NOT mark coursework or certifications as unsupported.

They count as supporting evidence.

----------------------------------

5. Project Analysis

Evaluate every project.

Provide

Complexity

Innovation

Technical Depth

Resume Description Quality

Architecture Clarity

Problem Solving

Evidence of Ownership

Role Clarity

Impact

Metrics

Missing Information

Improvement Suggestions

----------------------------------

6. Experience Analysis

If no work experience exists

Recognize that the candidate is a student.

Do NOT criticize missing industry experience.

Instead evaluate

Hackathons

Personal Projects

Open Source

Research

----------------------------------

7. Resume Consistency

Check

Summary matches projects

Projects support skills

Skills support career objective

Education supports domain

Dates consistent

Technologies consistent

No duplicated information

----------------------------------

8. ATS Analysis

Evaluate

Formatting

Section headings

Date consistency

Keyword coverage

Missing keywords

Parseability

Bullet quality

Contact information

----------------------------------

9. Technical Interview Risk

For every technology determine

High Risk

Medium Risk

Low Risk

Risk depends on

Evidence quality

Project depth

Repeated usage

----------------------------------

10. Interview Question Prediction

Generate likely interview questions based on

Projects

Skills

Technologies

Certifications

Coursework

Generate

Basic

Intermediate

Advanced

Behavioral

----------------------------------

11. Gap Analysis

Only identify genuine weaknesses.

Never create fake issues.

Student resumes should NOT be penalized for

Missing company experience

Missing production systems

Missing business metrics

Instead focus on

Missing role descriptions

Missing architecture

Missing impact

Missing measurable outcomes

Weak project explanations

Weak ownership

----------------------------------

12. Growth Roadmap

Prioritize improvements.

High Priority

Medium Priority

Low Priority

Every recommendation should be actionable.

----------------------------------

Return JSON only.

Never produce markdown.

Never produce explanations outside JSON.

CRITICAL: Keep all string descriptions extremely concise (1-2 sentences maximum) and limit arrays to top items to save tokens.


Return JSON exactly matching the ResumeAnalysis schema structure:
{
  "candidate_profile": { "career_stage": "", "primary_domain": "", "secondary_domain": "", "technical_maturity": "", "experience_level": "", "interview_readiness": "", "resume_quality": "", "overall_recommendation": "" },
  "scores": {
    "overall_resume": { "title": "Overall Resume", "score": 85, "reason": "" },
    "ats_compatibility": { "title": "ATS Compatibility", "score": 85, "reason": "" },
    "technical_skills": { "title": "Technical Skills", "score": 85, "reason": "" },
    "project_quality": { "title": "Project Quality", "score": 85, "reason": "" },
    "resume_writing": { "title": "Resume Writing", "score": 85, "reason": "" },
    "interview_readiness": { "title": "Interview Readiness", "score": 85, "reason": "" },
    "confidence_score": { "title": "Confidence Score", "score": 85, "reason": "" }
  },
  "summary": "2-3 sentence overview of the candidate's background",
  "strengths": ["...", "..."],
  "skill_matrix": [
    { "skill": "Python", "confidence": "High", "evidence": "Experience", "reason": "", "confidence_score": 90 }
  ],
  "project_reviews": [
    {
      "name": "Project Name", "complexity": 8, "innovation": 7, "technical_depth": 8, "architecture": 7, "ownership": 9, "documentation": 6, "resume_quality": 8, "impact": 7, "role_clarity": 8, "metrics_present": true,
      "strengths": ["..."], "weaknesses": ["..."], "missing_information": ["..."], "improvements": ["..."], "likely_interview_questions": ["question 1", "question 2"]
    }
  ],
  "experience_review": {
    "is_student": true, "projects_evaluation": "", "hackathons_evaluation": "", "research_evaluation": "", "open_source_evaluation": "", "work_experience_evaluation": ""
  },
  "resume_consistency": {
    "summary_aligns_with_projects": true, "skills_align_with_projects": true, "projects_align_with_career_objective": true, "education_supports_domain": true, "dates_consistent": true, "no_duplicates": true, "technologies_consistent": true
  },
  "ats_analysis": {
    "ats_score": 80, "formatting": "", "keyword_coverage": "", "section_detection": "", "date_formatting": "", "bullet_quality": "", "missing_keywords": [], "parseability": "", "recommendations": []
  },
  "technical_risks": [
    { "technology": "Docker", "risk_level": "Medium", "reason": "", "suggested_preparation": "" }
  ],
  "predicted_questions": [
    { "question": "", "category": "Projects", "difficulty": "Medium", "reason": "", "triggered_by": "", "probability": 80 }
  ],
  "growth_roadmap": {
    "high_priority": [ { "recommendation": "", "priority": "High", "reason": "", "expected_impact": "", "estimated_effort": "" } ],
    "medium_priority": [],
    "low_priority": []
  },
  "gaps": [
    {"category": "vague_description|missing_metric|unsupported_skill|ats_issue|formatting",
     "location": "Experience > Acme Corp > bullet 2",
     "issue": "what's wrong",
     "suggestion": "how to fix it",
     "severity": "low|medium|high"}
  ],
  "final_recommendation": "3-5 sentence conclusion summarizing readiness, biggest strengths, weaknesses, and what to improve before the interview."
}
"""

SKILL_EVIDENCE_PROMPT = """\
Instead of binary supported/not supported, it classifies confidence.

For every extracted skill determine the strongest evidence.

Evidence Priority

Experience = 100

Internship = 95

Research = 90

Open Source = 90

Projects = 85

Hackathons = 70

Certifications = 60

Coursework = 55

Professional Summary = 20

Skills Section = 10

Classify each skill as

HIGH

MEDIUM

LOW

UNVERIFIED

Never classify coursework or certifications as unsupported.

Return

{
  "skill":"Python",
  "confidence":"Medium",
  "evidence":"Coursework",
  "score":60,
  "reason":"Appears in coursework but not demonstrated in projects."
}
"""

PROJECT_REVIEWER_PROMPT = """\
Instead of only checking for metrics, deeply analyze each project.

You are evaluating a software engineering project.

Rate from 1-10

Technical Complexity

Architecture

Scalability

Innovation

Engineering Practices

Ownership

Documentation

Resume Description

Interview Difficulty

For every project identify

What is excellent

What is missing

What interviewers will ask

How to improve the resume description

Never penalize student hackathon projects for lacking production metrics.

Instead evaluate relative to student level.
"""

RESUME_SCORING_PROMPT = """\
Generate the dashboard scores.

Generate the following scores.

Overall Resume

ATS Compatibility

Technical Skills

Project Quality

Resume Writing

Interview Readiness

Confidence

Explain every score in under 25 words.

Scoring should be conservative.

95+ only for exceptional resumes.

80-90 for strong student resumes.

65-80 for average student resumes.

Below 65 only if major issues exist.
"""

INTERVIEW_PREP_PROMPT = """\
This is where InterviewAI becomes unique.

After resume analysis, generate interview-specific guidance that feeds directly into your interview engine.

Based on this resume, predict what a technical interviewer will most likely ask.

Group questions into

Resume Walkthrough

Projects

Programming

Core CS

Behavioral

Situational

Domain Knowledge

Follow-up Questions

Difficulty

Easy

Medium

Hard

For every question provide

Why the interviewer asks it

Which resume section triggered it

Expected depth of answer

Estimated interview probability (0-100%)

Do not invent technologies.

Use only information present in the extracted resume.
"""


def _build_unsupported_skill_gaps(
    graph: KnowledgeGraph, llm_gaps: list[ResumeGap]
) -> list[ResumeGap]:
    """Deterministic cross-check: any skill that KnowledgeGraph flags as
    unsupported (claimed but never tied to a project/experience technology)
    that the LLM's gaps list didn't already cover gets appended."""
    # Collect skills the LLM already flagged as unsupported
    llm_flagged_skills: set[str] = set()
    for gap in llm_gaps:
        if gap.category == "unsupported_skill":
            # Extract skill name from location like "Skills > React"
            parts = gap.location.split(">")
            if len(parts) >= 2:
                llm_flagged_skills.add(parts[-1].strip().lower())

    extra_gaps: list[ResumeGap] = []
    for skill in graph.unsupported_skills():
        if skill.lower() not in llm_flagged_skills:
            extra_gaps.append(ResumeGap(
                category="unsupported_skill",
                location=f"Skills > {skill}",
                issue=(
                    f'"{skill}" is listed in skills but not mentioned in '
                    f"any project or experience technology list."
                ),
                suggestion=(
                    f"Either add a project/experience entry that demonstrates "
                    f'"{skill}", or remove it from skills to avoid interviewer '
                    f"scrutiny."
                ),
                severity=Severity.high,
            ))
    return extra_gaps


def analyze(parsed: ParsedResume, graph: KnowledgeGraph) -> ResumeAnalysis:
    """Hybrid analysis: LLM judgment + deterministic unsupported-skill check."""
    user = (
        f"Skills: {parsed.skills}\n\n"
        f"Projects: {[p.model_dump() for p in parsed.projects]}\n\n"
        f"Experience: {[e.model_dump() for e in parsed.experience]}\n\n"
        f"Education: {[e.model_dump() for e in parsed.education]}\n\n"
        f"Certifications: {parsed.certifications}\n"
        f"Achievements: {parsed.achievements}"
    )
    # Give the LLM plenty of tokens for this massive JSON output, but keep under 8000 TPM
    result = llm.complete_json(SYSTEM_PROMPT, user, max_tokens=5500)

    raw_gaps = result.get("gaps", [])
    for g in raw_gaps:
        if "severity" in g and isinstance(g["severity"], str):
            g["severity"] = g["severity"].lower()
    llm_gaps = [ResumeGap(**g) for g in raw_gaps]

    # Deterministic cross-check: append unsupported skills the LLM missed
    deterministic_gaps = _build_unsupported_skill_gaps(graph, llm_gaps)
    all_gaps = llm_gaps + deterministic_gaps
    
    result["gaps"] = [g.model_dump() for g in all_gaps]

    return ResumeAnalysis(**result)


