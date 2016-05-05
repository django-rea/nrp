DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ("Bob Haugen", "bob.haugen@gmail.com"),
    ("Lynn Foster", "foster.j.lynn@gmail.com"),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '/home/nrp/webapps/django/valuenetwork/valuenetwork/valuenetwork.sqlite'
    }
}

# Make this unique, and don't share it with anybody.
SECRET_KEY = "b-h#ml28a24&gz)#_-w5*hefhcx)7*w6-sqg9z0_z^q(wn_gix"

SITE_ID = 1

STATIC_URL = "http:/nrp.webfactional.com/static/"
STATIC_ROOT = "/home/nrp/webapps/static/"

MEDIA_URL = "/site_media/"

EMAIL_HOST = 'smtp.webfaction.com'
EMAIL_HOST_USER = 'nrp'
EMAIL_HOST_PASSWORD = 'rEA8aqyMjVz5Sy0R'
DEFAULT_FROM_EMAIL = 'mailer@nrp.webfactional.com'
SERVER_EMAIL = 'mailer@nrp.webfactional.com'
EMAIL_SUBJECT_PREFIX = '[NRP]'
SEND_BROKEN_LINK_EMAILS = True

#Europe
MAP_LATITUDE = 48.1293204
MAP_LONGITUDE = 4.153537
MAP_ZOOM = 4

