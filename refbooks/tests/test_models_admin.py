from datetime import date
from io import StringIO
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase
from refbooks.models import Refbook, RefbookVersion, RefbookElement


class ModelTests(TestCase):
    def setUp(self):
        self.book = Refbook.objects.create(code='MS1', name='Специальности')
        self.version = RefbookVersion.objects.create(refbook=self.book, version='1.0', effective_date=date(2022, 1, 1))
        self.element = RefbookElement.objects.create(version=self.version, code='1', value='Терапевт')

    def test_database_uniqueness_constraints(self):
        duplicates = [
            (Refbook, {'code': 'MS1', 'name': 'Другой'}),
            (RefbookVersion, {'refbook': self.book, 'version': '1.0', 'effective_date': date(2023, 1, 1)}),
            (RefbookVersion, {'refbook': self.book, 'version': '2.0', 'effective_date': date(2022, 1, 1)}),
            (RefbookElement, {'version': self.version, 'code': '1', 'value': 'Хирург'}),
        ]
        for model, values in duplicates:
            with self.subTest(model=model.__name__, values=values):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    model.objects.create(**values)

    def test_uniqueness_is_scoped(self):
        other = Refbook.objects.create(code='OTHER', name='Другой')
        version = RefbookVersion.objects.create(refbook=other, version='1.0', effective_date=date(2022, 1, 1))
        RefbookElement.objects.create(version=version, code='1', value='Другой элемент')
        self.assertEqual(RefbookElement.objects.count(), 2)

    def test_required_fields_and_lengths(self):
        for model, field, limit in [(self.book, 'code', 100), (self.book, 'name', 300), (self.version, 'version', 50), (self.element, 'code', 100), (self.element, 'value', 300)]:
            old = getattr(model, field)
            for invalid in ['', 'x' * (limit + 1)]:
                with self.subTest(field=field, invalid=invalid):
                    setattr(model, field, invalid)
                    with self.assertRaises(ValidationError):
                        model.full_clean()
            setattr(model, field, old)

    def test_cascade_delete(self):
        self.book.delete()
        self.assertFalse(RefbookVersion.objects.exists())
        self.assertFalse(RefbookElement.objects.exists())

    def test_demo_command_idempotent(self):
        call_command('seed_demo', stdout=StringIO())
        counts = (Refbook.objects.count(), RefbookVersion.objects.count(), RefbookElement.objects.count())
        call_command('seed_demo', stdout=StringIO())
        self.assertEqual(counts, (Refbook.objects.count(), RefbookVersion.objects.count(), RefbookElement.objects.count()))
        self.element.refresh_from_db()
        self.assertEqual(self.element.value, 'Терапевт')


class AdminTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_superuser(username='admin', password='test-only-password')
        self.client.force_login(user)
        self.book = Refbook.objects.create(code='MS1', name='Специальности')
        self.version = RefbookVersion.objects.create(refbook=self.book, version='1.0', effective_date=date(2022, 1, 1))

    def test_lists_and_inline_forms(self):
        for path in ['refbook/', 'refbookversion/', 'refbookelement/', f'refbook/{self.book.pk}/change/', f'refbookversion/{self.version.pk}/change/', 'refbookelement/add/']:
            with self.subTest(path=path):
                self.assertEqual(self.client.get('/admin/refbooks/' + path).status_code, 200)
        self.assertContains(self.client.get(f'/admin/refbooks/refbook/{self.book.pk}/change/'), 'versions-TOTAL_FORMS')
        self.assertContains(self.client.get(f'/admin/refbooks/refbookversion/{self.version.pk}/change/'), 'elements-TOTAL_FORMS')
        self.assertContains(self.client.get('/admin/'), 'Сервис терминологии')

    def test_label_corrections_loaded_only_in_admin(self):
        book = self.client.get(f'/admin/refbooks/refbook/{self.book.pk}/change/')
        version = self.client.get(f'/admin/refbooks/refbookversion/{self.version.pk}/change/')
        delete = self.client.get(f'/admin/refbooks/refbookversion/{self.version.pk}/delete/')
        for response in (book, version, delete):
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'refbooks/admin_labels.js')
        self.assertNotContains(self.client.get('/refbooks/'), 'admin_labels.js')

    def test_admin_requires_login(self):
        self.client.logout()
        self.assertEqual(self.client.get('/admin/refbooks/refbook/').status_code, 302)
