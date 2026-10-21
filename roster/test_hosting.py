import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase
from config.hosting import read_hosting_config


class HostingTests(SimpleTestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        spec = importlib.util.spec_from_file_location('configure_hosting', settings.BASE_DIR / 'scripts/configure_pythonanywhere.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.configure = module.configure

    def test_setup_is_repeatable_without_rotating_key_or_overwriting_data(self):
        config_path = self.configure(self.root, 'example.pythonanywhere.com', self.root / 'data')
        config = read_hosting_config(config_path)
        self.assertGreaterEqual(len(config['secret_key']), 50)
        database = self.root / 'data/db.sqlite3'
        database.write_bytes(b'existing-data')
        self.configure(self.root, 'example.pythonanywhere.com', self.root / 'data')
        self.assertEqual(read_hosting_config(config_path), config)
        self.assertEqual(database.read_bytes(), b'existing-data')
        self.assertIn(repr(str(self.root)), (self.root / 'deploy/pythonanywhere_wsgi.generated.py').read_text())
        with self.assertRaises(ValueError):
            self.configure(self.root, 'other.pythonanywhere.com', self.root / 'data')

    def test_missing_or_invalid_settings_fail_closed(self):
        with self.assertRaises(ImproperlyConfigured):
            read_hosting_config(self.root / 'missing.json')
        for hostname in ['*', 'example.com', 'https://example.pythonanywhere.com']:
            with self.assertRaises(ValueError):
                self.configure(self.root, hostname, self.root / 'data')
        path = self.configure(self.root, 'example.eu.pythonanywhere.com', self.root / 'data')
        config = json.loads(path.read_text())
        config['secret_key'] = 'weak'
        path.write_text(json.dumps(config))
        with self.assertRaises(ImproperlyConfigured):
            read_hosting_config(path)

    def test_production_checks_and_wsgi_import(self):
        config_path = self.configure(self.root, 'example.pythonanywhere.com', self.root / 'data')
        environment = os.environ.copy()
        environment['GYMBATTLE_CONFIG_FILE'] = str(config_path)
        environment['DJANGO_SETTINGS_MODULE'] = 'config.pythonanywhere'
        result = subprocess.run([sys.executable, 'manage.py', 'check', '--deploy', '--fail-level', 'WARNING'],
                                cwd=settings.BASE_DIR, env=environment, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        code = 'from config.pythonanywhere_wsgi import application; from django.conf import settings; assert not settings.DEBUG; assert settings.SECURE_SSL_REDIRECT; assert settings.ALLOWED_HOSTS == ["example.pythonanywhere.com"]; assert str(settings.MEDIA_ROOT).endswith("media"); print("WSGI OK")'
        code += '; from django.test import Client; client = Client(); assert client.get("/", HTTP_HOST="example.pythonanywhere.com").status_code == 301; assert client.get("/", secure=True, HTTP_HOST="example.pythonanywhere.com").status_code == 302; assert client.get("/media/test.png", secure=True, HTTP_HOST="example.pythonanywhere.com").status_code == 302'
        result = subprocess.run([sys.executable, '-c', code], cwd=settings.BASE_DIR, env=environment, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
