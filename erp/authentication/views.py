from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth import update_session_auth_hash

# Create your views here.
from django.contrib.auth.models import User
from .models import Member
from .forms import UpdateProfileForm, CustomPasswordChangeForm
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages

from django.contrib.auth.decorators import login_required


@login_required
def home(request):
    # try:
    #     member = Member.objects.get(user=request.user)
    # except Member.DoesNotExist:
    #     # Handle the case where the Member object does not exist for the logged-in user
    #     member = None

    # return render(request, 'authentication/home.html', {'member': member})
    # return render(request, "authentication/index.html")
    if request.user:
        print("There is user!")
        try:
            member = Member.objects.get(user=request.user)
        except:
            member = None
        return render(request, "authentication/index.html", {"member": member})
    else:
        print("There is no user!")

        return render(request, "authentication/index.html")


def signup(request):
    if request.method == "POST":
        print("hello")
        # this is based on name, not id
        # username = request.POST.get('username')
        # below is same as above
        username = request.POST["username"]
        fname = request.POST["fname"]
        lname = request.POST["lname"]
        email = request.POST["email"]
        password = request.POST["password"]
        # cname = request.POST["cname"]

        myuser = User.objects.create_user(username, email, password)
        myuser.first_name = fname
        myuser.last_name = lname
        print(myuser)
        myuser.save()
        mymember = Member.objects.create(user=myuser)
        mymember.save()

        messages.success(request, "Your acccount has been successfully created.")
        return redirect("/authentication/signin")

    return render(request, "authentication/signup.html")


def signin(request):
    # go_to_url = request.GET['next']
    # print(go_to_url)
    if request.method == "GET":
        go_to_url = request.GET.get("next", "home")
        return render(request, "authentication/signin.html", {"next": go_to_url})

        # print('-------')
        # print(type(str(go_to_url)))
        # print(go_to_url)
        # print('-------')
    # def change():
    #     go_to_url = request.GET['next']
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        go_to_url = request.POST["next"]
        print("-------")
        print(type(str(go_to_url)))
        print(go_to_url)
        print("-------")
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            fname = user.first_name
            lname = user.last_name
            # return render(
            #     request,
            #     "authentication/index.html",
            #     {
            #         "fname": fname,
            #     },
            # )
            # print(go_to_url)
            # below takes it back to where they started in the url
            # return redirect(go_to_url)
            return redirect("/authentication/home")
        else:
            messages.error(request, "Bad Credentials!")
            # this is the name of the url
            # return redirect("/authentication/signin")
            args ={}
            args['errorMessage'] = 'Your password was wrong'
    return render(request, "authentication/signin.html",args)


def signout(request):
    logout(request)
    messages.success(request, "Logged out successfully")
    return redirect("index")


@login_required
def update_profile(request):
    if request.method == "POST":
        form = UpdateProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return HttpResponse("""
                <div class="alert alert-success" role="alert" style="padding: 1rem; background-color: #d1fae5; color: #065f46; border-radius: 0.5rem; margin-bottom: 1rem;">
                    <i class="fas fa-check-circle"></i> Profile updated successfully!
                </div>
            """)
        else:
            errors = form.errors.as_text()
            return HttpResponse(f"""
                <div class="alert alert-danger" role="alert" style="padding: 1rem; background-color: #fee2e2; color: #991b1b; border-radius: 0.5rem; margin-bottom: 1rem;">
                    <i class="fas fa-exclamation-circle"></i> Error updating profile: {errors}
                </div>
            """)
    return HttpResponse(status=405) # Method Not Allowed


@login_required
def change_password_settings(request):
    if request.method == "POST":
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(request, "Password changed successfully!")
            return HttpResponse("""
                <div class="alert alert-success" role="alert" style="padding: 1rem; background-color: #d1fae5; color: #065f46; border-radius: 0.5rem; margin-bottom: 1rem;">
                    <i class="fas fa-check-circle"></i> Password changed successfully!
                </div>
            """)
        else:
             # Basic error formatting
            error_html = "<ul>"
            for field, errors in form.errors.items():
                for error in errors:
                    error_html += f"<li>{error}</li>"
            error_html += "</ul>"
            
            return HttpResponse(f"""
                <div class="alert alert-danger" role="alert" style="padding: 1rem; background-color: #fee2e2; color: #991b1b; border-radius: 0.5rem; margin-bottom: 1rem;">
                    <i class="fas fa-exclamation-circle"></i> Error changing password: {error_html}
                </div>
            """)
    return HttpResponse(status=405)


# ------------------- Google OAuth Views -------------------

import os
import google_auth_oauthlib.flow
from django.views import View
from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from django.http import HttpResponse
from .models import GoogleChatCredentials

# Scopes for Google Chat
GOOGLE_CHAT_SCOPES = [
    'https://www.googleapis.com/auth/chat.spaces',
    'https://www.googleapis.com/auth/chat.spaces.readonly',
    'https://www.googleapis.com/auth/chat.messages.readonly',
    'https://www.googleapis.com/auth/chat.messages',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/drive.file',
    # Gmail Scopes
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.send',
    # Calendar Scopes
    'https://www.googleapis.com/auth/calendar.events',
]

# Allow HTTP for development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
# Allow Google to add extra scopes (like openid) without failing
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

class GoogleAuthView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('authentication:signin')

        # Use keys from settings
        # Ensure GOOGLE_OAUTH_CLIENT_ID and SECRET are in settings.py
        client_config = {
            "web": {
                "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "redirect_uris": [request.build_absolute_uri(reverse('authentication:google_callback'))]
            }
        }
        
        flow = google_auth_oauthlib.flow.Flow.from_client_config(
            client_config,
            scopes=GOOGLE_CHAT_SCOPES
        )

        flow.redirect_uri = request.build_absolute_uri(reverse('authentication:google_callback'))
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent' # Force consent to ensure we get refresh token and can see account picker
        )

        request.session['google_oauth_state'] = state
        
        return redirect(authorization_url)


class GoogleCallbackView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('authentication:signin')

        state = request.session.get('google_oauth_state')
        
        if not state:
             return HttpResponse("State not found in session.", status=400)

        client_config = {
            "web": {
                "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "redirect_uris": [request.build_absolute_uri(reverse('authentication:google_callback'))]
            }
        }

        flow = google_auth_oauthlib.flow.Flow.from_client_config(
            client_config,
            scopes=GOOGLE_CHAT_SCOPES,
            state=state
        )
        flow.redirect_uri = request.build_absolute_uri(reverse('authentication:google_callback'))
        
        print(f"DEBUG: Redirect URI used: {flow.redirect_uri}")

        authorization_response = request.get_full_path()
        
        try:
            flow.fetch_token(authorization_response=authorization_response)
        except Exception as e:
            # Common error: InvalidGrantError usually means code expired or reused
            error_msg = str(e)
            if "invalid_grant" in error_msg:
                friendly_msg = "The authorization code expired or was already used. Please try connecting again."
            elif "mismatch" in error_msg:
                friendly_msg = "Redirect URI mismatch. Please check Google Cloud Console settings."
            else:
                friendly_msg = f"Authentication failed: {error_msg}"

            return HttpResponse(f"""
                <div style="font-family: sans-serif; padding: 20px; text-align: center;">
                    <h1>Connection Failed</h1>
                    <p>{friendly_msg}</p>
                    <p style="color: #666; font-size: 12px;">Technical Detail: {error_msg}</p>
                    <a href="{reverse('user_settings')}" style="padding: 10px 20px; background: #1a73e8; color: white; text-decoration: none; border-radius: 4px;">Return to Settings</a>
                </div>
            """, status=400)

        credentials = flow.credentials
        
        # Fetch user info
        from googleapiclient.discovery import build
        user_info_service = build('oauth2', 'v2', credentials=credentials)
        user_info = user_info_service.userinfo().get().execute()
        
        email = user_info.get('email')
        picture = user_info.get('picture')
        
        GoogleChatCredentials.objects.update_or_create(
            user=request.user,
            defaults={
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': ' '.join(credentials.scopes) if credentials.scopes else '',
                'email': email,
                'avatar_url': picture
            }
        )

        return redirect('user_settings')


class GoogleDisconnectView(View):
    def get(self, request):
        if request.user.is_authenticated:
            GoogleChatCredentials.objects.filter(user=request.user).delete()
        return redirect('user_settings')
