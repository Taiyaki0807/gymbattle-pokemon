from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from .constants import TYPES
from .models import Member, Participation


class RosterTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('manager', password='test-password-123')
        self.client.force_login(self.user)

    def payload(self, name='テストメンバー'):
        data = {'name': name, 'notes': 'チームメモ'}
        for key, _ in TYPES:
            data[f'status_{key}'] = 'no'
            data[f'condition_{key}'] = ''
        data.update(status_fire='conditional', condition_fire='特定の編成時', status_water='yes')
        return data

    def create_member(self, name='テストメンバー'):
        response = self.client.post(reverse('roster:create'), self.payload(name))
        self.assertRedirects(response, reverse('roster:list'))
        return Member.objects.get(name=name)

    def test_all_views_require_login(self):
        member = self.create_member()
        self.client.logout()
        for url in [reverse('roster:list'), reverse('roster:create'),
                    reverse('roster:edit', args=[member.pk]), reverse('roster:delete', args=[member.pk])]:
            self.assertEqual(self.client.get(url).status_code, 302)
            self.assertEqual(self.client.post(url, {}).status_code, 302)

    def test_create_persists_all_18_types_and_condition(self):
        member = self.create_member()
        self.assertEqual(member.participations.count(), 18)
        self.assertEqual(member.participations.get(pokemon_type='fire').condition, '特定の編成時')
        response = self.client.get(reverse('roster:list'))
        self.assertContains(response, 'テストメンバー')
        self.assertContains(response, '特定の編成時')
        for _, label in TYPES:
            self.assertContains(response, label)

    def test_update_preserves_member_and_updates_records(self):
        member = self.create_member()
        data = self.payload('新しい名前')
        data['status_fire'] = 'yes'
        response = self.client.post(reverse('roster:edit', args=[member.pk]), data)
        self.assertRedirects(response, reverse('roster:list'))
        member.refresh_from_db()
        self.assertEqual(member.name, '新しい名前')
        self.assertEqual(member.participations.count(), 18)
        self.assertEqual(member.participations.get(pokemon_type='fire').status, 'yes')
        self.assertContains(self.client.get(reverse('roster:edit', args=[member.pk])), '新しい名前')

    def test_filter_matches_type_and_status_on_same_record(self):
        self.create_member('あおい')
        other = self.create_member('あかり')
        other.participations.filter(pokemon_type='fire').update(status='no')
        response = self.client.get('/', {'type': 'fire', 'status': 'conditional'})
        self.assertContains(response, 'あおい')
        self.assertNotContains(response, 'あかり')
        response = self.client.get('/', {'q': 'あか', 'type': 'water', 'status': 'yes'})
        self.assertContains(response, 'あかり')
        self.assertNotContains(response, 'あおい')

    def test_status_only_invalid_filters_and_empty_result(self):
        self.create_member()
        self.assertEqual(len(self.client.get('/', {'status': 'conditional'}).context['rows']), 1)
        self.assertEqual(len(self.client.get('/', {'type': 'invalid', 'status': 'invalid'}).context['rows']), 1)
        self.assertContains(self.client.get('/', {'q': '存在しない名前'}), '該当するメンバーがいません')

    def test_invalid_and_duplicate_input_does_not_partially_save(self):
        self.create_member()
        data = self.payload()
        self.assertEqual(self.client.post(reverse('roster:create'), data).status_code, 200)
        data = self.payload('別の人')
        data['status_fire'] = 'invalid'
        response = self.client.post(reverse('roster:create'), data)
        self.assertTrue(response.context['form'].errors)
        self.assertEqual(Member.objects.count(), 1)
        self.assertEqual(Participation.objects.count(), 18)
        data = self.payload('   ')
        self.assertEqual(self.client.post(reverse('roster:create'), data).status_code, 200)
        self.assertEqual(Member.objects.count(), 1)

    def test_delete_requires_post_and_cascades(self):
        member = self.create_member()
        url = reverse('roster:delete', args=[member.pk])
        self.assertContains(self.client.get(url), '削除する')
        self.assertTrue(Member.objects.filter(pk=member.pk).exists())
        self.assertRedirects(self.client.post(url), reverse('roster:list'))
        self.assertEqual(Member.objects.count(), 0)
        self.assertEqual(Participation.objects.count(), 0)

    def test_csrf_protection(self):
        from django.test import Client
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        member = self.create_member()
        for url in [reverse('roster:create'), reverse('roster:edit', args=[member.pk]), reverse('roster:delete', args=[member.pk])]:
            self.assertEqual(client.post(url, self.payload('別名')).status_code, 403)

    def test_database_constraints(self):
        member = self.create_member()
        for values in [{'pokemon_type': 'fire', 'status': 'yes'},
                       {'pokemon_type': 'invalid', 'status': 'yes'}]:
            with self.assertRaises(IntegrityError), transaction.atomic():
                Participation.objects.create(member=member, **values)

    def test_html_is_escaped_and_missing_member_returns_404(self):
        self.create_member('<script>alert(1)</script>')
        response = self.client.get('/')
        self.assertNotContains(response, '<script>alert(1)</script>')
        self.assertContains(response, '&lt;script&gt;')
        self.assertEqual(self.client.get(reverse('roster:edit', args=[999])).status_code, 404)

    def test_empty_state_and_login_page(self):
        self.assertContains(self.client.get('/'), '最初のメンバーを登録しましょう')
        self.client.logout()
        self.assertContains(self.client.get(reverse('login')), 'ログイン')
