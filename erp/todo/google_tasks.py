from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from django.utils import timezone
from authentication.models import GoogleChatCredentials
from todo.models import Task
from team.models import TeamTask
from datetime import datetime
import json

def get_tasks_service(user):
    """
    Builds and returns a Google Tasks API service wrapper from the user's credentials.
    Returns None if the user hasn't linked Google or the token is invalid.
    """
    try:
        creds_model = GoogleChatCredentials.objects.get(user=user)
        
        # We need the task scope to be present. If it's an old token, it might not have it.
        # But for now, we'll try to build it. If it fails, the caller handles it.
        creds = Credentials(
            token=creds_model.token,
            refresh_token=creds_model.refresh_token,
            token_uri=creds_model.token_uri,
            client_id=creds_model.client_id,
            client_secret=creds_model.client_secret,
            scopes=creds_model.scopes.split() if creds_model.scopes else []
        )
        
        service = build('tasks', 'v1', credentials=creds)
        return service
    except GoogleChatCredentials.DoesNotExist:
        return None
    except Exception as e:
        print(f"Error building Tasks service: {e}")
        return None

def push_task_to_google(user, task):
    """
    Creates a new task in the user's default Google Tasks list based on a personal ERP task.
    Saves the google_task_id to the task model.
    """
    service = get_tasks_service(user)
    if not service:
        return False
        
    try:
        body = {
            'title': task.name,
            'notes': task.description or '',
            'status': 'completed' if task.completed else 'needsAction',
        }
        
        if task.due_date:
            # Google Tasks expects RFC 3339 timestamp string
            dt = datetime.combine(task.due_date, datetime.min.time())
            body['due'] = dt.isoformat() + 'Z'
            
        result = service.tasks().insert(tasklist='@default', body=body).execute()
        
        # Save the ID back to our DB
        task.google_task_id = result.get('id')
        task.save(update_fields=['google_task_id'])
        return True
    except Exception as e:
        print(f"Error pushing task to Google: {e}")
        return False

def push_team_task_to_google(user, team_task):
    """
    Creates a new task in the user's default Google Tasks list based on an ERP Team task.
    Saves the google_task_id to the team_task model. Appends team info to the notes.
    """
    service = get_tasks_service(user)
    if not service:
        return False
        
    try:
        notes = f"[ERP Team Task from {team_task.team.name}]\n\n"
        if team_task.description:
            notes += team_task.description
            
        body = {
            'title': team_task.title,
            'notes': notes,
            'status': 'completed' if team_task.status == 'done' else 'needsAction',
        }
        
        if team_task.due_date:
            # Google Tasks expects RFC 3339 timestamp string for due dates (needs to be converted properly)
            body['due'] = team_task.due_date.isoformat()
            
        result = service.tasks().insert(tasklist='@default', body=body).execute()
        
        team_task.google_task_id = result.get('id')
        team_task.save(update_fields=['google_task_id'])
        return True
    except Exception as e:
        print(f"Error pushing team task to Google: {e}")
        return False

def update_task_in_google(user, task_obj, is_team=False):
    """
    Updates an existing task in Google Tasks.
    task_obj can be either a todo.Task or team.TeamTask.
    """
    if not task_obj.google_task_id:
        # If it doesn't exist in Google yet, just push it now
        if is_team:
            return push_team_task_to_google(user, task_obj)
        else:
            return push_task_to_google(user, task_obj)
            
    service = get_tasks_service(user)
    if not service:
        return False
        
    try:
        if is_team:
            notes = f"[ERP Team Task from {task_obj.team.name}]\n\n"
            if task_obj.description:
                notes += task_obj.description
            body = {
                'id': task_obj.google_task_id,
                'title': task_obj.title,
                'notes': notes,
                'status': 'completed' if task_obj.status == 'done' else 'needsAction',
            }
            if task_obj.due_date:
                 body['due'] = task_obj.due_date.isoformat()
        else:
            body = {
                'id': task_obj.google_task_id,
                'title': task_obj.name,
                'notes': task_obj.description or '',
                'status': 'completed' if task_obj.completed else 'needsAction',
            }
            if task_obj.due_date:
                dt = datetime.combine(task_obj.due_date, datetime.min.time())
                body['due'] = dt.isoformat() + 'Z'
                
        service.tasks().update(tasklist='@default', task=task_obj.google_task_id, body=body).execute()
        return True
    except Exception as e:
        print(f"Error updating task in Google: {e}")
        return False

def sync_from_google(user):
    """
    Downloads the user's task list from Google Tasks.
    If a task doesn't have a matching google_task_id in the DB, 
    creates it as a Personal Task in ERP.
    """
    service = get_tasks_service(user)
    if not service:
        return False
        
    try:
        # Get tasks from default list
        # We only want tasks that are not completed, or recently updated
        results = service.tasks().list(tasklist='@default', maxResults=100, showHidden=True).execute()
        items = results.get('items', [])
        
        if not items:
            return True
            
        if not hasattr(user, 'member'):
            return False
            
        member = user.member
        
        for item in items:
            g_id = item.get('id')
            g_title = item.get('title', 'Untitled Task')
            g_notes = item.get('notes', '')
            g_status = item.get('status') # 'needsAction' or 'completed'
            g_due = item.get('due')
            
            # Check if this task exists in either Personal or Team tasks
            personal_exists = Task.objects.filter(google_task_id=g_id).first()
            team_exists = TeamTask.objects.filter(google_task_id=g_id).first()
            
            if team_exists:
                # If it's a team task, we can update our local status based on Google
                if g_status == 'completed' and team_exists.status != 'done':
                    team_exists.status = 'done'
                    team_exists.completed_at = timezone.now()
                    team_exists.save(update_fields=['status', 'completed_at'])
                elif g_status == 'needsAction' and team_exists.status == 'done':
                    team_exists.status = 'todo'
                    team_exists.save(update_fields=['status'])
                continue
                
            if personal_exists:
                # Update existing personal task from Google
                if g_status == 'completed' and not personal_exists.completed:
                    personal_exists.completed = True
                    personal_exists.completed_at = timezone.now()
                    personal_exists.save(update_fields=['completed', 'completed_at'])
                elif g_status == 'needsAction' and personal_exists.completed:
                    personal_exists.completed = False
                    personal_exists.completed_at = None
                    personal_exists.save(update_fields=['completed', 'completed_at'])
                continue
                
            # If we get here, this is a NEW task from Google
            # We ONLY import into Personal Tasks (todo.Task) because Google Tasks has no team concept
            due_date_obj = None
            if g_due:
                # Parse '2023-10-31T00:00:00.000Z' string -> datetime -> date
                try:
                    due_date_obj = datetime.strptime(g_due[:10], '%Y-%m-%d').date()
                except ValueError:
                    due_date_obj = timezone.now().date()
            else:
                due_date_obj = timezone.now().date()
                
            Task.objects.create(
                name=g_title,
                description=g_notes,
                due_date=due_date_obj,
                priority='medium',
                status='done' if g_status == 'completed' else 'todo',
                completed=(g_status == 'completed'),
                completed_at=timezone.now() if g_status == 'completed' else None,
                member=member,
                created_by=member,
                google_task_id=g_id
            )
            
        return True
    except Exception as e:
        print(f"Error syncing from Google Tasks: {e}")
        return False
