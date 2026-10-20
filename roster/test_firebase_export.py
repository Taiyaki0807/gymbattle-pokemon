import importlib.util
import json
from pathlib import Path
import sqlite3
from contextlib import closing
from tempfile import TemporaryDirectory
from django.conf import settings
from django.test import SimpleTestCase


class FirebaseExportTests(SimpleTestCase):
    def test_export_preserves_ratings_and_excludes_accounts_and_images(self):
        spec = importlib.util.spec_from_file_location('export_roster', settings.BASE_DIR / 'scripts/export_for_firebase.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with TemporaryDirectory() as directory:
            source, output = Path(directory) / 'source.sqlite3', Path(directory) / 'team.json'
            with closing(sqlite3.connect(source)) as db:
                db.execute('CREATE TABLE roster_member (id INTEGER, name TEXT, notes TEXT)')
                db.execute('CREATE TABLE roster_participation (member_id INTEGER, pokemon_type TEXT, category TEXT, status TEXT, condition TEXT)')
                db.execute('INSERT INTO roster_member VALUES (1, ?, ?)', ('あおい', 'メモ'))
                db.execute('INSERT INTO roster_participation VALUES (1, ?, ?, ?, ?)', ('fire', 'physical', 'excellent', '編成条件'))
                db.execute('CREATE TABLE auth_user (password TEXT)')
                db.execute("INSERT INTO auth_user VALUES ('test-only-not-exported')")
                db.commit()
            self.assertEqual(module.export(source, output), 1)
            text = output.read_text(encoding='utf-8')
            data = json.loads(text)
            self.assertNotIn('test-only-not-exported', text)
            self.assertEqual(data['members'][0]['name'], 'あおい')
            self.assertEqual(len(data['members'][0]['ratings']), 36)
            self.assertEqual(data['members'][0]['ratings']['fire_physical'], {'status': 'excellent', 'condition': '編成条件'})
            self.assertEqual(data['members'][0]['ratings']['fire_special']['status'], 'no')
            with self.assertRaises(ValueError):
                module.export(source, output)
