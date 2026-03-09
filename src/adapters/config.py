"""
Configuration adapter for dependency injection.
"""
from typing import Dict, Any

from src.services.google import GoogleWorkspaceService
# pylint: disable=import-error,no-name-in-module
from src.adapters.localmock import MockCalendarAdapter, MockMailAdapter

def get_providers(env: str = "dev") -> Dict[str, Any]:
    """
    Dependency Injection wiring.
    Return configured providers based on the targeted environment.
    """
    if env == "prod":
        adapter = GoogleWorkspaceService()
        return {
            "mail_provider": adapter,
            "cal_provider": adapter
        }

    # Default to dev environment -> Local mocks
    return {
        "mail_provider": MockMailAdapter(),
        "cal_provider": MockCalendarAdapter()
    }
