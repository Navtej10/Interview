import os
import glob
import re

mock_analysis_str = """ResumeAnalysis(
                candidate_profile={"career_stage":"","primary_domain":"","secondary_domain":"","technical_maturity":"","experience_level":"","interview_readiness":"","resume_quality":"","overall_recommendation":""},
                scores={"overall_resume":{"title":"","score":0,"reason":""},"ats_compatibility":{"title":"","score":0,"reason":""},"technical_skills":{"title":"","score":0,"reason":""},"project_quality":{"title":"","score":0,"reason":""},"resume_writing":{"title":"","score":0,"reason":""},"interview_readiness":{"title":"","score":0,"reason":""},"confidence_score":{"title":"","score":0,"reason":""}},
                summary="A test candidate", gaps=[], strengths=[], skill_matrix=[], project_reviews=[],
                experience_review={"is_student":False,"projects_evaluation":"","hackathons_evaluation":"","research_evaluation":"","open_source_evaluation":""},
                resume_consistency={"summary_aligns_with_projects":True,"skills_align_with_projects":True,"projects_align_with_career_objective":True,"education_supports_domain":True,"dates_consistent":True,"no_duplicates":True,"technologies_consistent":True},
                ats_analysis={"ats_score":0,"formatting":"","keyword_coverage":"","section_detection":"","date_formatting":"","bullet_quality":"","missing_keywords":[],"parseability":"","recommendations":[]},
                technical_risks=[], predicted_questions=[]
            )"""

# Find all test files
for filepath in glob.glob(r'd:\Navtej\Interview\backend\tests\test_*.py'):
    with open(filepath, 'r') as f:
        content = f.read()

    # We need to replace all instances of ResumeAnalysis(...) with our mock_analysis_str
    # BUT only if it is the old short version. We'll use regex.
    # The old version is something like:
    # ResumeAnalysis(summary="...", gaps=[], strengths=[], ats_issues=[])
    
    # We will use a regex to match ResumeAnalysis( ... ) that DOES NOT contain candidate_profile
    new_content = re.sub(
        r'ResumeAnalysis\(\s*summary=[^)]+?\)',
        mock_analysis_str.replace("A test candidate", "\\1") if False else mock_analysis_str,
        content,
        flags=re.DOTALL
    )
    
    # Another pattern: ResumeAnalysis(...) where it doesn't match the above but is short
    new_content = re.sub(
        r'ResumeAnalysis\([^)]*summary=[^)]*\)',
        mock_analysis_str,
        new_content,
        flags=re.DOTALL
    )

    if new_content != content:
        with open(filepath, 'w') as f:
            f.write(new_content)
        print(f"Updated {filepath}")
