'''
When a perminant url landing page is established it should be included in the ALLOWED HOST variable 
'''


from pathlib import Path
import os 

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
LOG_LEVEL = 'INFO' ## Flag
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

LOGS_DIR = os.path.join(BASE_DIR, 'logs')
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        },
    },
    'handlers': {
        'file': {
            'level': LOG_LEVEL,
            'class': 'logging.FileHandler',
            'filename': os.path.join(LOGS_DIR, 'ServerLog.log'),
            'formatter': 'standard'
        },
        'background_file': {
            'level': LOG_LEVEL,
            'class': 'logging.FileHandler',
            'filename': os.path.join(LOGS_DIR, 'BackgroundTasksLog.log'),
            'formatter': 'standard',  # Use the 'standard' formatter
        },
        'sqlFile': {
            'level': LOG_LEVEL,
            'class': 'logging.FileHandler',
            'filename': os.path.join(LOGS_DIR, 'SqlLog.log'),
            'formatter': 'standard',  # Use the 'standard' formatter
        },
    },
    'loggers': {
        'server': {
            'handlers': ['file'],
            'level': LOG_LEVEL,
            'propagate': True,
        },
        'background_tasks': {  # Create a logger for background tasks
            'handlers': ['background_file'],  # Use the 'background_file' handler
            'level': LOG_LEVEL,  # Set the logging level for background tasks
            'propagate': True,
        },
        'sqlLogger': {  # Create a logger for background tasks
            'handlers': ['sqlFile'],  # Use the 'background_file' handler
            'level': LOG_LEVEL,  # Set the logging level for background tasks
            'propagate': True,
        },
    },
}
os.makedirs(LOGS_DIR, exist_ok=True)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-x^ek8@8+=301_nj87hs4tf2d$$28%1n2lj#n81dga5v_a3ztb-'


# ALLOWED_HOSTS = ['169.254.129.2','hpclockifyapi.azurewebsites.net', '169.254.130.3','169.254.129.3', 'localhost', '127.0.0.1', '169.254.130.2',
# '20.237.180.234','20.237.181.23','20.237.181.49','20.228.97.254','20.228.99.26','20.237.179.112','104.40.10.200','104.40.9.245','104.40.14.130','104.40.3.249','104.40.18.254','104.40.18.248','40.112.243.106']
ALLOWED_HOSTS = ["*"]

# Application definition

INSTALLED_APPS = [
    'HpClockfiyApi',
    'rest_framework',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # 'asgiref.middleware.AsyncMiddleware',
]

ROOT_URLCONF = 'HpClockfiyApi.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

# WSGI_APPLICATION = 'HpClockfiyApi.wsgi.application'

ASGI_APPLICATION = 'HpClockfiyApi.asgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'mssql',
        'NAME': 'hpdb',
        'USER': 'hpUser',
        'PASSWORD': '0153HP!!',
        'HOST': 'hpcs.database.windows.net',  # e.g., 'localhost' or IP address
        'PORT': 1433,  # Default is usually '1433'
        'OPTIONS': {
            'driver':'ODBC Driver 18 for SQL Server',  # Change to your ODBC driver version
        }       
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

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


# Celery Configuration
# Celery Configuration
# CELERY_BROKER_URL = 'amqp://guest:guest@localhost'
# task_ignore_result = False
# SQL Server result backend
# CELERY_RESULT_BACKEND = 'django-db'

# CELERY_RESULT_BACKEND = 'mssql+pyodbc://hpUser:0153HP!!@hpcs.database.windows.net:1433/hpdb?driver=ODBC+Driver+18+for+SQL+Server'
# CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
# # App to discover tasks
# CELERY_APP = 'HpClockfiyApi'
# CELERY_WORKER_CONCURRENCY = 4
# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

USE_TZ = False

TIME_ZONE = 'America/Edmonton'

USE_I18N = True



# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
