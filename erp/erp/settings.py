"""
Django settings for erp project.

Generated by 'django-admin startproject' using Django 4.2.4.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.2/ref/settings/
"""

from pathlib import Path
import os

# below is for loading environment variables for establishing security
# from dotenv import load_dotenv
from decouple import config

# load_dotenv()
# print(os.getenv('DATABASE'))
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = [
    ".vercel.app",
    "erp.demfirat.com",
    "demfirat.com",
    "127.0.0.1",
    "localhost",
    "app.nejum.com",
    "www.nejum.com",
    "nejum.com"
]

# CSRF_TRUSTED_ORIGINS = ['https://*.demfirat.com','https://*.127.0.0.1']
CSRF_TRUSTED_ORIGINS = [
    "https://*.demfirat.com",
    "https://*.vercel.app",
]

# Below is added for django OAuth
# we may need to change to something else other than 1, but that's for later
# SITE_ID = 1

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "erp",
    "todo",
    "crm",
    "accounting",
    "jquery",
    "authentication",
    "operating",
    "django_htmx",
    # below is for google auth
    # "django.contrib.sites",
    # "allauth",  # this allows us to do other authentications beside the standard one (like google)
    # "allauth.account",
    # "allauth.socialaccount",
    # "allauth.socialaccount.providers.google",
]

# SOCIALACCOUNT_PROVIDERS = {
#     "google": {
#         # this is our credentials
#         "SCOPE": [
#             "profile",
#             "email",
#         ],
#         "AUTH_PARAMS": {
#             "access_type": "online",
#         },
#     }
# }


# Don't know if below does any shit.
# SOCIALACCOUNT_LOGIN_ON_GET = True
# TEMPLATE_CONTEXT_PROCESSORS = [
#     # ...
#     "allauth.socialaccount.context_processors.socialaccount",
#     # ...
# ]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    # "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "erp.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # The below helps to put the view function variable global in all templates
                'erp.context_processors.last_five_entities',
            ],
        },
    },
]

# WSGI_APPLICATION = "erp.wsgi.application"
WSGI_APPLICATION = "erp.wsgi.app"


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases
# DATABASE_URL = 'postgresql://postgres:z5nJKvkJjjrYwgHZZYRz@containers-us-west-99.railway.app:6547/railway'
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

# below is for postgres that I added myself @firat
# below is for local postgres
# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.postgresql",
#         # name of database
#         "NAME": "erp",
#         # user that created the database, or have access to it
#         "USER": "postgres",
#         # user password
#         "PASSWORD": "12345678",
#         "HOST": "",  # an empty string means localhost
#         "PORT": "5432",
#     }
# }
# BELOW IS FOR SECURE LOCAL DB WITH ENV FILE
# DATABASES = {
#     os.getenv('DATABASE')
# }

# below is for railway postgres db
# DATABASES = {
#     "default": {
#         "ENGINE": config('ENGINE'),
#         # name of database
#         "NAME": config("NAME"),
#         # user that created the database, or have access to it
#         "USER": config("USER"),
#         # user password
#         "PASSWORD": config("PASSWORD"),
#         "HOST": config("HOST"), # an empty string means localhost
#         "PORT": config("PORT"),
#     }
# }
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        # name of database
        "NAME": "postgres",
        # user that created the database, or have access to it
        "USER": "postgres.eyzefiawzpxtwzqymyph",
        # user password
        "PASSWORD": "mzH36GKgBrDgr4QF",
        "HOST": "aws-0-eu-west-1.pooler.supabase.com", # an empty string means localhost
        "PORT": "6543",
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = "en-us"

# TIME_ZONE = 'UTC'
# TIME_ZONE = "US/Pacific"
TIME_ZONE = 'Europe/Istanbul'

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

# STATIC_URL = '/static/'

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "static")
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# specify the URL where Django should redirect unauthenticated users:
# LOGIN_URL = 'login'
# LOGOUT_URL = 'logout'


AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

if not DEBUG:
    STATIC_ROOT = BASE_DIR / "static"

STATICFILES_DIRS = []


# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# AUTHENTICATION_BACKENDS = (
#     # Needed to login by username in Django admin, regardless of 'allauth'
#     "django.contrib.auth.backends.ModelBackend",
#     # Logging in with allauth
#     "allauth.account.auth_backends.AuthenticationBackend",
# )

# LOGIN_REDIRECT_URL = ""
LOGIN_URL = '/authentication/signin'
LOGOUT_REDIRECT_URL = "/authentication/index"
# LOGOUT_REDIRECT_URL = "/"
