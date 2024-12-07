# Django settings for Experiment project.

import pymysql
pymysql.install_as_MySQLdb()

from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv() 

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-)k*f=c1$ph%n_#8igq7dt%om(a#frr0)0!(0rvoxv7l_0b-%bt'
DEBUG = True
ALLOWED_HOSTS = [
    '48e535w8p4.execute-api.ap-south-1.amazonaws.com',
    '48e535w8p4.execute-api.ap-south-1.amazonaws.com/dev',  # Optional, depends on setup
    '3.108.32.137'
    '127.0.0.1',
    'localhost'
]


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'Experiment',  # Your app containing the model
    'storages',
]

APPEND_SLASH = False  # Add this if you want to disable automatic slash appending

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'Experiment.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates',  # Ensure your custom templates directory is included
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'Experiment.wsgi.application'

# Define multiple databases in the DATABASES setting
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': "ONLINE",  # Default database
        'USER': "admin",
        'PASSWORD': "HHepo6YA0NPfYrVkegAz",
        'HOST': "stpl-ktm.cb2ymckcwftz.ap-south-1.rds.amazonaws.com",
        'PORT': '3306',
        'OPTIONS': {
            'charset': 'utf8mb4',
            'collation': 'utf8mb4_unicode_ci',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'autocommit': True,
        }
    },
    'custmas': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': "CUSTMAS",  # Database 1
        'USER': "admin",
        'PASSWORD': "HHepo6YA0NPfYrVkegAz",
        'HOST': "stpl-ktm.cb2ymckcwftz.ap-south-1.rds.amazonaws.com",
        'PORT': '3306',
        'OPTIONS': {
            'charset': 'utf8mb4',
            'collation': 'utf8mb4_unicode_ci',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'autocommit': True,
        }
    },
    'onlinechit': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': "onlinechit",  # Database 2
        'USER': "admin",
        'PASSWORD': "HHepo6YA0NPfYrVkegAz",
        'HOST': "stpl-ktm.cb2ymckcwftz.ap-south-1.rds.amazonaws.com",
        'PORT': '3306',
        'OPTIONS': {
            'charset': 'utf8mb4',
            'collation': 'utf8mb4_unicode_ci',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'autocommit': True,
        }
    },
    'service': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': "Service",  # Database 3
        'USER': "admin",
        'PASSWORD': "HHepo6YA0NPfYrVkegAz",
        'HOST': "stpl-ktm.cb2ymckcwftz.ap-south-1.rds.amazonaws.com",
        'PORT': '3306',
        'OPTIONS': {
            'charset': 'utf8mb4',
            'collation': 'utf8mb4_unicode_ci',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'autocommit': True,
        }
    }
}

# AWS S3 configurations
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
AWS_REGION = os.getenv('AWS_REGION')  # Default to 'us-west-1' if not specified

# Configure default file storage to use S3
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

# Additional optional settings
AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"
AWS_DEFAULT_ACL = None  # Optional: This makes sure files are private by default
AWS_QUERYSTRING_AUTH = False  # Optional: Set to False for non-expiring URLs
AWS_S3_FILE_OVERWRITE = False  # Optional: Prevent file overwriting
AWS_S3_REGION_NAME = AWS_REGION  # Optional: Specify the region if you are in a different region
AWS_S3_SIGNATURE_VERSION = 's3v4'  # Optional: Explicitly set signature version if needed

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-otp',
    }
}

USE_TZ = True
TIME_ZONE = 'Asia/Kolkata'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
}

CORS_ALLOWED_ORIGINS = [
    "48e535w8p4.execute-api.ap-south-1.amazonaws.com/dev"
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
