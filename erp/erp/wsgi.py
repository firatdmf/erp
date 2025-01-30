"""
WSGI config for erp project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')

application = get_wsgi_application()


# I added below for deploying the django to Vercel
# to bridge the connection with vercel (remember vercel.app from settings.py)
# app = application
