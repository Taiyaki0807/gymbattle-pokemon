import os
from pathlib import Path
from .hosting import read_hosting_config

_config = read_hosting_config(os.environ.get('GYMBATTLE_CONFIG_FILE',
    Path(__file__).resolve().parent.parent / '.pythonanywhere.json'))
os.environ['DJANGO_DEBUG'] = '0'
os.environ['DJANGO_SECRET_KEY'] = _config['secret_key']
os.environ['DJANGO_ALLOWED_HOSTS'] = _config['hostname']
from .settings import *  # noqa: E402,F403

_data_dir = Path(_config['data_dir'])
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3',
                        'NAME': _data_dir / 'db.sqlite3', 'OPTIONS': {'timeout': 20}}}
MEDIA_ROOT = _data_dir / 'media'
CSRF_TRUSTED_ORIGINS = ['https://' + _config['hostname']]
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
