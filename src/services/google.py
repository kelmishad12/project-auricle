from typing import Protocol, List, Dict, Any

# --- Protocols (Interfaces) ---

class MailProvider(Protocol):
    """Abstract protocol for Mail Provider."""
    async def get_recent_emails(self, limit: int = 10) -> List[Dict[str, Any]]: ...
    async def send_email(self, to: str, subject: str, body: str) -> bool: ...

class CalendarProvider(Protocol):
    """Abstract protocol for Calendar Provider."""
    async def get_upcoming_events(self, days: int = 1) -> List[Dict[str, Any]]: ...

# --- Google Service Factories ---

def getGmailService(credentials_path: str = None):
    """
    Setup Google Auth and get Gmail Service.
    Currently a stub to be implemented with google-api-python-client.
    """
    print("[AUTH] Setting up Gmail Service...")
    # TODO: implement google.oauth2 credentials loading and service build
    # return build('gmail', 'v1', credentials=creds)
    pass

def getCalendarService(credentials_path: str = None):
    """
    Setup Google Auth and get Calendar Service.
    Currently a stub to be implemented with google-api-python-client.
    """
    print("[AUTH] Setting up Calendar Service...")
    # TODO: implement google.oauth2 credentials loading and service build
    # return build('calendar', 'v3', credentials=creds)
    pass
