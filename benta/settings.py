import os
import json
from pathlib import Path

from dotenv import load_dotenv
import dj_database_url
from decouple import config
from google.oauth2 import service_account


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


# ============================================================
# SECURITY
# ============================================================

SECRET_KEY = config(
    'SECRET_KEY',
    default='change-this-secret-key-in-production'
)

# FINAL PRODUCTION DEPLOYMENT
DEBUG = config(
    'DEBUG',
    default=False,
    cast=bool
)


# ============================================================
# ALLOWED HOSTS
# ============================================================

ALLOWED_HOSTS = [
    'oppoglobe.co.za',
    'www.oppoglobe.co.za',

    # Railway
    'property-production-61c8.up.railway.app',
    '*.up.railway.app',
    '*.railway.app',

    # Railway internal
    'property.railway.internal',
    '*.railway.internal',

    # Local development access
    '127.0.0.1',
    'localhost',
    '0.0.0.0',
]


# ============================================================
# CSRF TRUSTED ORIGINS
# ============================================================

CSRF_TRUSTED_ORIGINS = [
    'https://oppoglobe.co.za',
    'https://www.oppoglobe.co.za',

    # Railway
    'https://property-production-61c8.up.railway.app',

    # Local
    'http://127.0.0.1:8000',
    'http://localhost:8000',

    # Railway internal
    'https://property.railway.internal',
]


# ============================================================
# CORS
# ============================================================

CORS_ALLOWED_ORIGINS = [
    'https://oppoglobe.co.za',
    'https://www.oppoglobe.co.za',

    'https://property-production-61c8.up.railway.app',

    # Local
    'http://127.0.0.1:8000',
    'http://localhost:8000',
]

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = True


# ============================================================
# SESSION SETTINGS
# ============================================================

SESSION_ENGINE = 'django.contrib.sessions.backends.db'

SESSION_COOKIE_AGE = 1209600  # 2 weeks

SESSION_COOKIE_HTTPONLY = True

SESSION_COOKIE_SAMESITE = 'Lax'

SESSION_COOKIE_SECURE = True


# ============================================================
# CSRF COOKIE
# ============================================================

CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = 'Lax'


# ============================================================
# SSL / RAILWAY PROXY
# ============================================================

SECURE_PROXY_SSL_HEADER = (
    'HTTP_X_FORWARDED_PROTO',
    'https'
)

SECURE_SSL_REDIRECT = False


# ============================================================
# SECURITY HEADERS
# ============================================================

if not DEBUG:

    SECURE_CONTENT_TYPE_NOSNIFF = True

    SECURE_BROWSER_XSS_FILTER = True

    X_FRAME_OPTIONS = 'DENY'

    SECURE_HSTS_SECONDS = 31536000

    SECURE_HSTS_INCLUDE_SUBDOMAINS = True

    SECURE_HSTS_PRELOAD = True


# ============================================================
# APPLICATIONS
# ============================================================

INSTALLED_APPS = [

    # Django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',

    # Development / utilities
    'django_extensions',

    # Forms
    'crispy_forms',
    'crispy_bootstrap5',

    # REST API
    'rest_framework',
    'django_filters',
    'rest_framework_simplejwt',

    # Authentication
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',

    # Project apps
    'hiring',
    'realestate',
    'core',
    'education',
    'notifications',
    'ads',

    # Communication
    'channels',
    'corsheaders',

    # Utilities
    'phonenumber_field',

    # PWA
    'pwa',
    'webpush',
    'storages',
    'whitenoise',
]


# ============================================================
# CUSTOM USER
# ============================================================

AUTH_USER_MODEL = 'hiring.CustomUser'


# ============================================================
# SITE
# ============================================================

SITE_ID = 1


# ============================================================
# GOOGLE OAUTH 2.0
# ============================================================

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
        'OAUTH_PKCE_ENABLED': True,
    }
}


# ============================================================
# PWA
# ============================================================

PWA_APP_NAME = 'OppoGlobe'

PWA_APP_DESCRIPTION = (
    'Find your dream property and access convenient property services.'
)

PWA_APP_THEME_COLOR = '#c62828'

PWA_APP_BACKGROUND_COLOR = '#ffffff'

PWA_APP_DISPLAY = 'standalone'

PWA_APP_SCOPE = '/'

PWA_APP_START_URL = '/'

PWA_APP_STATUS_BAR_COLOR = 'default'

PWA_APP_DIR = 'ltr'

PWA_APP_LANG = 'en-US'

PWA_APP_ORIENTATION = 'portrait'


PWA_APP_ICONS = [

    {
        'src': '/static/images/icon-192x192.png',
        'sizes': '192x192',
        'type': 'image/png',
    },

    {
        'src': '/static/images/icon-512x512.png',
        'sizes': '512x512',
        'type': 'image/png',
    },
]


PWA_APP_SPLASH_SCREEN = [

    {
        'src': '/static/images/icon-512x512.png',
        'sizes': '512x512',
        'type': 'image/png',
    },
]


# ============================================================
# WEB PUSH / PWA NOTIFICATIONS
# ============================================================

PWA_VAPID_PUBLIC_KEY = os.environ.get(
    'VAPID_PUBLIC_KEY',
    ''
)

PWA_VAPID_PRIVATE_KEY = os.environ.get(
    'VAPID_PRIVATE_KEY',
    ''
)

PWA_VAPID_EMAIL = os.environ.get(
    'VAPID_EMAIL',
    'akaniivinmiyen@gmail.com'
)


PWA_SETTINGS = {

    'VAPID_PUBLIC_KEY': PWA_VAPID_PUBLIC_KEY,

    'VAPID_PRIVATE_KEY': PWA_VAPID_PRIVATE_KEY,

    'VAPID_EMAIL': PWA_VAPID_EMAIL,
}


WEBPUSH_SETTINGS = {

    'VAPID_PUBLIC_KEY': PWA_VAPID_PUBLIC_KEY,

    'VAPID_PRIVATE_KEY': PWA_VAPID_PRIVATE_KEY,

    'VAPID_CLAIM': {
        'sub': f'mailto:{PWA_VAPID_EMAIL}'
    },
}


# ============================================================
# MIDDLEWARE
# ============================================================

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


# ============================================================
# URL CONFIGURATION
# ============================================================

ROOT_URLCONF = 'benta.urls'


# ============================================================
# TEMPLATES
# ============================================================

TEMPLATES = [

    {

        'BACKEND':
            'django.template.backends.django.DjangoTemplates',

        'DIRS': [
            BASE_DIR / 'templates',
        ],

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


# ============================================================
# WSGI / ASGI
# ============================================================

WSGI_APPLICATION = 'benta.wsgi.application'

ASGI_APPLICATION = 'benta.asgi.application'


# ============================================================
# DATABASE
# ============================================================

if os.environ.get('DATABASE_URL'):

    DATABASES = {

        'default': dj_database_url.config(

            default=os.environ.get(
                'DATABASE_URL'
            ),

            conn_max_age=600,

            ssl_require=True,
        )
    }

else:

    DATABASES = {

        'default': {

            'ENGINE':
                'django.db.backends.sqlite3',

            'NAME':
                BASE_DIR / 'db.sqlite3',
        }
    }


# ============================================================
# API KEYS
# ============================================================

DEEPSEEK_API_KEY = os.environ.get(
    'DEEPSEEK_API_KEY',
    ''
)


GOOGLE_MAPS_API_KEY = os.environ.get(
    'GOOGLE_MAPS_API_KEY',
    ''
)


# ============================================================
# STATIC FILES
# ============================================================

STATIC_URL = '/static/'

STATIC_ROOT = os.path.join(
    BASE_DIR,
    'staticfiles'
)


STATICFILES_DIRS = [

    os.path.join(
        BASE_DIR,
        'static'
    ),

    os.path.join(
        BASE_DIR,
        'hiring',
        'static'
    ),
]


# ============================================================
# CREATE STATIC DIRECTORIES IF NEEDED
# ============================================================

for directory in STATICFILES_DIRS:

    if not os.path.exists(directory):

        os.makedirs(
            directory,
            exist_ok=True
        )


if not os.path.exists(STATIC_ROOT):

    os.makedirs(
        STATIC_ROOT,
        exist_ok=True
    )


# ============================================================
# UPLOAD LIMITS
# ============================================================

MAX_UPLOAD_SIZE = 314572800

DATA_UPLOAD_MAX_MEMORY_SIZE = 314572800

FILE_UPLOAD_MAX_MEMORY_SIZE = 314572800


# ============================================================
# PASSWORD VALIDATION
# ============================================================

AUTH_PASSWORD_VALIDATORS = [

    {
        'NAME':
            'django.contrib.auth.password_validation.'
            'UserAttributeSimilarityValidator',
    },

    {
        'NAME':
            'django.contrib.auth.password_validation.'
            'MinimumLengthValidator',
    },

    {
        'NAME':
            'django.contrib.auth.password_validation.'
            'CommonPasswordValidator',
    },

    {
        'NAME':
            'django.contrib.auth.password_validation.'
            'NumericPasswordValidator',
    },
]


# ============================================================
# INTERNATIONALIZATION
# ============================================================

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Africa/Johannesburg'

USE_I18N = True

USE_TZ = True


# ============================================================
# AUTHENTICATION BACKENDS
# ============================================================

AUTHENTICATION_BACKENDS = [

    'django.contrib.auth.backends.ModelBackend',

    'allauth.account.auth_backends.AuthenticationBackend',
]


# ============================================================
# ALLAUTH
# ============================================================

ACCOUNT_LOGIN_METHODS = {
    'email',
    'username',
}

ACCOUNT_SIGNUP_FIELDS = [
    'email*',
    'username*',
    'password1*',
    'password2*',
]

ACCOUNT_EMAIL_VERIFICATION = 'optional'

ACCOUNT_UNIQUE_EMAIL = True

ACCOUNT_LOGOUT_ON_GET = True

ACCOUNT_LOGOUT_REDIRECT_URL = '/'

LOGIN_REDIRECT_URL = '/'

ACCOUNT_SIGNUP_REDIRECT_URL = '/profile/'

# ============================================================
# REST FRAMEWORK
# ============================================================

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

    'DEFAULT_THROTTLE_CLASSES': [

        'rest_framework.throttling.AnonRateThrottle',

        'rest_framework.throttling.UserRateThrottle',
    ],

    'DEFAULT_THROTTLE_RATES': {

        'anon': '1000/day',

        'user': '1000/day',
    },

    'DEFAULT_PAGINATION_CLASS':
        'rest_framework.pagination.PageNumberPagination',

    'PAGE_SIZE': 20,
}


# ============================================================
# FRONTEND URL
# ============================================================

FRONTEND_URL = config(
    'FRONTEND_URL',
    default='https://www.oppoglobe.co.za'
)


# ============================================================
# PRODUCTION EMAIL
# ============================================================
#
# IMPORTANT:
# DO NOT use the Django console email backend here.
#
# This is the final deployed application.
# Password reset emails must actually be sent through Gmail SMTP.
#
# EMAIL_HOST_PASSWORD must be a Google App Password.
# ============================================================

EMAIL_BACKEND = (
    'django.core.mail.backends.smtp.EmailBackend'
)

EMAIL_HOST = 'smtp.gmail.com'

EMAIL_PORT = 587

EMAIL_USE_TLS = True

EMAIL_USE_SSL = False

EMAIL_HOST_USER = config(
    'EMAIL_HOST_USER',
    default=''
)

EMAIL_HOST_PASSWORD = config(
    'EMAIL_HOST_PASSWORD',
    default=''
)

DEFAULT_FROM_EMAIL = config(
    'DEFAULT_FROM_EMAIL',
    default='OppoGlobe <ivinakani@gmail.com>'
)

SERVER_EMAIL = DEFAULT_FROM_EMAIL


# ============================================================
# PASSWORD RESET
# ============================================================

PASSWORD_RESET_TIMEOUT = 86400

PASSWORD_RESET_EMAIL_TEMPLATE = (
    'registration/password_reset_email.html'
)


# ============================================================
# CRISPY FORMS
# ============================================================

CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'

CRISPY_TEMPLATE_PACK = 'bootstrap5'


# ============================================================
# PROJECT IDENTIFIERS
# ============================================================

RESIDENT_ID_PREFIX = 'ugr'

BUSINESS_ID_PREFIX = 'lec'


# ============================================================
# DEFAULT PRIMARY KEY
# ============================================================

DEFAULT_AUTO_FIELD = (
    'django.db.models.BigAutoField'
)


# ============================================================
# REAL ESTATE SETTINGS
# ============================================================

REALESTATE_SETTINGS = {

    'ENABLE_REAL_TIME_TRACKING': False,

    'ENABLE_GOOGLE_MAPS': True,

    'GOOGLE_MAPS_API_KEY':
        GOOGLE_MAPS_API_KEY,

    'MAX_NEARBY_RADIUS': 20,

    'DEFAULT_BOOKING_MODE': 'traditional',
}


# ============================================================
# CHANNELS / WEBSOCKETS
# ============================================================

CHANNEL_LAYERS = {

    'default': {

        'BACKEND':
            'channels.layers.InMemoryChannelLayer',
    },
}


# ============================================================
# LOGGING
# ============================================================

LOGGING = {

    'version': 1,

    'disable_existing_loggers': False,

    'formatters': {

        'verbose': {

            'format':
                '%(levelname)s %(asctime)s %(module)s '
                '%(process)d %(thread)d %(message)s',
        },
    },

    'handlers': {

        'console': {

            'level': 'INFO',

            'class':
                'logging.StreamHandler',

            'formatter':
                'verbose',
        },
    },

    'root': {

        'level': 'INFO',

        'handlers': [
            'console'
        ],
    },
}


# ============================================================
# GOOGLE CLOUD STORAGE
# ============================================================

GS_BUCKET_NAME = os.environ.get(
    'GS_BUCKET_NAME',
    'tolleya-storage'
)


def get_google_credentials():
    """
    Load Google Cloud credentials from Railway
    or local development environment.
    """

    # --------------------------------------------------------
    # Railway JSON credentials
    # --------------------------------------------------------

    if 'GS_CREDENTIALS_JSON' in os.environ:

        try:

            creds_json = json.loads(
                os.environ['GS_CREDENTIALS_JSON']
            )

            return (
                service_account
                .Credentials
                .from_service_account_info(
                    creds_json
                )
            )

        except Exception as e:

            print(
                f'Error loading GS_CREDENTIALS_JSON: {e}'
            )


    # --------------------------------------------------------
    # GOOGLE_APPLICATION_CREDENTIALS
    # --------------------------------------------------------

    if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:

        cred_path = os.environ[
            'GOOGLE_APPLICATION_CREDENTIALS'
        ]

        if os.path.exists(cred_path):

            try:

                return (
                    service_account
                    .Credentials
                    .from_service_account_file(
                        cred_path
                    )
                )

            except Exception as e:

                print(
                    f'Error loading GOOGLE_APPLICATION_CREDENTIALS: {e}'
                )


    # --------------------------------------------------------
    # GS_CREDENTIALS
    # --------------------------------------------------------

    if 'GS_CREDENTIALS' in os.environ:

        cred_path = os.environ[
            'GS_CREDENTIALS'
        ]

        if os.path.exists(cred_path):

            try:

                return (
                    service_account
                    .Credentials
                    .from_service_account_file(
                        cred_path
                    )
                )

            except Exception as e:

                print(
                    f'Error loading GS_CREDENTIALS: {e}'
                )


    # --------------------------------------------------------
    # Local credentials
    # --------------------------------------------------------

    local_cred_path = os.path.join(
        BASE_DIR,
        'credentials',
        'service-account-key.json'
    )


    if os.path.exists(local_cred_path):

        try:

            return (
                service_account
                .Credentials
                .from_service_account_file(
                    local_cred_path
                )
            )

        except Exception as e:

            print(
                f'Error loading local credentials: {e}'
            )


    return None


GS_CREDENTIALS = get_google_credentials()


# ============================================================
# GOOGLE CLOUD STORAGE CONFIGURATION
# ============================================================

GS_FILE_OVERWRITE = False

GS_QUERYSTRING_AUTH = False


if GS_CREDENTIALS and GS_BUCKET_NAME:

    STORAGES = {

        'default': {

            'BACKEND':
                'storages.backends.gcloud.GoogleCloudStorage',

            'OPTIONS': {

                'bucket_name':
                    GS_BUCKET_NAME,

                'credentials':
                    GS_CREDENTIALS,

                'file_overwrite':
                    GS_FILE_OVERWRITE,

                'querystring_auth':
                    GS_QUERYSTRING_AUTH,
            },
        },

        'staticfiles': {

            'BACKEND':
                'whitenoise.storage.'
                'CompressedManifestStaticFilesStorage',
        },
    }


    MEDIA_URL = (
        f'https://storage.googleapis.com/'
        f'{GS_BUCKET_NAME}/'
    )


else:

    STORAGES = {

        'default': {

            'BACKEND':
                'django.core.files.storage.FileSystemStorage',
        },

        'staticfiles': {

            'BACKEND':
                'whitenoise.storage.'
                'CompressedManifestStaticFilesStorage',
        },
    }


    MEDIA_URL = '/media/'

    MEDIA_ROOT = os.path.join(
        BASE_DIR,
        'media'
    )


# ============================================================
# WHITENOISE
# ============================================================

STATICFILES_STORAGE = (
    'whitenoise.storage.'
    'CompressedManifestStaticFilesStorage'
)


# ============================================================
# CUSTOM THROTTLE
# ============================================================

from rest_framework.throttling import BaseThrottle


class NoThrottle(BaseThrottle):

    def allow_request(
        self,
        request,
        view
    ):
        return True


# ============================================================
# END OF SETTINGS
# ============================================================