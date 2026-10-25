import os
import datetime
from googleapiclient.discovery import build
from authentication.models import GoogleChatCredentials

def get_calendar_service(user):
    """Build and return a Google Calendar API service for the user"""
    try:
        creds_model = GoogleChatCredentials.objects.get(user=user)
        
        creds = creds_model.google_credentials()
        
        return build('calendar', 'v3', credentials=creds)
    except Exception as e:
        print(f"Error building Calendar service: {e}")
        return None

def create_meet_event(user, title, start_time_iso, duration_minutes=60, description="", location=""):
    """
    Creates a Google Calendar event with a Google Meet link.
    start_time_iso: ISO 8601 string (e.g., '2023-10-27T10:00:00')
    """
    service = get_calendar_service(user)
    if not service:
        return {'success': False, 'error': 'Google Account not connected'}

    try:
        # Calculate end time
        start_dt = datetime.datetime.fromisoformat(start_time_iso)
        end_dt = start_dt + datetime.timedelta(minutes=int(duration_minutes))
        
        event_body = {
            'summary': title,
            'location': location,
            'description': description,
            'start': {
                'dateTime': start_dt.isoformat(),
                'timeZone': 'UTC', # Adjust if you have user's timezone
            },
            'end': {
                'dateTime': end_dt.isoformat(),
                'timeZone': 'UTC',
            },
            'conferenceData': {
                'createRequest': {
                    'requestId': f"meet_{int(datetime.datetime.now().timestamp())}",
                    'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                }
            }
        }

        event = service.events().insert(
            calendarId='primary',
            body=event_body,
            conferenceDataVersion=1
        ).execute()

        meet_link = event.get('hangoutLink')
        
        return {
            'success': True,
            'meet_link': meet_link,
            'event_id': event.get('id'),
            'html_link': event.get('htmlLink')
        }

    except Exception as e:
        print(f"Calendar Event Error: {e}")
        return {'success': False, 'error': str(e)}
