from django.urls import path
from . import views

app_name = 'email_automation'

urlpatterns = [
    # Dashboard - main email page
    path('', views.dashboard, name='dashboard'),
    
    # Gmail OAuth
    path('connect/', views.connect_gmail, name='connect_gmail'),
    path('oauth2callback/', views.oauth2callback, name='oauth2callback'),
    path('disconnect/', views.disconnect_gmail, name='disconnect_gmail'),
    
    # Inbox/Outbox
    path('inbox/', views.inbox_view, name='inbox'),
    path('outbox/', views.outbox_view, name='outbox'),
    
    # Templates
    path('templates/', views.template_list, name='template_list'),
    path('templates/create/', views.template_create, name='template_create'),
    path('templates/<int:pk>/edit/', views.template_edit, name='template_edit'),
    
    # Campaigns
    path('campaigns/', views.campaign_list, name='campaign_list'),
    path('campaigns/<int:pk>/', views.campaign_detail, name='campaign_detail'),
    path('campaigns/<int:pk>/pause/', views.campaign_pause, name='campaign_pause'),
    path('campaigns/<int:pk>/resume/', views.campaign_resume, name='campaign_resume'),
    path('campaigns/<int:pk>/delete/', views.campaign_delete, name='campaign_delete'),
    
    # API Endpoints
    path('api/inbox/', views.api_inbox, name='api_inbox'),
    path('api/inbox/<str:message_id>/', views.api_inbox_detail, name='api_inbox_detail'),
    path('api/sent/', views.api_sent, name='api_sent'),
    path('api/sent/<int:pk>/', views.api_sent_detail, name='api_sent_detail'),
    path('api/templates/', views.api_templates, name='api_templates'),
    path('api/campaigns/', views.api_campaigns, name='api_campaigns'),
    
    # Legacy API
    path('sent/<int:pk>/', views.sent_email_detail_api, name='sent_email_detail_api'),
]
