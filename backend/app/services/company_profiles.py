import json
import os
import logging
from typing import Optional
from app.models.schemas import CompanyStyleProfile

logger = logging.getLogger(__name__)

# Cache profiles in memory after first load
_PROFILES_CACHE: dict[str, CompanyStyleProfile] = {}

def _load_profiles():
    if _PROFILES_CACHE:
        return

    json_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'company_style_profiles.json')
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for item in data:
                profile = CompanyStyleProfile(**item)
                _PROFILES_CACHE[profile.company.lower()] = profile
    except Exception as e:
        logger.error(f"Failed to load company profiles from {json_path}: {e}")

def get_company_profile(company_name: str) -> Optional[CompanyStyleProfile]:
    """
    Retrieve a company profile by name. Falls back to 'generic_faang' if not found,
    or 'default' if generic_faang is also missing.
    """
    _load_profiles()
    
    if not company_name:
        return _PROFILES_CACHE.get('default')

    normalized_name = company_name.lower().strip()
    profile = _PROFILES_CACHE.get(normalized_name)
    
    if profile:
        return profile
        
    logger.warning(f"Company profile '{company_name}' not found. Falling back to generic_faang.")
    return _PROFILES_CACHE.get('generic_faang') or _PROFILES_CACHE.get('default')

def get_all_companies() -> list[CompanyStyleProfile]:
    """Returns a list of all loaded company profiles."""
    _load_profiles()
    return list(_PROFILES_CACHE.values())
