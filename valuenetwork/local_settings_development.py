
#for a development machine
DEBUG = True

TEMPLATE_DEBUG = DEBUG

#this is nice for development
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'valuenetwork.sqlite'
    }
}


# valueaccounting settings can be overridden
USE_WORK_NOW = False
SUBSTITUTABLE_DEFAULT = False

STATIC_URL = "/static/"

#example: Greece
MAP_LATITUDE = 38.2749497
MAP_LONGITUDE = 23.8102717
MAP_ZOOM = 6

#and you can override any other settings in settings.py