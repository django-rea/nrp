"""
    You want a local_settings.py file in the same directory
    as settings.py.
    settings.py will import it, if it exists
    and local_settings will override settings
    for the setting with the same name.
    
    You also want your localsettings.py to be different
    on a development machine and a server,
    in ways that will be mentioned below.
    
    Note: don't use this local_settings_example.py.
    It is internally inconsistent to show some choices.
    Create your own local_settings.py file 
    to fit your own needs.
    
"""

#for a development machine
DEBUG = True
#for a server
DEBUG = False
TEMPLATE_DEBUG = DEBUG

#this is nice for development
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'valuenetwork.sqlite'
    }
}
#for a server, you want a real database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.', # Add 'postgresql_psycopg2', 'mysql', or 'oracle'.
        'NAME': '',                      
        'USER': '',                      
        'PASSWORD': '',                  
        'HOST': '',                      
        'PORT': '',                      # Set to empty string for default.
    }
}

STATIC_URL = "/static/"

# valueaccounting settings can be overridden
USE_WORK_NOW = False
SUBSTITUTABLE_DEFAULT = False

#example: Greece
MAP_LATITUDE = 38.2749497
MAP_LONGITUDE = 23.8102717
MAP_ZOOM = 6

STATIC_URL = "/static/"

#and you can override any other settings in settings.py