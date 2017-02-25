import os
from django.utils.translation import ugettext_lazy as _

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
PACKAGE_ROOT = os.path.abspath(os.path.dirname(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ("Your Name", "your_email@example.com"),
)

MANAGERS = ADMINS

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "django_rea.sqlite",
    }
}

TIME_ZONE = "UTC"

SITE_ID = 1

USE_TZ = True

MEDIA_ROOT = os.path.join(PACKAGE_ROOT, "site_media", "media")

MEDIA_URL = "/site_media/media/"

STATIC_ROOT = os.path.join(PACKAGE_ROOT, "site_media", "static")

STATIC_URL = "/site_media/static/"

STATICFILES_DIRS = [
    os.path.join(PACKAGE_ROOT, "static"),
]

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

# Make this unique, and don't share it with anybody.
SECRET_KEY = "use ./manage.py generate_secret_key to make this"

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = [
    "django.template.loaders.filesystem.Loader",
    "django.template.loaders.app_directories.Loader",
]

TEMPLATE_CONTEXT_PROCESSORS = [
    "django.contrib.auth.context_processors.auth",
    #"django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.core.context_processors.tz",
    "django.core.context_processors.request",
    "django.contrib.messages.context_processors.messages",
    "django_rea.context_processors.settings",
    "account.context_processors.account",
    "fobi.context_processors.theme",
]

LOGIN_URL = '/account/login/'

LOGIN_EXEMPT_URLS = (
    r"^$",
    r'^membership/',
    r'^membershipthanks/',
    r'^joinaproject/',
    r'^joinaproject-thanks/',
    r'^account/signup/',
    r'^account/password/reset/',
    r'^account/password_reset_sent/',
    r'^captcha/image/',
    r'^i18n/',
    r'^robots.txt$',
)


MIDDLEWARE_CLASSES = [
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    #'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django_rea.login_required_middleware.LoginRequiredMiddleware',
    'account.middleware.LocaleMiddleware',
    #'debug_toolbar.middleware.DebugToolbarMiddleware',
]

ROOT_URLCONF = "ocp.urls"

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = "ocp.wsgi.application"

TEMPLATE_DIRS = [
    os.path.join(PACKAGE_ROOT, "templates"),
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django_comments",

    # theme
    "pinax_theme_bootstrap_account",
    "pinax_theme_bootstrap",
    "django_forms_bootstrap",

    # external
    #'debug_toolbar',
    'django_extensions',
    'easy_thumbnails',
    #'report_builder',
    'pinax.notifications',
    'corsheaders',
    #'django_filters',
    'rest_framework',
    'captcha',

    # `django-fobi` core
    'fobi',

    # `django-fobi` themes
    'fobi.contrib.themes.bootstrap3', # Bootstrap 3 theme
    'fobi.contrib.themes.foundation5', # Foundation 5 theme
    'fobi.contrib.themes.simple', # Simple theme

    # `django-fobi` form elements - fields
    'fobi.contrib.plugins.form_elements.fields.boolean',
    'fobi.contrib.plugins.form_elements.fields.checkbox_select_multiple',
    'fobi.contrib.plugins.form_elements.fields.date',
    'fobi.contrib.plugins.form_elements.fields.date_drop_down',
    'fobi.contrib.plugins.form_elements.fields.datetime',
    'fobi.contrib.plugins.form_elements.fields.decimal',
    'fobi.contrib.plugins.form_elements.fields.email',
    'fobi.contrib.plugins.form_elements.fields.file',
    'fobi.contrib.plugins.form_elements.fields.float',
    'fobi.contrib.plugins.form_elements.fields.hidden',
    'fobi.contrib.plugins.form_elements.fields.input',
    'fobi.contrib.plugins.form_elements.fields.integer',
    'fobi.contrib.plugins.form_elements.fields.ip_address',
    'fobi.contrib.plugins.form_elements.fields.null_boolean',
    'fobi.contrib.plugins.form_elements.fields.password',
    'fobi.contrib.plugins.form_elements.fields.radio',
    #'fobi.contrib.plugins.form_elements.fields.regex',
    'fobi.contrib.plugins.form_elements.fields.select',
    'fobi.contrib.plugins.form_elements.fields.select_model_object',
    'fobi.contrib.plugins.form_elements.fields.select_multiple',
    'fobi.contrib.plugins.form_elements.fields.select_multiple_model_objects',
    'fobi.contrib.plugins.form_elements.fields.slug',
    'fobi.contrib.plugins.form_elements.fields.text',
    'fobi.contrib.plugins.form_elements.fields.textarea',
    'fobi.contrib.plugins.form_elements.fields.time',
    'fobi.contrib.plugins.form_elements.fields.url',

    # `django-fobi` form elements - content elements
    'fobi.contrib.plugins.form_elements.test.dummy',
    'fobi.contrib.plugins.form_elements.content.content_image',
    'fobi.contrib.plugins.form_elements.content.content_text',
    'fobi.contrib.plugins.form_elements.content.content_video',

    # `django-fobo` form handlers
    'fobi.contrib.plugins.form_handlers.db_store',
    'fobi.contrib.plugins.form_handlers.http_repost',
    'fobi.contrib.plugins.form_handlers.mail',

    #'work.fobi_form_callbacks',

    # project
    'django_rea.valueaccounting.apps.ValueAccountingAppConfig',
    'django_rea.equipment.apps.EquipmentAppConfig',
    'django_rea.board.apps.BoardAppConfig',
    'django_rea.api.apps.ApiAppConfig',
    'account',
    'ocp.work',


]

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAuthenticatedOrReadOnly',),
    'PAGINATE_BY': 10,
   'URL_FIELD_NAME': 'api_url',
}

# valueaccounting settings
USE_WORK_NOW = True
SUBSTITUTABLE_DEFAULT = True
MAP_LATITUDE = 45.5601062
MAP_LONGITUDE = -73.7120832
MAP_ZOOM = 11

NOTIFICATION_QUEUE_ALL = True

THUMBNAIL_DEBUG = True

#SOUTH_MIGRATION_MODULES = {
#    'easy_thumbnails': 'easy_thumbnails.south_migrations',
#}

INTERNAL_IPS = ('127.0.0.1',)

DEBUG_TOOLBAR_CONFIG = {
    'INTERCEPT_REDIRECTS': False,
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse"
        }
    },
    "handlers": {
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler"
        }
    },
    "loggers": {
        "django.request": {
            "handlers": ["mail_admins"],
            "level": "ERROR",
            "propagate": True,
        },
    }
}

#LOGGING_CONFIG = None

FIXTURE_DIRS = [
    os.path.join(PROJECT_ROOT, "fixtures"),
]


ACCOUNT_OPEN_SIGNUP = False
ACCOUNT_USE_OPENID = False
ACCOUNT_REQUIRED_EMAIL = False
ACCOUNT_EMAIL_VERIFICATION = False
ACCOUNT_EMAIL_AUTHENTICATION = False
ACCOUNT_LOGIN_REDIRECT_URL = "/accounting/start/"
WORKER_LOGIN_REDIRECT_URL = "/work/home/"
WORKER_LOGOUT_REDIRECT_URL = "/work/work-home/"
ACCOUNT_LOGOUT_REDIRECT_URL = "home"
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 2
LOGIN_URL = '/account/login/'
AUTH_USER_MODEL = "auth.User"

CORS_URLS_REGEX = r'^/api/.*$'
CORS_ORIGIN_ALLOW_ALL = True
CORS_ALLOW_CREDENTIALS = True

USE_FAIRCOINS = False
BROADCAST_FAIRCOINS_LOCK_WAIT_TIMEOUT = None
#id of the group to send payments to
SEND_MEMBERSHIP_PAYMENT_TO = "FC MembershipRequest"

import re
IGNORABLE_404_URLS = (
    re.compile(r'\.(php|cgi)$'),
    re.compile(r'^/phpmyadmin/'),
    re.compile(r'^/apple-touch-icon.*\.png$'),
    re.compile(r'^/favicon\.ico$'),
    re.compile(r'^/robots\.txt$'),
    re.compile(r'^/accounting/timeline/__history__.html\?0$'),
    re.compile(r'^/accounting/timeline/__history__.html$')
)

ALL_WORK_PAGE = "/accounting/work/"


# updating to django 1.5
USE_TZ = True

# updating to prep for django 1.8
TEST_RUNNER = 'django.test.runner.DiscoverRunner'

# Translations and localization settings
USE_I18N = True
USE_L10N = True
LOCALE_PATHS = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), '..', "locale")),
]
LANGUAGE_CODE = 'en'
LANGUAGES = (
  ('en',  _('English')),
  ('es',  _('Spanish')),
)

# Captcha settings
CAPTCHA_CHALLENGE_FUNCT = 'captcha.helpers.math_challenge'
CAPTCHA_LETTER_ROTATION = (-15,15)
CAPTCHA_MATH_CHALLENGE_OPERATOR = 'x'
CAPTCHA_NOISE_FUNCTIONS = (
  'captcha.helpers.noise_dots',
  'captcha.helpers.noise_dots',
)

# ----put all other settings above this line----
try:
    from local_settings import *
except ImportError:
    pass
