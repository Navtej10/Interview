import json
import datetime

filepath = 'd:/Navtej/Interview/backend/app/data/company_style_profiles.json'
with open(filepath, 'r', encoding='utf-8') as f:
    profiles = json.load(f)

for p in profiles:
    # Seniority Modifiers
    p['seniority_modifiers'] = {
        'entry': {
            'question_mix_shift': { 'technical': 0.05, 'case_or_system_design': -0.10, 'behavioral': 0.05 },
            'difficulty_start': 'baseline',
            'evaluation_emphasis': ['Problem Solving', 'Fundamentals', 'Learning Ability']
        },
        'mid': {
            'question_mix_shift': { },
            'difficulty_start': 'moderate',
            'evaluation_emphasis': []
        },
        'senior': {
            'question_mix_shift': { 'case_or_system_design': 0.10, 'behavioral': 0.05, 'technical': -0.15 },
            'difficulty_start': 'elevated',
            'evaluation_emphasis': ['Ownership', 'Cross-team Influence', 'Architectural Judgment']
        },
        'staff_plus': {
            'question_mix_shift': { 'case_or_system_design': 0.20, 'technical': -0.25, 'behavioral': 0.05 },
            'difficulty_start': 'elevated',
            'evaluation_emphasis': ['Strategic Impact', 'Org-level Influence', 'Ambiguity Navigation']
        }
    }
    
    # Vocabulary Cues
    if p['company'].lower() == 'amazon':
        p['vocabulary_cues'] = {
            'phrases': ['Tell me about a time you had to dive deep into...', 'What was your bar for success there?', 'Walk me through the trade-off you made and why.', 'What would you have done differently, looking back?'],
            'avoid': ['casual/slangy phrasing that undercuts the rubric-driven tone', 'vague praise without following up for specifics']
        }
    elif p['company'].lower() == 'google':
        p['vocabulary_cues'] = {
            'phrases': ['How does this scale to millions of users?', 'What edge cases did you consider?', 'Tell me how you would design...', 'How did you navigate that ambiguity?'],
            'avoid': ['overly rigid corporate speak', 'focusing solely on past behavior without hypothetical scaling questions']
        }
    elif p['company'].lower() == 'meta':
        p['vocabulary_cues'] = {
            'phrases': ['How fast can we ship this?', 'What is the most efficient way to build this?', 'How did you handle the engineering trade-offs?', 'Walk me through the fastest working solution.'],
            'avoid': ['spending too much time on abstract architectural perfection', 'ignoring execution speed']
        }
    elif p['company'].lower() == 'apple':
        p['vocabulary_cues'] = {
            'phrases': ['How did you ensure the highest quality user experience?', 'Walk me through the lowest-level details of that implementation.', 'Why did you choose that specific design over the alternatives?', 'Tell me about a time you obsessed over the details.'],
            'avoid': ['rushing past design and polish', 'accepting "good enough" answers']
        }
    elif p['company'].lower() == 'microsoft':
        p['vocabulary_cues'] = {
            'phrases': ['How did you ensure the system was resilient?', 'Tell me how you collaborated across teams to build this.', 'Walk me through the system architecture.', 'How did you handle backward compatibility?'],
            'avoid': ['discouraging cross-team collaboration', 'ignoring legacy constraints']
        }
    else:
        p['vocabulary_cues'] = {
            'phrases': ['Tell me about your experience with...', 'Walk me through your design process.', 'What were the main challenges?', 'How did you solve that?'],
            'avoid': ['using overly specific company jargon', 'being excessively abrasive']
        }
        
    # Disclaimer
    if p['company'].lower() == 'generic faang':
        p['disclaimer'] = 'A composite style based on commonly reported big-tech interview patterns — not modeled on any single company.'
    elif p['company'].lower() == 'default ai interviewer':
        p['disclaimer'] = 'InterviewAI\'s standard interview style.'
    else:
        p['disclaimer'] = f"Styled after publicly known {p['company']} interview patterns — not an official, affiliated, or verified simulation of {p['company']}'s actual interview process."
        
    # Versioning
    p['profile_version'] = '1.1.0'
    p['last_reviewed'] = datetime.datetime.now().strftime('%Y-%m-%d')
    p['review_notes'] = 'Added seniority modifiers, vocabulary cues, and disclaimers. Audited closing_style.'
    
    # Audit Closing Style
    p['closing_style'] = 'Conclude the interview neutrally. Summarize briefly if needed, thank the candidate for their time, and offer a brief moment for them to ask any final questions.'

with open(filepath, 'w', encoding='utf-8') as f:
    json.dump(profiles, f, indent=2)

print('JSON updated.')
