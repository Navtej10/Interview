import asyncio
import websockets
import requests
import json
import uuid

async def test_ws():
    # 1. Start interview
    resume = {
        "parsed": {
            "raw_text": "text",
            "skills": [],
            "projects": [],
            "experience": [],
            "education": [],
            "certifications": [],
            "achievements": [],
            "low_confidence": False,
            "parse_quality_notes": []
        },
        "analysis": {
            "candidate_profile": {
                "career_stage": "entry",
                "primary_domain": "sw",
                "secondary_domain": "web",
                "technical_maturity": "low",
                "experience_level": "low",
                "interview_readiness": "ready",
                "resume_quality": "good",
                "overall_recommendation": "hire"
            },
            "scores": {
                "overall_resume": {"title": "x", "score": 10, "reason": "y"},
                "ats_compatibility": {"title": "x", "score": 10, "reason": "y"},
                "technical_skills": {"title": "x", "score": 10, "reason": "y"},
                "project_quality": {"title": "x", "score": 10, "reason": "y"},
                "resume_writing": {"title": "x", "score": 10, "reason": "y"},
                "interview_readiness": {"title": "x", "score": 10, "reason": "y"},
                "confidence_score": {"title": "x", "score": 10, "reason": "y"}
            },
            "summary": "x",
            "strengths": [],
            "skill_matrix": [],
            "project_reviews": [],
            "experience_review": {
                "is_student": False,
                "projects_evaluation": "x",
                "hackathons_evaluation": "x",
                "research_evaluation": "x",
                "open_source_evaluation": "x",
                "work_experience_evaluation": "x"
            },
            "resume_consistency": {
                "summary_aligns_with_projects": True,
                "skills_align_with_projects": True,
                "projects_align_with_career_objective": True,
                "education_supports_domain": True,
                "dates_consistent": True,
                "no_duplicates": True,
                "technologies_consistent": True
            },
            "ats_analysis": {
                "ats_score": 100,
                "formatting": "good",
                "keyword_coverage": "good",
                "section_detection": "good",
                "date_formatting": "good",
                "bullet_quality": "good",
                "missing_keywords": [],
                "parseability": "good",
                "recommendations": []
            },
            "technical_risks": [],
            "predicted_questions": [],
            "gaps": [],
            "final_recommendation": "x"
        },
        "graph": {"nodes": [], "edges": []}
    }
    resp = requests.post("http://localhost:8000/interview/start", json={"resume": resume})
    if resp.status_code != 200:
        print("Start failed:", resp.text)
        return
    session_id = resp.json()["session_id"]
    print("Started session:", session_id)
    
    # 2. Connect to WS
    ws_url = f"ws://localhost:8000/interview/voice_turn/{session_id}"
    print("Connecting to", ws_url)
    async with websockets.connect(ws_url) as ws:
        print("Connected!")
        # Wait for messages
        while True:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=20.0)
                if isinstance(msg, bytes):
                    print(f"Received bytes of length {len(msg)}")
                else:
                    print("Received text:", msg)
            except asyncio.TimeoutError:
                print("Timeout waiting for message")
                break
            except Exception as e:
                print("Error:", e)
                break

asyncio.run(test_ws())
