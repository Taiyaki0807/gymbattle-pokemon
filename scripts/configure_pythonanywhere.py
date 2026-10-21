"""Configure a PythonAnywhere checkout without storing secrets in Git."""
import argparse
import json
import os
from pathlib import Path
import re
import secrets


def configure(project, hostname, data_dir):
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]*\.(?:eu\.)?pythonanywhere\.com', hostname):
        raise ValueError('Use your app hostname, for example username.pythonanywhere.com')
    project = Path(project).resolve()
    data_dir = Path(data_dir).resolve()
    config_path = project / '.pythonanywhere.json'
    if config_path.exists():
        config = json.loads(config_path.read_text(encoding='utf-8'))
        if config['hostname'] != hostname or Path(config['data_dir']) != data_dir:
            raise ValueError('Existing configuration differs. It was not overwritten.')
    else:
        config = {'hostname': hostname, 'secret_key': secrets.token_urlsafe(64), 'data_dir': str(data_dir)}
        with os.fdopen(os.open(config_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w', encoding='utf-8') as stream:
            json.dump(config, stream, indent=2)
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / 'media').mkdir(exist_ok=True)
    deploy_dir = project / 'deploy'
    deploy_dir.mkdir(exist_ok=True)
    snippet = 'import sys\n' + f'sys.path.insert(0, {str(project)!r})\n' + 'from config.pythonanywhere_wsgi import application\n'
    (deploy_dir / 'pythonanywhere_wsgi.generated.py').write_text(snippet, encoding='utf-8')
    return config_path


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--hostname', required=True)
    parser.add_argument('--data-dir', type=Path)
    args = parser.parse_args()
    project = Path(__file__).resolve().parent.parent
    try:
        configure(project, args.hostname, args.data_dir or project / 'data')
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print('Private configuration prepared. Existing database and images were not modified.')
    print('Next: python manage.py migrate --settings=config.pythonanywhere')
    print('Then: python manage.py collectstatic --noinput --settings=config.pythonanywhere')
    print('WSGI snippet: deploy/pythonanywhere_wsgi.generated.py')
