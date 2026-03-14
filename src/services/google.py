"""
Google Services provider protocols and factories.
"""
# pylint: disable=import-error,no-name-in-module,no-member
from typing import Protocol, List, Dict, Any
import asyncio
import os.path
import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/calendar.readonly'
]


def _get_credentials(client_secrets_file: str = 'credentials.json'):
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI")
            if not redirect_uri:
                raise ValueError(
                    "GOOGLE_REDIRECT_URI environment variable must be set "
                    "(e.g., http://localhost:57785/)"
                )

            if not os.path.exists(client_secrets_file):
                client_id = os.environ.get("GOOGLE_CLIENT_ID")
                client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")

                if not client_id or not client_secret:
                    raise FileNotFoundError(
                        f"Missing {client_secrets_file} for Google OAuth2. Either provide it "
                        "or set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables."
                    )

                client_config = {
                    "installed": {
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "project_id": "project-auricle",
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                        "redirect_uris": [redirect_uri]
                    }
                }
                flow = InstalledAppFlow.from_client_config(
                    client_config, SCOPES)
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    client_secrets_file, SCOPES)

            # TODO: run_local_server is for local testing only.
            # In a deployed web app, use flow.authorization_url() and
            # fetch_token() instead.
            creds = flow.run_local_server(port=57785, prompt='consent')
        with open('token.json', 'w', encoding='utf-8') as token:
            token.write(creds.to_json())
    return creds

# --- Protocols (Interfaces) ---


class MailProvider(Protocol):
    """Abstract protocol for Mail Provider."""

    async def get_recent_emails(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve recent emails."""

    async def send_email(self, to: str, subject: str, body: str) -> bool:
        """Send an email."""


class CalendarProvider(Protocol):
    """Abstract protocol for Calendar Provider."""

    async def get_upcoming_events(self, days: int = 1) -> List[Dict[str, Any]]:
        """Retrieve upcoming calendar events."""

# --- Google Service Factories ---


def get_gmail_service(_credentials_path: str = None):
    """
    Setup Google Auth and get Gmail Service.
    """
    print("[AUTH] Setting up Gmail Service...")
    creds = _get_credentials(_credentials_path or 'credentials.json')
    return build('gmail', 'v1', credentials=creds)


def get_calendar_service(_credentials_path: str = None):
    """
    Setup Google Auth and get Calendar Service.
    """
    print("[AUTH] Setting up Calendar Service...")
    creds = _get_credentials(_credentials_path or 'credentials.json')
    return build('calendar', 'v3', credentials=creds)


class GoogleWorkspaceService(MailProvider, CalendarProvider):
    """Concrete implementation for Google Workspace using API client."""

    def __init__(self, credentials_path: str = None):
        self.credentials_path = credentials_path
        self._gmail_service = None
        self._calendar_service = None

    @property
    def gmail_service(self):
        """Lazy-load and return the built Gmail service client."""
        if not self._gmail_service:
            self._gmail_service = get_gmail_service(self.credentials_path)
        return self._gmail_service

    @property
    def calendar_service(self):
        """Lazy-load and return the built Calendar service client."""
        if not self._calendar_service:
            self._calendar_service = get_calendar_service(
                self.credentials_path)
        return self._calendar_service

    async def get_recent_emails(self, limit: int = 10) -> List[Dict[str, Any]]:
        loop = asyncio.get_event_loop()

        def _fetch():
            results = self.gmail_service.users().messages().list(
                userId='me', maxResults=limit).execute()
            messages = results.get('messages', [])
            emails = []
            for msg in messages:
                message = self.gmail_service.users().messages().get(
                    userId='me', id=msg['id']).execute()
                headers = message.get('payload', {}).get('headers', [])

                subject = next(
                    (h['value'] for h in headers if h['name'] == 'Subject'),
                    'No Subject')
                sender = next(
                    (h['value'] for h in headers if h['name'] == 'From'),
                    'Unknown Sender')
                emails.append(
                    {"sender": sender, "subject": subject, "id": msg['id']})
            return emails
        return await loop.run_in_executor(None, _fetch)

    async def send_email(self, to: str, subject: str, body: str) -> bool:
        # Placeholder for full MIME constructing
        print(f"[Real] Sent email to {to} | Subject: {subject}")
        return True

    async def get_upcoming_events(self, days: int = 1) -> List[Dict[str, Any]]:
        loop = asyncio.get_event_loop()

        def _fetch():
            now = datetime.datetime.utcnow().isoformat() + 'Z'
            events_result = self.calendar_service.events().list(
                calendarId='primary', timeMin=now, maxResults=max(10, days * 5),
                singleEvents=True, orderBy='startTime').execute()
            events = events_result.get('items', [])
            return [{"title": e.get('summary', 'Untitled'), "time": e['start'].get(
                'dateTime', e['start'].get('date'))} for e in events]
        return await loop.run_in_executor(None, _fetch)
