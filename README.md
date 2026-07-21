# InterviewAI

Scaffold for the resume-grounded adaptive interview platform. Modules map
directly to your build order:

1. **Resume Parser** — `backend/app/services/resume_parser.py`
   Working. Pure structured extraction (PDF + DOCX): skills, projects,
   experience, education, certifications, achievements. No judgment.

2. **Resume Analysis Engine** — `backend/app/services/resume_analysis.py`
   Working. Takes the parsed resume and judges it: gaps, unsupported
   claims, ATS issues, formatting problems, suggestions.

3. **Resume Knowledge Graph** — `backend/app/services/knowledge_graph.py`
   Working, and deliberately deterministic (no LLM call) — links
   projects/experience/technologies/skills. Gives you `unsupported_skills()`
   for free: skills claimed with no project/experience backing.

4. **Resume-Based Question Generator** — `backend/app/services/question_generator.py`
   Working. Generates the opening question, grounded in the resume AND the
   Interview Planner's first section (see below).

5. **Interview Planner** — `backend/app/services/planner.py`
   Working. Generates the interview blueprint once, at session start:
   sections with objectives/target topics/target difficulty/estimated
   turns, plus scoring criteria. `section_for_question_index()` is the
   deterministic helper that maps "which question number are we on" to
   "which section are we in" — no LLM call needed for that part.

6. **Adaptive interview loop (Conversation Engine)** — `backend/app/services/interview_engine.py`
   **The core of the product.** Working end-to-end via the text-mode UI
   (`InterviewSession.tsx`), and now plan-aware: every turn is told its
   current section's objective/target topics, and steers toward it while
   still adapting difficulty within the section based on how the candidate
   is actually doing. Read the docstring at the top of that file before
   modifying.

7. **Feedback** — `backend/app/services/feedback_service.py`
   Working. Written report is a single structured call. Live debrief reuses
   the conversational pattern from the interview loop.

8. **Voice + avatar** — `backend/app/services/tts_service.py` and
   `avatar_service.py` are stubs. Wire in your existing edge-tts +
   LivePortrait pipeline here — the signatures are deliberately simple
   (text/audio path in, file path out) so nothing else has to change.

**Not yet built** (next in your list): Conversation Memory, Interview
State Machine, Follow-Up Generator, and Adaptive Difficulty Engine are
currently folded into the Conversation Engine's single prompt (transcript
= memory, turn_count/section = state machine, the deepen/pivot/simplify/
follow_up strategy = follow-up + adaptive difficulty). That's fine for now
— splitting them into standalone modules is worth doing once you've run
real interviews and know which of those concerns actually needs to be more
sophisticated than "one LLM call with the full transcript." Interview
Orchestrator, Speech Pipeline streaming, Behavior & Emotion Engine, and
Feedback & Scoring Engine (structured scoring against the planner's
criteria) are also still ahead.

## Why it's built this way

The whole point of doing it in this order: layers 1-4 are pure text
in/text out, so you can build and debug the actual interview intelligence
using the browser text-mode UI, with no audio latency or lip-sync
debugging in the loop. Once the conversation itself feels right, layer 5
is a relatively mechanical wiring exercise on top of something that
already works.

## Running it

**Backend**
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in ANTHROPIC_API_KEY, or switch LLM_PROVIDER=ollama
uvicorn app.main:app --reload
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — upload a resume (PDF or .txt), review the gap
analysis, run the text-mode interview, then pick a feedback mode.

## What's stubbed vs. real

- Real: resume parsing, resume analysis, the knowledge graph, question
  generation, the interview planner, the adaptive loop, both feedback
  modes — all as actual LLM calls (or, for the graph, deterministic code),
  not mocked responses.
- Stubbed: TTS and avatar rendering — raise `NotImplementedError` until you
  wire in your existing pipeline.
- Session storage is in-memory (`session_store.py`) — fine for local dev,
  swap for Redis before multi-user/production use.

## Known gaps to fix before this is real

- No auth / user accounts.
- No persistence beyond the process lifetime (sessions vanish on restart).
- No streaming — turns wait for the full LLM response. Fine for text mode;
  once voice is wired in you'll want to look at streaming responses to
  keep latency down.
- Frontend styling is intentionally bare — functional over the wire, not
  designed. Worth a real pass once the flow is validated.
