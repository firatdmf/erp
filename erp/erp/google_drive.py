import os
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from authentication.models import GoogleChatCredentials

def get_drive_service(user):
    """Build and return a Google Drive API service for the user"""
    try:
        creds_model = GoogleChatCredentials.objects.get(user=user)
        
        creds = Credentials(
            token=creds_model.token,
            refresh_token=creds_model.refresh_token,
            token_uri=creds_model.token_uri,
            client_id=creds_model.client_id,
            client_secret=creds_model.client_secret,
            scopes=creds_model.scopes.split(' ') if creds_model.scopes else []
        )
        
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        print(f"Error building Drive service: {e}")
        return None

def upload_file_to_drive(user, file_obj, folder_name="ERP Attachments"):
    """
    Uploads a file directly to Google Drive.
    Returns dictionary with file_id, web_view_link, etc.
    """
    service = get_drive_service(user)
    if not service:
        return {'success': False, 'error': 'Google Account not connected'}

    try:
        # 1. Check/Create Folder
        folder_id = None
        query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
        results = service.files().list(q=query, fields="files(id)").execute()
        files = results.get('files', [])
        
        if files:
            folder_id = files[0]['id']
        else:
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = service.files().create(body=folder_metadata, fields='id').execute()
            folder_id = folder.get('id')

        # 2. Upload File
        file_metadata = {
            'name': file_obj.name,
            'parents': [folder_id]
        }
        
        # Determine mime type (guess if not available)
        mime_type = getattr(file_obj, 'content_type', 'application/octet-stream')
        
        media = MediaIoBaseUpload(file_obj, mimetype=mime_type, resumable=True)
        
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, webViewLink, webContentLink, iconLink'
        ).execute()

        # 3. Make file readable by anyone with link
        try:
            permission = {'type': 'anyone', 'role': 'reader'}
            service.permissions().create(fileId=file.get('id'), body=permission).execute()
        except Exception as pe:
             print(f"Warning: Failed to set permissions for {file.get('name')}: {pe}")

        return {
            'success': True,
            'file_id': file.get('id'),
            'name': file.get('name'),
            'drive_link': file.get('webViewLink'),
            'download_link': file.get('webContentLink'),
            'icon_link': file.get('iconLink')
        }

    except Exception as e:
        print(f"Drive Upload Error: {e}")
        return {'success': False, 'error': str(e)}
