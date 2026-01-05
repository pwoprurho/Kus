import os
import json
import datetime
from typing import Dict, Any, Optional

# Try to import Google API client libraries; if unavailable we'll fall back to a simulator
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    GOOGLE_AVAILABLE = True
except Exception:
    GOOGLE_AVAILABLE = False


def create_calendar_event(event: Dict[str, Any], calendar_id: str = 'primary') -> Dict[str, Any]:
    """Create an event in Google Calendar using a service account JSON payload.

    - If `GOOGLE_SERVICE_ACCOUNT_JSON` env var is present it should contain the
      JSON credentials for a service account with domain-wide calendar access
      (or a calendar shared to the service account).
    - If Google libraries or credentials are missing, returns a simulated result
      describing what would have been done.

    event: dict with keys like 'summary', 'start', 'end', 'description', 'attendees'
    calendar_id: calendar identifier (default: 'primary')
    """
    # Minimal normalization
    evt = dict(event) if isinstance(event, dict) else {'summary': str(event)}

    if not GOOGLE_AVAILABLE:
        return {
            'status': 'SIMULATED',
            'message': 'google-api-python-client not available in environment',
            'event_preview': evt,
            'created_at': datetime.datetime.utcnow().isoformat()
        }

    # Credential getter: either from file path env var or entire JSON in env var
    sa_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON_FILE') or os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
    if not sa_json:
        return {
            'status': 'SIMULATED',
            'message': 'No service account credentials provided (GOOGLE_SERVICE_ACCOUNT_JSON[_FILE])',
            'event_preview': evt,
            'created_at': datetime.datetime.utcnow().isoformat()
        }

    credentials = None
    try:
        if os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON_FILE'):
            credentials = service_account.Credentials.from_service_account_file(sa_json, scopes=['https://www.googleapis.com/auth/calendar'])
        else:
            info = json.loads(sa_json)
            credentials = service_account.Credentials.from_service_account_info(info, scopes=['https://www.googleapis.com/auth/calendar'])
    except Exception as e:
        return {
            'status': 'SIMULATED',
            'message': f'Credentials parse error: {str(e)}',
            'event_preview': evt,
            'created_at': datetime.datetime.utcnow().isoformat()
        }

    try:
        service = build('calendar', 'v3', credentials=credentials, cache_discovery=False)
        created = service.events().insert(calendarId=calendar_id, body=evt).execute()
        return {'status': 'CREATED', 'event': created}
    except Exception as e:
        return {'status': 'FAILED', 'error': str(e), 'event_preview': evt}
