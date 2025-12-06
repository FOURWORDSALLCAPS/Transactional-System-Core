import os
from pathlib import Path

import dj_database_url
import django
from env_settings import EnvSettings

from webapp.loguru_django import LoguruInterceptHandler

ENV = EnvSettings()

# Build paths inside the webapp like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

SECRET_KEY = ENV.DJ.SECRET_KEY

DEBUG = ENV.DJ.DEBUG

ALLOWED_HOSTS = ENV.DJ.ALLOWED_HOSTS

CSRF_TRUSTED_ORIGINS = ENV.DJ.CSRF_TRUSTED_ORIGINS

# Application definition

INSTALLED_APPS = [
    "django.forms",
    # contrib apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # third party apps
    "transfer.apps.TransferConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "webapp.urls"

_TEMPLATE_LOADERS = [
    "django.template.loaders.filesystem.Loader",
    "django.template.loaders.app_directories.Loader",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates",
            # The path to Django form templates should be specified explicitly if FORM_RENDERER settings is overrided
            Path(django.__path__[0]) / "forms" / "templates",
        ],
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
            # Cached loader is automatically enabled if OPTIONS['loaders'] is not specified, so it should
            # define loaders explicitly to make it possible to disable caching during development
            "loaders": _TEMPLATE_LOADERS,
        },
    },
]
# Use non default form renderer to fix aggressive template caching. It slows down the development
# of widget templates dramatically.
FORM_RENDERER = "django.forms.renderers.TemplatesSetting"

WSGI_APPLICATION = "webapp.wsgi.application"

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

if not ENV.DJ.DEBUG:
    DATABASES = {
        "default": dj_database_url.config(
            default=ENV.get_postgres_uri,
            engine="django.db.backends.postgresql_psycopg2",
        ),
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": "db_sqlite3",
        },
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

TIME_ZONE = "Europe/Moscow"

USE_I18N = True

USE_TZ = True

STATIC_URL = ENV.DJ.STATIC_URL
STATIC_ROOT = "/collected_static"

MEDIA_URL = ENV.DJ.MEDIA_URL
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

STATICFILES_DIRS = [BASE_DIR / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

DISABLE_DARK_MODE = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "loguru_console": {
            "()": LoguruInterceptHandler,
            "level": 1,
        },
    },
    "loggers": {
        "": {
            "handlers": ["loguru_console"],
            "level": "INFO",
            "propagate": True,
        },
        "django.server": {
            "handlers": ["loguru_console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["loguru_console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["loguru_console"],
            "level": "INFO",
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["loguru_console"],
    },
}
