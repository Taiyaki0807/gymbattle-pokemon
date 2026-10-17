from django.contrib.auth import get_user_model
from django.db import connection, IntegrityError, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse
from .constants import TYPES, CATEGORIES
from .models import Member, Participation


class RosterTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('manager', password='test-password-123')
        self.client.force_login(self.user)

    def add(self):
        response = self.client.post(reverse('roster:create'), HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        return Member.objects.get(pk=response.json()['id'])

    def cell_url(self, member, kind='physical', key='fire'):
        return reverse('roster:participation', args=[member.pk, key, kind])

    def test_plus_creates_36_cells_and_unique_names(self):
        first, second = self.add(), self.add()
        self.assertNotEqual(first.name, second.name)
        self.assertEqual(first.participations.count(), 36)
        self.assertEqual(set(first.participations.values_list('status', flat=True)), {'no'})
        self.assertEqual(set(first.participations.values_list('category', flat=True)), {'physical', 'special'})

    def test_table_headers_order_and_inline_controls(self):
        member = self.add()
        response = self.client.get('/')
        self.assertEqual(TYPES[-1], ('normal', 'ノーマル'))
        self.assertEqual(len(response.context['rows'][0]['cells']), 36)
        for _, label in TYPES + CATEGORIES:
            self.assertContains(response, label)
        for label in ['◎', '〇', '△', '×']:
            self.assertContains(response, label)
        self.assertContains(response, 'colspan="2"', count=18)
        self.assertContains(response, self.cell_url(member))
        self.assertNotContains(response, '不可')
        self.assertContains(response, 'メンバーを1人追加')

    def test_each_symbol_saves_independently_for_both_categories(self):
        member = self.add()
        for kind, _ in CATEGORIES:
            for symbol in Participation.Status.values:
                response = self.client.post(self.cell_url(member, kind),
                    {'status': symbol, 'condition': '条件メモ'}, HTTP_ACCEPT='application/json')
                self.assertEqual(response.status_code, 200)
                record = member.participations.get(pokemon_type='fire', category=kind)
                self.assertEqual(record.status, symbol)
                self.assertEqual(record.condition, '条件メモ')
        self.client.post(self.cell_url(member), {'status': 'excellent', 'condition': ''})
        self.assertEqual(member.participations.get(pokemon_type='fire', category='physical').status, 'excellent')
        self.assertEqual(member.participations.get(pokemon_type='fire', category='special').status, 'no')
        self.assertContains(self.client.get('/'), 'value="excellent" selected')

    def test_inline_name_notes_and_duplicate_validation(self):
        member, other = self.add(), self.add()
        url = reverse('roster:edit', args=[member.pk])
        response = self.client.post(url, {'name': 'あおい', 'notes': '既存メモ'}, HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        member.refresh_from_db()
        self.assertEqual((member.name, member.notes), ('あおい', '既存メモ'))
        for name in [other.name, '   ', 'a' * 61]:
            self.assertEqual(self.client.post(url, {'name': name}, HTTP_ACCEPT='application/json').status_code, 400)
        member.refresh_from_db()
        self.assertEqual(member.name, 'あおい')
        self.assertEqual(member.participations.count(), 36)

    def test_filter_uses_same_type_category_status(self):
        member, other = self.add(), self.add()
        member.participations.filter(pokemon_type='fire', category='physical').update(status='excellent')
        other.participations.filter(pokemon_type='fire', category='special').update(status='excellent')
        response = self.client.get('/', {'type': 'fire', 'category': 'physical', 'status': 'excellent'})
        self.assertEqual([r['member'].pk for r in response.context['rows']], [member.pk])
        response = self.client.get('/', {'q': other.name, 'type': 'fire', 'category': 'special', 'status': 'excellent'})
        self.assertEqual([r['member'].pk for r in response.context['rows']], [other.pk])
        self.assertEqual(len(self.client.get('/', {'status': 'excellent'}).context['rows']), 2)

    def test_invalid_cell_inputs_cannot_mutate_data(self):
        member = self.add()
        for data in [{'status': 'invalid'}, {'status': 'excellent', 'condition': 'x' * 201}]:
            self.assertEqual(self.client.post(self.cell_url(member), data, HTTP_ACCEPT='application/json').status_code, 400)
        self.assertEqual(self.client.post(self.cell_url(member, 'invalid'), {'status': 'yes'}).status_code, 404)
        self.assertEqual(self.client.post(self.cell_url(member, key='invalid'), {'status': 'yes'}).status_code, 404)
        self.assertEqual(self.client.get(self.cell_url(member)).status_code, 405)
        self.assertEqual(member.participations.filter(status='no').count(), 36)

    def test_authentication_and_csrf(self):
        member = self.add()
        urls = [reverse('roster:create'), reverse('roster:edit', args=[member.pk]),
                self.cell_url(member), reverse('roster:delete', args=[member.pk])]
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        for url in urls:
            self.assertEqual(csrf_client.post(url, {}).status_code, 403)
        self.client.logout()
        for url in urls:
            self.assertEqual(self.client.post(url, {}).status_code, 302)
        self.assertEqual(self.client.get('/').status_code, 302)
        self.assertContains(self.client.get(reverse('login')), 'ログイン')

    def test_get_never_creates_and_form_page_is_replaced(self):
        self.assertRedirects(self.client.get(reverse('roster:create')), '/')
        self.assertEqual(Member.objects.count(), 0)
        member = self.add()
        self.assertEqual(self.client.get(reverse('roster:edit', args=[member.pk])).status_code, 302)

    def test_delete_confirmation_and_cascade(self):
        member = self.add()
        url = reverse('roster:delete', args=[member.pk])
        self.assertContains(self.client.get(url), '削除する')
        self.assertEqual(Member.objects.count(), 1)
        self.assertRedirects(self.client.post(url), '/')
        self.assertEqual(Participation.objects.count(), 0)

    def test_database_constraints(self):
        member = self.add()
        for key, category, symbol in [('fire', 'physical', 'yes'), ('invalid', 'physical', 'yes'),
                                      ('fire', 'invalid', 'yes'), ('fire', 'physical', 'invalid')]:
            with self.assertRaises(IntegrityError), transaction.atomic():
                Participation.objects.create(member=member, pokemon_type=key, category=category, status=symbol)

    def test_empty_filters_and_html_escaping(self):
        self.assertContains(self.client.get('/'), '最初のメンバーを追加')
        member = self.add()
        Member.objects.filter(pk=member.pk).update(name='<script>alert(1)</script>')
        response = self.client.get('/', {'type': 'invalid', 'status': 'invalid', 'category': 'invalid'})
        self.assertContains(response, '&lt;script&gt;')
        self.assertNotContains(response, '<script>alert(1)</script>')
        self.assertContains(self.client.get('/', {'q': '該当しない名前'}), '該当するメンバーがいません')


class MigrationTests(TransactionTestCase):
    def test_existing_data_is_preserved_in_both_categories(self):
        executor = MigrationExecutor(connection)
        apps = executor.loader.project_state([('roster', '0002_remove_participation_unique_member_type_and_more')]).apps
        OldMember = apps.get_model('roster', 'Member')
        OldParticipation = apps.get_model('roster', 'Participation')
        member = OldMember.objects.create(name='既存メンバー', notes='既存メモ')
        for key, symbol in [('fire', 'yes'), ('water', 'conditional'), ('normal', 'no')]:
            OldParticipation.objects.create(member=member, pokemon_type=key, status=symbol, condition='引継ぎメモ')
        from importlib import import_module
        migrate = import_module('roster.migrations.0003_split_existing_participation').split_existing
        with connection.schema_editor() as editor:
            migrate(apps, editor)
            migrate(apps, editor)
        member = Member.objects.get(pk=member.pk)
        self.assertEqual(member.notes, '既存メモ')
        self.assertEqual(member.participations.count(), 36)
        for key, symbol in [('fire', 'yes'), ('water', 'conditional'), ('normal', 'no')]:
            for kind, _ in CATEGORIES:
                record = member.participations.get(pokemon_type=key, category=kind)
                self.assertEqual(record.status, symbol)
                self.assertEqual(record.condition, '引継ぎメモ')
