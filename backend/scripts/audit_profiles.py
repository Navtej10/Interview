import json
import os
from datetime import datetime

def audit_profiles():
    filepath = os.path.join(os.path.dirname(__file__), '..', 'app', 'data', 'company_style_profiles.json')
    
    with open(filepath, 'r', encoding='utf-8') as f:
        profiles = json.load(f)
        
    print(f"{'Company':<20} | {'Version':<10} | {'Last Reviewed':<15} | {'Notes'}")
    print("-" * 80)
    
    # Sort profiles by last_reviewed ascending (oldest first)
    sorted_profiles = sorted(
        profiles, 
        key=lambda x: datetime.strptime(x.get('last_reviewed', '1970-01-01'), '%Y-%m-%d')
    )
    
    for p in sorted_profiles:
        company = p.get('company', 'Unknown')
        version = p.get('profile_version', 'N/A')
        last_rev = p.get('last_reviewed', 'N/A')
        notes = p.get('review_notes', '')
        
        # truncate notes for display
        if len(notes) > 30:
            notes = notes[:27] + "..."
            
        print(f"{company:<20} | {version:<10} | {last_rev:<15} | {notes}")

if __name__ == '__main__':
    audit_profiles()
