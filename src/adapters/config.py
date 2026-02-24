"""
Configuration adapter for dependency injection.
"""
from typing import Dict, Any

from src.adapters.google_workspace import GoogleWorkspaceAdapter
# pylint: disable=import-error
from src.adapters.localmock import MockMailAdapter, MockCalendarAdapter

def get_providers(env: str = "dev") -> Dict[str, Any]:
    """
    Dependency Injection wiring.
    Return configured providers based on the targeted environment.
    """
    if env == "prod":
        return {
            "mail_provider": GoogleWorkspaceAdapter(),
            # "cal_provider": GoogleWorkspaceAdapter() # Will be implemented later in same file
            "cal_provider": MockCalendarAdapter() 
        }

    # Default to dev environment -> Local mocks
    return {
        "mail_provider": MockMailAdapter(),
        "cal_provider": MockCalendarAdapter()
    }
