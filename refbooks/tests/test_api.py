from datetime import date
from unittest.mock import patch
from django.test import TestCase
from rest_framework.test import APIClient
from refbooks.models import Refbook, RefbookVersion, RefbookElement


class APITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.book = Refbook.objects.create(code='MS1', name='Специальности')
        cls.empty = Refbook.objects.create(code='EMPTY', name='Без версий')
        cls.old = RefbookVersion.objects.create(refbook=cls.book, version='10.0', effective_date=date(2022, 1, 1))
        cls.current = RefbookVersion.objects.create(refbook=cls.book, version='2.0', effective_date=date(2023, 1, 1))
        cls.future = RefbookVersion.objects.create(refbook=cls.book, version='3.0', effective_date=date(2024, 1, 1))
        cls.draft = RefbookVersion.objects.create(refbook=cls.book, version='draft')
        for version, value in [(cls.old, 'Старое значение'), (cls.current, 'Врач-терапевт'), (cls.future, 'Будущее значение')]:
            RefbookElement.objects.create(version=version, code='1', value=value)
        RefbookElement.objects.create(version=cls.current, code='2', value='Хирург')

    def setUp(self):
        self.client = APIClient()
        self.clock = patch('django.utils.timezone.localdate', return_value=date(2023, 1, 1))
        self.clock.start()
        self.addCleanup(self.clock.stop)
        self.elements = f'/refbooks/{self.book.pk}/elements'
        self.check = f'/refbooks/{self.book.pk}/check_element'

    def test_all_books_including_no_versions(self):
        response = self.client.get('/refbooks/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'refbooks': [
            {'id': str(self.book.pk), 'code': 'MS1', 'name': 'Специальности'},
            {'id': str(self.empty.pk), 'code': 'EMPTY', 'name': 'Без версий'}]})

    def test_date_filter_inclusive_without_duplicates(self):
        for day in ['2022-01-01', '2023-01-01', '2025-01-01']:
            with self.subTest(day=day):
                response = self.client.get('/refbooks/', {'date': day})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(len(response.json()['refbooks']), 1)

    def test_date_before_first_version(self):
        self.assertEqual(self.client.get('/refbooks/', {'date': '2021-12-31'}).json(), {'refbooks': []})

    def test_invalid_dates(self):
        for day in ['', '2023-02-29', '2023-1-1', '01.01.2023', 'garbage', '2023-01-01T00:00:00']:
            with self.subTest(day=day):
                self.assertEqual(self.client.get('/refbooks/', {'date': day}).status_code, 400)

    def test_current_by_date_not_version_name(self):
        response = self.client.get(self.elements)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'elements': [
            {'code': '1', 'value': 'Врач-терапевт'}, {'code': '2', 'value': 'Хирург'}]})

    def test_explicit_old_and_future_versions(self):
        for version, expected in [('10.0', 'Старое значение'), ('3.0', 'Будущее значение')]:
            with self.subTest(version=version):
                response = self.client.get(self.elements, {'version': version})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()['elements'][0]['value'], expected)

    def test_empty_undated_version(self):
        self.assertEqual(self.client.get(self.elements, {'version': 'draft'}).json(), {'elements': []})
        self.assertEqual(self.client.get(self.check, {'version': 'draft', 'code': '1', 'value': 'x'}).json(), {'valid': False})

    def test_missing_book_or_version(self):
        for path in ['/refbooks/999999/elements', '/refbooks/999999/check_element', self.elements, self.check]:
            with self.subTest(path=path):
                response = self.client.get(path, {'version': 'missing', 'code': '1', 'value': 'x'})
                self.assertEqual(response.status_code, 404)

    def test_no_current_version(self):
        future_only = Refbook.objects.create(code='FUTURE', name='Будущий')
        RefbookVersion.objects.create(refbook=future_only, version='1', effective_date=date(2024, 1, 1))
        undated = Refbook.objects.create(code='DRAFT', name='Черновик')
        RefbookVersion.objects.create(refbook=undated, version='1')
        for book in [self.empty, future_only, undated]:
            for endpoint in ['elements', 'check_element']:
                with self.subTest(book=book.code, endpoint=endpoint):
                    response = self.client.get(f'/refbooks/{book.pk}/{endpoint}', {'code': '1', 'value': 'x'})
                    self.assertEqual(response.status_code, 404)
        self.assertEqual(len(self.client.get('/refbooks/', {'date': '2023-01-01'}).json()['refbooks']), 1)

    def test_invalid_versions(self):
        for path in [self.elements, self.check]:
            for version in ['', 'x' * 51]:
                with self.subTest(path=path, version=version):
                    self.assertEqual(self.client.get(path, {'version': version, 'code': '1', 'value': 'x'}).status_code, 400)

    def test_check_current(self):
        self.assertEqual(self.client.get(self.check, {'code': '1', 'value': 'Врач-терапевт'}).json(), {'valid': True})

    def test_check_exact_pair(self):
        for code, value in [('1', 'Хирург'), ('2', 'Врач-терапевт'), ('3', 'Хирург'), ('1', 'врач-терапевт'), ('1', 'Врач-терапевт '), ('1', 'Старое значение')]:
            with self.subTest(code=code, value=value):
                response = self.client.get(self.check, {'code': code, 'value': value})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {'valid': False})

    def test_check_explicit_version(self):
        self.assertEqual(self.client.get(self.check, {'code': '1', 'value': 'Старое значение', 'version': '10.0'}).json(), {'valid': True})

    def test_check_missing_empty_or_oversized_parameters(self):
        for params in [{}, {'code': '1'}, {'value': 'x'}, {'code': '', 'value': 'x'}, {'code': '1', 'value': ''}, {'code': 'x'*101, 'value': 'x'}, {'code': '1', 'value': 'x'*301}]:
            with self.subTest(params=params):
                self.assertEqual(self.client.get(self.check, params).status_code, 400)

    def test_version_scoped_to_refbook(self):
        other = RefbookVersion.objects.create(refbook=self.empty, version='other', effective_date=date(2022, 1, 1))
        RefbookElement.objects.create(version=other, code='1', value='Other')
        self.assertEqual(self.client.get(self.elements, {'version': 'other'}).status_code, 404)
        self.assertEqual(self.client.get(self.check, {'code': '1', 'value': 'Other'}).json(), {'valid': False})

    def test_read_only(self):
        for path in ['/refbooks/', self.elements, self.check]:
            for method in ['post', 'put', 'patch', 'delete']:
                with self.subTest(path=path, method=method):
                    self.assertEqual(getattr(self.client, method)(path, {}, format='json').status_code, 405)

    def test_schema_and_swagger(self):
        response = self.client.get('/api/schema/?format=json')
        self.assertEqual(response.status_code, 200)
        schema = response.json()
        self.assertEqual(set(schema['paths']), {'/refbooks/', '/refbooks/{id}/elements', '/refbooks/{id}/check_element'})
        self.assertContains(self.client.get('/api/docs/'), 'swagger-ui-bundle.js')
