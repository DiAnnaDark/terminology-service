"""Integration checks for Django Admin writes and SQLite index access paths."""

from datetime import date

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase

from refbooks.models import Refbook, RefbookElement, RefbookVersion


class AdminWriteTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_superuser(
            username="admin-write-audit", password="local-test-only-password"
        )
        self.client.force_login(user)

    def test_create_edit_and_delete_refbook(self):
        add_url = "/admin/refbooks/refbook/add/"
        response = self.client.post(add_url, {
            "code": "MS1",
            "name": "Специальности",
            "description": "Первое описание",
            "versions-TOTAL_FORMS": "0",
            "versions-INITIAL_FORMS": "0",
            "versions-MIN_NUM_FORMS": "0",
            "versions-MAX_NUM_FORMS": "1000",
            "_save": "Save",
        })
        self.assertEqual(response.status_code, 302, response.context)
        book = Refbook.objects.get(code="MS1")

        response = self.client.post(
            f"/admin/refbooks/refbook/{book.pk}/change/",
            {
                "code": "MS1",
                "name": "Специальности врачей",
                "description": "Исправлено",
                "versions-TOTAL_FORMS": "0",
                "versions-INITIAL_FORMS": "0",
                "versions-MIN_NUM_FORMS": "0",
                "versions-MAX_NUM_FORMS": "1000",
                "_save": "Save",
            },
        )
        self.assertEqual(response.status_code, 302, response.context)
        book.refresh_from_db()
        self.assertEqual(book.name, "Специальности врачей")
        self.assertEqual(book.description, "Исправлено")

        response = self.client.post(
            f"/admin/refbooks/refbook/{book.pk}/delete/",
            {"post": "yes"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Refbook.objects.filter(pk=book.pk).exists())

    def test_version_form_creates_and_updates_inline_element(self):
        book = Refbook.objects.create(code="MS1", name="Специальности")
        add_url = "/admin/refbooks/refbookversion/add/"
        response = self.client.post(add_url, {
            "refbook": str(book.pk),
            "version": "1.0",
            "effective_date": "2022-01-01",
            "elements-TOTAL_FORMS": "1",
            "elements-INITIAL_FORMS": "0",
            "elements-MIN_NUM_FORMS": "0",
            "elements-MAX_NUM_FORMS": "1000",
            "elements-0-code": "1",
            "elements-0-value": "Терапевт",
            "_save": "Save",
        })
        self.assertEqual(response.status_code, 302, response.context)
        version = RefbookVersion.objects.get(refbook=book, version="1.0")
        element = RefbookElement.objects.get(version=version, code="1")
        self.assertEqual(element.value, "Терапевт")

        response = self.client.post(
            f"/admin/refbooks/refbookversion/{version.pk}/change/",
            {
                "refbook": str(book.pk),
                "version": "1.0",
                "effective_date": "2022-01-01",
                "elements-TOTAL_FORMS": "1",
                "elements-INITIAL_FORMS": "1",
                "elements-MIN_NUM_FORMS": "0",
                "elements-MAX_NUM_FORMS": "1000",
                "elements-0-id": str(element.pk),
                "elements-0-version": str(version.pk),
                "elements-0-code": "1",
                "elements-0-value": "Врач-терапевт",
                "_save": "Save",
            },
        )
        self.assertEqual(response.status_code, 302, response.context)
        element.refresh_from_db()
        self.assertEqual(element.value, "Врач-терапевт")

    def test_refbook_name_is_a_change_link(self):
        book = Refbook.objects.create(code="LINK-TEST", name="Открываемое название")
        response = self.client.get("/admin/refbooks/refbook/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f'<a href="/admin/refbooks/refbook/{book.pk}/change/">Открываемое название</a>',
            html=True,
        )

    def test_duplicate_refbook_code_is_rejected_by_admin(self):
        Refbook.objects.create(code="MS1", name="Первый")
        response = self.client.post("/admin/refbooks/refbook/add/", {
            "code": "MS1",
            "name": "Дубликат",
            "description": "",
            "versions-TOTAL_FORMS": "0",
            "versions-INITIAL_FORMS": "0",
            "versions-MIN_NUM_FORMS": "0",
            "versions-MAX_NUM_FORMS": "1000",
            "_save": "Save",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Refbook.objects.filter(code="MS1").count(), 1)


class SqliteIndexTests(TestCase):
    def test_critical_lookup_uses_version_element_index(self):
        book = Refbook.objects.create(code="MS1", name="Специальности")
        version = RefbookVersion.objects.create(
            refbook=book, version="1.0", effective_date=date(2022, 1, 1)
        )
        RefbookElement.objects.create(version=version, code="1", value="Терапевт")
        # Django passes bound SQL parameters through its database connection.
        queryset = RefbookElement.objects.filter(version=version, code="1")
        sql, params = queryset.query.sql_with_params()
        with connection.cursor() as cursor:
            cursor.execute("EXPLAIN QUERY PLAN " + sql, params)
            details = " ".join(str(row[-1]) for row in cursor.fetchall()).upper()
        self.assertIn("INDEX", details, details)
        self.assertNotIn("SCAN REFBOOKS_REFBOOKELEMENT", details, details)
