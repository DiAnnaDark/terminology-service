"""Regression tests for minimally localized Django Admin validation."""

from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from refbooks.models import Refbook, RefbookElement, RefbookVersion


class AdminLocalizationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(
            username="localized-admin", password="test-only-password"
        )
        cls.book = Refbook.objects.create(code="MS1", name="Специальности")
        cls.v1 = RefbookVersion.objects.create(
            refbook=cls.book, version="1.0", effective_date=date(2022, 1, 1)
        )
        RefbookElement.objects.create(
            version=cls.v1, code="1", value="Врач-терапевт"
        )

    def setUp(self):
        self.client.force_login(self.user)

    @staticmethod
    def management(prefix, total, initial):
        return {
            f"{prefix}-TOTAL_FORMS": str(total),
            f"{prefix}-INITIAL_FORMS": str(initial),
            f"{prefix}-MIN_NUM_FORMS": "0",
            f"{prefix}-MAX_NUM_FORMS": "1000",
        }

    def test_refbook_duplicate_code_uses_lowercase_russian(self):
        response = self.client.post("/admin/refbooks/refbook/add/", {
            "code": "MS1",
            "name": "Другой",
            "description": "",
            **self.management("versions", 0, 0),
            "_save": "Save",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Справочник с таким кодом уже существует.")
        self.assertEqual(Refbook.objects.filter(code="MS1").count(), 1)

    def test_version_duplicate_number_localized(self):
        response = self.client.post(
            f"/admin/refbooks/refbook/{self.book.pk}/change/",
            {
                "code": self.book.code,
                "name": self.book.name,
                "description": "",
                **self.management("versions", 2, 1),
                "versions-0-id": str(self.v1.pk),
                "versions-0-refbook": str(self.book.pk),
                "versions-0-version": "1.0",
                "versions-0-effective_date": "2022-01-01",
                "versions-1-version": "1.0",
                "versions-1-effective_date": "2024-01-01",
                "_save": "Save",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, 'Пожалуйста, измените повторяющееся значение в поле "версия".'
        )
        self.assertEqual(self.book.versions.count(), 1)

    def test_version_duplicate_date_localized(self):
        response = self.client.post(
            f"/admin/refbooks/refbook/{self.book.pk}/change/",
            {
                "code": self.book.code,
                "name": self.book.name,
                "description": "",
                **self.management("versions", 2, 1),
                "versions-0-id": str(self.v1.pk),
                "versions-0-refbook": str(self.book.pk),
                "versions-0-version": "1.0",
                "versions-0-effective_date": "2022-01-01",
                "versions-1-version": "2.0",
                "versions-1-effective_date": "2022-01-01",
                "_save": "Save",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'Пожалуйста, измените повторяющееся значение в поле "дата начала действия".',
        )
        self.assertEqual(self.book.versions.count(), 1)

    def test_element_duplicate_code_localized(self):
        element = self.v1.elements.get(code="1")
        response = self.client.post(
            f"/admin/refbooks/refbookversion/{self.v1.pk}/change/",
            {
                "refbook": str(self.book.pk),
                "version": "1.0",
                "effective_date": "2022-01-01",
                **self.management("elements", 2, 1),
                "elements-0-id": str(element.pk),
                "elements-0-version": str(self.v1.pk),
                "elements-0-code": "1",
                "elements-0-value": "Врач-терапевт",
                "elements-1-code": "1",
                "elements-1-value": "Хирург",
                "_save": "Save",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'Пожалуйста, измените повторяющееся значение в поле "код элемента".',
        )
        self.assertEqual(self.v1.elements.count(), 1)
