from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.hashers import make_password, check_password
from .models import WebClient
import json


@csrf_exempt
@require_http_methods(["POST"])
def create_web_client(request):
    """Create a new web client account"""
    try:
        data = json.loads(request.body)
        
        # Validation
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        name = data.get('name')
        
        if not all([username, email, password, name]):
            return JsonResponse({
                'error': 'All fields (username, email, password, name) are required'
            }, status=400)
        
        # Check if username already exists
        if WebClient.objects.filter(username=username).exists():
            return JsonResponse({
                'error': 'Username already taken'
            }, status=409)
        
        # Check if email already exists
        if WebClient.objects.filter(email=email).exists():
            return JsonResponse({
                'error': 'Email already registered'
            }, status=409)
        
        # Hash password
        hashed_password = make_password(password)
        
        # Create web client
        web_client = WebClient.objects.create(
            username=username,
            email=email,
            password=hashed_password,
            name=name
        )
        
        return JsonResponse({
            'message': 'Account created successfully',
            'user': {
                'id': web_client.id,
                'username': web_client.username,
                'email': web_client.email,
                'name': web_client.name,
                'created_at': web_client.created_at.isoformat()
            }
        }, status=201)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def login_web_client(request):
    """Login web client"""
    try:
        data = json.loads(request.body)
        
        username = data.get('username')
        password = data.get('password')
        
        if not all([username, password]):
            return JsonResponse({
                'error': 'Username and password are required'
            }, status=400)
        
        # Get user
        try:
            web_client = WebClient.objects.get(username=username)
        except WebClient.DoesNotExist:
            return JsonResponse({
                'error': 'Invalid credentials'
            }, status=401)
        
        # Check if account is active
        if not web_client.is_active:
            return JsonResponse({
                'error': 'Account is inactive'
            }, status=403)
        
        # Verify password
        if not check_password(password, web_client.password):
            return JsonResponse({
                'error': 'Invalid credentials'
            }, status=401)
        
        return JsonResponse({
            'message': 'Login successful',
            'user': {
                'id': web_client.id,
                'username': web_client.username,
                'email': web_client.email,
                'name': web_client.name
            }
        }, status=200)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def check_web_client_email(request):
    """Check if email exists (for Google OAuth)"""
    try:
        data = json.loads(request.body)
        email = data.get('email')
        
        if not email:
            return JsonResponse({
                'error': 'Email is required'
            }, status=400)
        
        exists = WebClient.objects.filter(email=email).exists()
        
        if exists:
            web_client = WebClient.objects.get(email=email)
            return JsonResponse({
                'exists': True,
                'user': {
                    'id': web_client.id,
                    'username': web_client.username,
                    'email': web_client.email,
                    'name': web_client.name
                }
            }, status=200)
        else:
            return JsonResponse({
                'exists': False
            }, status=200)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def create_google_client(request):
    """Create web client from Google OAuth"""
    try:
        data = json.loads(request.body)
        
        email = data.get('email')
        name = data.get('name')
        
        if not email:
            return JsonResponse({
                'error': 'Email is required'
            }, status=400)
        
        # Check if already exists
        if WebClient.objects.filter(email=email).exists():
            web_client = WebClient.objects.get(email=email)
            return JsonResponse({
                'message': 'User already exists',
                'user': {
                    'id': web_client.id,
                    'username': web_client.username,
                    'email': web_client.email,
                    'name': web_client.name
                }
            }, status=200)
        
        # Create username from email
        username = email.split('@')[0]
        counter = 1
        original_username = username
        while WebClient.objects.filter(username=username).exists():
            username = f"{original_username}_{counter}"
            counter += 1
        
        # Create web client (no password needed for OAuth users)
        web_client = WebClient.objects.create(
            username=username,
            email=email,
            password=make_password(None),  # Dummy password
            name=name or 'Google User'
        )
        
        return JsonResponse({
            'message': 'Account created successfully',
            'user': {
                'id': web_client.id,
                'username': web_client.username,
                'email': web_client.email,
                'name': web_client.name
            }
        }, status=201)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)
