from googleapiclient.discovery import build
from django.utils import timezone
from authentication.models import GoogleChatCredentials
from todo.models import Task
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
        creds = creds_model.google_credentials()
        
        service = build('tasks', 'v1', credentials=creds)
        return service
    except GoogleChatCredentials.DoesNotExist:
        return None
    except Exception as e:
        print(f"Error building Tasks service: {e}")
        return None

def _google_body(task):
    """What Google Tasks holds for a task. A team task's notes say which
    team it is from, since Google has no teams."""
    notes = task.description or ''
    if task.team_id:
        notes = f"[ERP Team Task from {task.team.name}]\n\n" + notes
    body = {
        'title': task.name,
        'notes': notes,
        'status': 'completed' if task.completed else 'needsAction',
    }
    if task.due_date:
        # Google Tasks expects an RFC 3339 timestamp; it keeps only the day.
        dt = datetime.combine(task.due_date, datetime.min.time())
        body['due'] = dt.isoformat() + 'Z'
    return body


def push_task_to_google(user, task):
    """
    Creates a new task in the user's default Google Tasks list from an ERP
    task, personal or team. Saves the google_task_id to the task.
    """
    service = get_tasks_service(user)
    if not service:
        return False

    try:
        result = service.tasks().insert(tasklist='@default', body=_google_body(task)).execute()
        task.google_task_id = result.get('id')
        task.save(update_fields=['google_task_id'])
        return True
    except Exception as e:
        print(f"Error pushing task to Google: {e}")
        return False


def update_task_in_google(user, task_obj):
    """
    Updates an existing task in Google Tasks, or pushes it if Google has
    not got it yet.
    """
    if not task_obj.google_task_id:
        return push_task_to_google(user, task_obj)

    service = get_tasks_service(user)
    if not service:
        return False

    try:
        body = _google_body(task_obj)
        body['id'] = task_obj.google_task_id
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
            
            # Personal and team tasks are one kind of task
            personal_exists = Task.everywhere.filter(google_task_id=g_id).first()

            if personal_exists:
                # Finished or reopened in Google: the same as on our screens
                if g_status == 'completed' and not personal_exists.completed:
                    personal_exists.set_status('done')
                    personal_exists.save()
                elif g_status == 'needsAction' and personal_exists.completed:
                    personal_exists.set_status('todo')
                    personal_exists.save()
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
