"""Regression tests for N+1 queries in list endpoints and related-object access."""

from datetime import date

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from refbooks.models import Refbook, RefbookElement, RefbookVersion


class NPlusOneTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin_user = get_user_model().objects.create_superuser(
            username="query-audit-admin", password="local-test-only-password"
        )

    def capture_queries(self, callback):
        with CaptureQueriesContext(connection) as queries:
            callback()
        return list(queries.captured_queries)

    def add_records(self, start, stop):
        for index in range(start, stop):
            book = Refbook.objects.create(
                code=f"BOOK-{index}", name=f"Справочник {index}"
            )
            version = RefbookVersion.objects.create(
                refbook=book, version="1.0", effective_date=date(2022, 1, 1)
            )
            RefbookElement.objects.create(
                version=version, code="1", value=f"Элемент {index}"
            )

    def assert_query_count_does_not_scale(self, callback):
        self.add_records(0, 2)
        small_queries = self.capture_queries(callback)
        self.add_records(2, 42)
        large_queries = self.capture_queries(callback)
        small, large = len(small_queries), len(large_queries)
        print(
            f"\\n{self._testMethodName}: "
            f"2 records = {small} SQL queries; "
            f"42 records = {large} SQL queries",
            flush=True,
        )
        if self._testMethodName == "test_refbook_list_api_query_count":
            selects = [
                entry["sql"] for entry in large_queries
                if entry["sql"].lstrip().upper().startswith("SELECT")
            ]
            if selects:
                print(f"Example SQL (42 records):\\n{selects[0]}", flush=True)
        self.assertLessEqual(
            large, small,
            f"N+1 suspected: 2 records used {small} SQL queries, "
            f"42 records used {large}."
        )

    def test_refbook_list_api_query_count(self):
        def request_list():
            response = self.client.get("/refbooks/")
            self.assertEqual(response.status_code, 200)

        self.assert_query_count_does_not_scale(request_list)

    def test_refbook_admin_changelist_query_count(self):
        self.client.force_login(self.admin_user)

        def request_list():
            response = self.client.get("/admin/refbooks/refbook/")
            self.assertEqual(response.status_code, 200)

        self.assert_query_count_does_not_scale(request_list)

    def test_version_admin_changelist_query_count(self):
        self.client.force_login(self.admin_user)

        def request_list():
            response = self.client.get("/admin/refbooks/refbookversion/")
            self.assertEqual(response.status_code, 200)

        self.assert_query_count_does_not_scale(request_list)

    def test_element_admin_changelist_query_count(self):
        self.client.force_login(self.admin_user)

        def request_list():
            response = self.client.get("/admin/refbooks/refbookelement/")
            self.assertEqual(response.status_code, 200)

        self.assert_query_count_does_not_scale(request_list)
