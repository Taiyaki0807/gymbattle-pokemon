import json
import re
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured


def read_hosting_config(path):
    try:
        config = json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        raise ImproperlyConfigured('Run scripts/configure_pythonanywhere.py first.') from error
    hostname = config.get('hostname', '')
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]*\.(?:eu\.)?pythonanywhere\.com', hostname):
        raise ImproperlyConfigured('A PythonAnywhere application hostname is required.')
    if len(config.get('secret_key', '')) < 50:
        raise ImproperlyConfigured('A private random secret key of at least 50 characters is required.')
    data_dir = Path(config.get('data_dir', ''))
    if not data_dir.is_absolute():
        raise ImproperlyConfigured('data_dir must be an absolute path.')
    return config
