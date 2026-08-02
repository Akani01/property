import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url
from decouple import config
import json
from google.oauth2 import service_account

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# -------------------------------------------------------------------
# SECURITY
# -------------------------------------------------------------------
SECRET_KEY = config('SECRET_KEY', default='your-secret-key')
DEBUG = config('DEBUG', default=False, cast=bool)

# ============================================
# ALLOWED HOSTS
# ============================================
ALLOWED_HOSTS = [
    '127.0.0.1',
    'localhost',
    '0.0.0.0',
    'property.railway.internal',
    '*.railway.internal',
    'property-production-61c8.up.railway.app',
    '*.up.railway.app',
    '*.railway.app',
]

# ============================================
# CSRF TRUSTED ORIGINS
# ============================================
CSRF_TRUSTED_ORIGINS = [
    'http://127.0.0.1:8000',
    'http://localhost:8000',
    'http://property.railway.internal',
    'https://property.railway.internal',
    'https://property-production-61c8.up.railway.app',
    'https://*.up.railway.app',
    'https://*.railway.app',
]

# ============================================
# CORS Settings
# ============================================
CORS_ALLOWED_ORIGINS = [
    'http://127.0.0.1:8000',
    'http://localhost:8000',
    'http://property.railway.internal',
    'https://property-production-61c8.up.railway.app',
    'https://*.up.railway.app',
    'https://*.railway.app',
]
CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOW_CREDENTIALS = True


# ============================================================
# SESSION SETTINGS
# ============================================================

SESSION_COOKIE_SECURE = not DEBUG  # True in production
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 1209600  # 2 weeks
# -------------------------------------------------------------------
# SSL/Proxy Settings
# -------------------------------------------------------------------
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# -------------------------------------------------------------------
# APPLICATIONS
# -------------------------------------------------------------------
INSTALLED_APPS = [
    "django_extensions",
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    "crispy_forms",
    "crispy_bootstrap5",
    "rest_framework",
    "django_filters",
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'django.contrib.sites',
    'rest_framework_simplejwt',
    'social_auth',
    'channels',
    'corsheaders',
    'phonenumber_field',
    'pwa',
    'storages',
    'whitenoise',
    'hiring',
    'realestate',
    'core',
    'education',
    'notifications',
    'webpush',
]

AUTH_USER_MODEL = 'hiring.CustomUser'


# Google Auth
# ============================================================
# GOOGLE OAUTH 2.0 SETTINGS
# ============================================================

# Get Google Client ID from environment variable
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')

# If GOOGLE_CLIENT_ID is not set in environment, you can set it here for development
if not GOOGLE_CLIENT_ID and DEBUG:
    # For development, you can hardcode your Client ID here temporarily
    # GOOGLE_CLIENT_ID = 'YOUR_CLIENT_ID.apps.googleusercontent.com'
    pass

print(f"🔑 Google Client ID configured: {GOOGLE_CLIENT_ID[:20] if GOOGLE_CLIENT_ID else 'Not Set'}...")

# PWA settings
PWA_APP_NAME = 'Tolleya'
PWA_APP_DESCRIPTION = "Find your dream property"
PWA_APP_THEME_COLOR = '#c62828'
PWA_APP_BACKGROUND_COLOR = '#ffffff'
PWA_APP_DISPLAY = 'standalone'
PWA_APP_SCOPE = '/'
PWA_APP_START_URL = '/'
PWA_APP_STATUS_BAR_COLOR = 'default'
PWA_APP_ICONS = [
    {
        'src': '/static/images/icon-192x192.png',
        'sizes': '192x192',
        'type': 'image/png'
    },
    {
        'src': '/static/images/icon-512x512.png',
        'sizes': '512x512',
        'type': 'image/png'
    }
]
PWA_APP_SPLASH_SCREEN = [
    {
        'src': '/static/images/icon-512x512.png',
        'sizes': '512x512',
        'type': 'image/png'
    }
]
PWA_APP_DIR = 'ltr'
PWA_APP_LANG = 'en-US'
PWA_APP_ORIENTATION = 'portrait'

PWA_SETTINGS = {
    'VAPID_PUBLIC_KEY': 'YOUR_PUBLIC_KEY_HERE',
    'VAPID_PRIVATE_KEY': 'YOUR_PRIVATE_KEY_HERE',
    'VAPID_EMAIL': 'akaniivinmiyen@gmail.com',
}
# -------------------------------------------------------------------
# MIDDLEWARE
# -------------------------------------------------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'hiring.middleware.PWAThrottleMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'benta.urls'

# -------------------------------------------------------------------
# TEMPLATES
# -------------------------------------------------------------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                'core.context_processors.google_maps_api_key',
            ],
        },
    },
]

WSGI_APPLICATION = 'benta.wsgi.application'
ASGI_APPLICATION = 'benta.asgi.application'

# -------------------------------------------------------------------
# DATABASE
# -------------------------------------------------------------------
if 'DATABASE_URL' in os.environ:
    DATABASES = {
        'default': dj_database_url.config(
            default=os.environ.get('DATABASE_URL'),
            conn_max_age=600,
            ssl_require=True
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')

# -------------------------------------------------------------------
# STATIC & MEDIA FILES - FULLY FIXED
# -------------------------------------------------------------------
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
    os.path.join(BASE_DIR, 'hiring', 'static'),
]

# ✅ Auto-create static directories
for directory in STATICFILES_DIRS:
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
if not os.path.exists(STATIC_ROOT):
    os.makedirs(STATIC_ROOT, exist_ok=True)

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MAX_UPLOAD_SIZE = 314572800
DATA_UPLOAD_MAX_MEMORY_SIZE = 314572800
FILE_UPLOAD_MAX_MEMORY_SIZE = 314572800

# -------------------------------------------------------------------
# PASSWORD VALIDATION
# -------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# -------------------------------------------------------------------
# INTERNATIONALIZATION
# -------------------------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Johannesburg'
USE_I18N = True
USE_TZ = True

# -------------------------------------------------------------------
# ALLAUTH SETTINGS - UPDATED (Fixed deprecation warnings)
# -------------------------------------------------------------------
SITE_ID = 1
ACCOUNT_LOGIN_METHODS = {'email', 'username'}  # ✅ NEW
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*']  # ✅ NEW
ACCOUNT_EMAIL_VERIFICATION = 'optional'
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_LOGOUT_ON_GET = True
ACCOUNT_LOGOUT_REDIRECT_URL = '/'
LOGIN_REDIRECT_URL = '/dashboard/'
ACCOUNT_SIGNUP_REDIRECT_URL = '/profile/edit/'

# -------------------------------------------------------------------
# REST FRAMEWORK
# -------------------------------------------------------------------
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# -------------------------------------------------------------------
# EMAIL
# -------------------------------------------------------------------
FRONTEND_URL = config('FRONTEND_URL', default='https://property-production-61c8.up.railway.app')

if not DEBUG and 'EMAIL_HOST_USER' in os.environ:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'smtp.gmail.com'
    EMAIL_HOST_USER = config("EMAIL_HOST_USER")
    EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD")
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_USE_SSL = False
    DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL")
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# -------------------------------------------------------------------
# OTHER CONFIGS
# -------------------------------------------------------------------
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

RESIDENT_ID_PREFIX = 'ugr'
BUSINESS_ID_PREFIX = 'lec'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# -------------------------------------------------------------------
# REAL ESTATE APP SETTINGS
# -------------------------------------------------------------------
REALESTATE_SETTINGS = {
    'ENABLE_REAL_TIME_TRACKING': False,
    'ENABLE_GOOGLE_MAPS': True,
    'GOOGLE_MAPS_API_KEY': os.environ.get('GOOGLE_MAPS_API_KEY', ''),
    'MAX_NEARBY_RADIUS': 20,
    'DEFAULT_BOOKING_MODE': 'traditional',
}

GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', '')

# -------------------------------------------------------------------
# CHANNELS (WebSocket)
# -------------------------------------------------------------------
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}

# -------------------------------------------------------------------
# LOGGING
# -------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(module)s "
            "%(process)d %(thread)d %(message)s"
        }
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        }
    },
    "root": {"level": "INFO", "handlers": ["console"]},
}

# -------------------------------------------------------------------
# SECURITY HEADERS
# -------------------------------------------------------------------
if not DEBUG:
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# ============================================
# GOOGLE CLOUD STORAGE - UNIFORM BUCKET ACCESS (FIXED)
# ============================================

GS_BUCKET_NAME = os.environ.get('GS_BUCKET_NAME', 'tolleya-storage')

def get_google_credentials():
    """Get Google Cloud credentials from multiple sources"""
    
    # From environment variable as JSON string (Railway)
    if 'GS_CREDENTIALS_JSON' in os.environ:
        try:
            creds_json = json.loads(os.environ['GS_CREDENTIALS_JSON'])
            return service_account.Credentials.from_service_account_info(creds_json)
        except Exception as e:
            print(f"Error loading GS_CREDENTIALS_JSON: {e}")
    
    # From GOOGLE_APPLICATION_CREDENTIALS
    if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
        cred_path = os.environ['GOOGLE_APPLICATION_CREDENTIALS']
        if os.path.exists(cred_path):
            try:
                return service_account.Credentials.from_service_account_file(cred_path)
            except Exception as e:
                print(f"Error loading GOOGLE_APPLICATION_CREDENTIALS: {e}")
    
    # From GS_CREDENTIALS
    if 'GS_CREDENTIALS' in os.environ:
        cred_path = os.environ['GS_CREDENTIALS']
        if os.path.exists(cred_path):
            try:
                return service_account.Credentials.from_service_account_file(cred_path)
            except Exception as e:
                print(f"Error loading GS_CREDENTIALS: {e}")
    
    # From local credentials folder (development)
    local_cred_path = os.path.join(BASE_DIR, 'credentials', 'service-account-key.json')
    if os.path.exists(local_cred_path):
        try:
            return service_account.Credentials.from_service_account_file(local_cred_path)
        except Exception as e:
            print(f"Error loading local credentials: {e}")
    
    return None

GS_CREDENTIALS = get_google_credentials()

# ============================================
# STORAGES SETTINGS - UNIFORM BUCKET ACCESS (FIXED)
# ============================================

# ✅ No GS_DEFAULT_ACL - uniform bucket access handles permissions
GS_FILE_OVERWRITE = False
GS_QUERYSTRING_AUTH = False

if GS_CREDENTIALS and GS_BUCKET_NAME:
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.gcloud.GoogleCloudStorage",
            "OPTIONS": {
                "bucket_name": GS_BUCKET_NAME,
                "credentials": GS_CREDENTIALS,
                # ✅ No default_acl - bucket is public via IAM
                "file_overwrite": GS_FILE_OVERWRITE,
                "querystring_auth": GS_QUERYSTRING_AUTH,
            },
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
    MEDIA_URL = f'https://storage.googleapis.com/{GS_BUCKET_NAME}/'
    print(f"✅ Google Cloud Storage configured with uniform bucket-level access: {GS_BUCKET_NAME}")
else:
    # Fallback to local storage if no credentials
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
    MEDIA_URL = '/media/'
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
    print("⚠️ Using local file storage (Google Cloud credentials not found)")

# ============================================================
# PWA SETTINGS
# ============================================================

# Add these at the bottom of settings.py

# At the bottom of settings.py

# ⚠️ USING THE RAW VAPID KEYS FROM vapid_raw_keys.txt
PWA_SETTINGS = {
    'VAPID_PUBLIC_KEY': 'BAt7mPbnnynQNSCQalbpByolKwY_0LS3JyiQ0VSWpDDC2wFkyVJBsEMmra-beaYx-cUMTXgeQAtrzIYDYnnp7tk',
    'VAPID_PRIVATE_KEY': 'WPuo4Fr5_VXkmIoAy_talxVhdOhJ8mF3N8staMMloMg',
    'VAPID_EMAIL': 'akaniivinmiyen@gmail.com',
}

WEBPUSH_SETTINGS = {
    'VAPID_PUBLIC_KEY': PWA_SETTINGS['VAPID_PUBLIC_KEY'],
    'VAPID_PRIVATE_KEY': PWA_SETTINGS['VAPID_PRIVATE_KEY'],
    'VAPID_CLAIM': {'sub': 'mailto:' + PWA_SETTINGS['VAPID_EMAIL']}
}


# Add to settings.py
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '1000/day',
        'user': '1000/day',
    },
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# Add custom throttling for static files
from rest_framework.throttling import BaseThrottle

class NoThrottle(BaseThrottle):
    def allow_request(self, request, view):
        return True

# In your view, you can use:
# throttle_classes = [NoThrottle]