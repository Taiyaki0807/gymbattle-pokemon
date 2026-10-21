from io import BytesIO
from tempfile import TemporaryDirectory
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from PIL import Image
from .models import HeaderIcon, Member, Participation


class TeamAccessTests(TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.override = override_settings(MEDIA_ROOT=self.directory.name)
        self.override.enable()
        self.addCleanup(self.directory.cleanup)
        self.addCleanup(self.override.disable)
        User = get_user_model()
        self.manager = User.objects.create_superuser('manager', 'test@example.com', 'test-password')
        self.editor = User.objects.create_user('member', password='test-password')
        buffer = BytesIO()
        Image.new('RGB', (8, 8), 'green').save(buffer, 'PNG')
        self.icon = HeaderIcon(key='fire_physical')
        self.icon.image.save('test.png', ContentFile(buffer.getvalue()))
        self.member = Member.objects.create(name='チームメンバー')

    def test_every_active_nonstaff_user_can_edit(self):
        self.assertFalse(self.editor.is_staff)
        self.client.login(username='member', password='test-password')
        self.assertEqual(self.client.get('/').status_code, 200)
        response = self.client.post(reverse('roster:participation', args=[self.member.pk, 'fire', 'physical']),
                                   {'status': 'excellent', 'condition': ''}, HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Participation.objects.get(member=self.member).status, 'excellent')
        self.assertNotContains(self.client.get('/'), '利用者アカウント')

    def test_manager_deactivation_revokes_existing_sessions_and_login(self):
        self.client.login(username='member', password='test-password')
        second_device = Client()
        second_device.login(username='member', password='test-password')
        manager = Client()
        manager.force_login(self.manager)
        # Change the same "有効" field exposed by the standard Django user admin.
        response = manager.post(reverse('admin:auth_user_change', args=[self.editor.pk]), {
            'username': self.editor.username, 'first_name': '', 'last_name': '', 'email': '',
            'date_joined_0': self.editor.date_joined.strftime('%Y-%m-%d'),
            'date_joined_1': self.editor.date_joined.strftime('%H:%M:%S'),
            'last_login_0': '', 'last_login_1': '',
        })
        self.assertEqual(response.status_code, 302)
        self.editor.refresh_from_db()
        self.assertFalse(self.editor.is_active)
        for device in [self.client, second_device]:
            for url in ['/', self.icon.image.url]:
                self.assertEqual(device.get(url).status_code, 302)
            response = device.post(reverse('roster:edit', args=[self.member.pk]), {'name': '変更不可'})
            self.assertEqual(response.status_code, 302)
        self.member.refresh_from_db()
        self.assertEqual(self.member.name, 'チームメンバー')
        self.assertFalse(Client().login(username='member', password='test-password'))
        self.assertEqual(manager.get('/').status_code, 200)

    def test_images_require_active_login_and_disable_caching(self):
        self.assertEqual(self.client.get(self.icon.image.url).status_code, 302)
        self.client.force_login(self.editor)
        response = self.client.get(self.icon.image.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/png')
        self.assertIn('no-store', response['Cache-Control'])
        self.assertIn('private', response['Cache-Control'])
        response.close()

    def test_images_are_protected_in_production_too(self):
        with override_settings(DEBUG=False):
            self.assertEqual(self.client.get(self.icon.image.url).status_code, 302)
            self.client.force_login(self.editor)
            response = self.client.get(self.icon.image.url)
            self.assertEqual(response.status_code, 200)
            response.close()

    def test_missing_and_traversal_paths_do_not_expose_files(self):
        self.client.force_login(self.editor)
        for path in ['missing.png', '../manage.py', '../../manage.py']:
            response = self.client.get(reverse('member_image', args=[path]))
            self.assertEqual(response.status_code, 404)

    def test_manager_can_open_user_admin_and_member_cannot(self):
        self.client.force_login(self.manager)
        self.assertContains(self.client.get('/'), '利用者アカウント')
        self.assertEqual(self.client.get(reverse('admin:auth_user_changelist')).status_code, 200)
        self.client.force_login(self.editor)
        self.assertEqual(self.client.get(reverse('admin:auth_user_changelist')).status_code, 302)
