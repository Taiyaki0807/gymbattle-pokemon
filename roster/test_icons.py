from io import BytesIO
from tempfile import TemporaryDirectory
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms import modelform_factory
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image
from .models import HeaderIcon


class IconTests(TestCase):
    def setUp(self):
        self.storage = TemporaryDirectory()
        self.settings_override = override_settings(MEDIA_ROOT=self.storage.name)
        self.settings_override.enable()
        self.addCleanup(self.storage.cleanup)
        self.addCleanup(self.settings_override.disable)
        self.user = get_user_model().objects.create_superuser('icon-admin', 'test@example.com', 'test-password')
        self.client.force_login(self.user)
        self.form_class = modelform_factory(HeaderIcon, fields=['key', 'image'])

    def image(self, name='icon.png', size=(32, 32), color='green'):
        output = BytesIO()
        Image.new('RGBA', size, color).save(output, format='PNG')
        return SimpleUploadedFile(name, output.getvalue(), content_type='image/png')

    def upload(self, key='fire'):
        response = self.client.post(reverse('admin:roster_headericon_add'), {'key': key, 'image': self.image()})
        self.assertEqual(response.status_code, 302)
        return HeaderIcon.objects.get(key=key)

    def test_admin_upload_displays_type_and_category_icons(self):
        fire = self.upload()
        physical = self.upload('physical')
        special = self.upload('special')
        response = self.client.get('/')
        self.assertContains(response, fire.image.url)
        self.assertContains(response, physical.image.url, count=18)
        self.assertContains(response, special.image.url, count=18)
        self.assertTrue(fire.image.storage.exists(fire.image.name))
        response = self.client.get('/', {'type': ['fire', 'water']})
        self.assertContains(response, physical.image.url, count=2)
        self.assertContains(response, special.image.url, count=2)
        self.assertContains(response, 'キャラ・タイプ画像の設定')

    def test_each_type_and_category_uses_its_own_character_image(self):
        fire_physical = self.upload('fire_physical')
        fire_special = self.upload('fire_special')
        water_physical = self.upload('water_physical')
        water_special = self.upload('water_special')
        response = self.client.get('/', {'type': ['fire', 'water']})
        headers = response.context['type_headers']
        self.assertEqual([[c['icon_url'] for c in item['categories']] for item in headers],
                         [[fire_physical.image.url, fire_special.image.url],
                          [water_physical.image.url, water_special.image.url]])
        for icon in [fire_physical, fire_special, water_physical, water_special]:
            self.assertContains(response, icon.image.url, count=1)
        response = self.client.get('/', {'type': ['fire']})
        self.assertNotContains(response, water_physical.image.url)
        self.assertNotContains(response, water_special.image.url)
        self.assertContains(response, fire_physical.image.url)

    def test_images_are_after_labels_and_individual_image_overrides_common(self):
        fire = self.upload('fire')
        common = self.upload('physical')
        individual = self.upload('fire_physical')
        response = self.client.get('/', {'type': ['fire', 'water']})
        self.assertContains(response, 'ほのお<img class="header-icon" src="' + fire.image.url)
        self.assertContains(response, '物理<img class="header-icon category-icon" src="' + individual.image.url)
        self.assertContains(response, common.image.url, count=1)
        self.assertContains(response, individual.image.url, count=1)
        individual.delete()
        self.assertContains(self.client.get('/', {'type': ['fire', 'water']}), common.image.url, count=2)

    def test_all_36_character_destinations_are_valid_and_distinct(self):
        from .constants import TYPES, CATEGORIES
        for key, _ in TYPES:
            for category, _ in CATEGORIES:
                form = self.form_class({'key': f'{key}_{category}'}, {'image': self.image()})
                self.assertTrue(form.is_valid(), form.errors)
                form.save()
        self.assertEqual(HeaderIcon.objects.count(), 36)

    def test_replacement_and_delete_restore_fallback(self):
        icon = self.upload()
        old_path = icon.image.name
        response = self.client.post(reverse('admin:roster_headericon_change', args=[icon.pk]),
                                    {'key': 'fire', 'image': self.image(color='red')})
        self.assertEqual(response.status_code, 302)
        icon.refresh_from_db()
        self.assertNotEqual(icon.image.name, old_path)
        self.assertContains(self.client.get('/'), icon.image.url)
        url = icon.image.url
        icon.delete()
        response = self.client.get('/')
        self.assertNotContains(response, url)
        self.assertContains(response, 'type-dot fire')

    def test_duplicate_target_and_invalid_target_rejected(self):
        self.upload()
        for key in ['fire', 'invalid']:
            form = self.form_class({'key': key}, {'image': self.image()})
            self.assertFalse(form.is_valid())
            self.assertIn('key', form.errors)
        self.assertEqual(HeaderIcon.objects.count(), 1)

    def test_bad_large_and_oversized_images_rejected(self):
        files = [SimpleUploadedFile('bad.png', b'not an image', content_type='image/png'),
                 self.image('bad.svg'), self.image(size=(1025, 2)),
                 SimpleUploadedFile('big.png', self.image().read() + b'\0' * (2 * 1024 * 1024), content_type='image/png')]
        for upload in files:
            form = self.form_class({'key': 'fire'}, {'image': upload})
            self.assertFalse(form.is_valid(), upload.name)
            self.assertIn('image', form.errors)
        self.assertEqual(HeaderIcon.objects.count(), 0)

    def test_only_staff_can_upload(self):
        normal = get_user_model().objects.create_user('normal', password='test-password')
        self.client.force_login(normal)
        response = self.client.post(reverse('admin:roster_headericon_add'), {'key': 'fire', 'image': self.image()})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(HeaderIcon.objects.count(), 0)
        self.assertNotContains(self.client.get('/'), 'キャラ・タイプ画像の設定')
