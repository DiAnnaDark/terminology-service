"""Minimal Russian labels for Django Admin uniqueness messages.

This changes presentation only: Django still performs all original uniqueness
checks, and the database constraints stay unchanged.
"""

from django import forms
from django.forms.models import BaseInlineFormSet

from .models import Refbook


class RefbookAdminForm(forms.ModelForm):
    class Meta:
        model = Refbook
        fields = "__all__"
        error_messages = {
            "code": {"unique": "Справочник с таким кодом уже существует."},
        }


class RussianUniqueFieldsFormSet(BaseInlineFormSet):
    field_names = {}

    def get_unique_error_message(self, unique_check):
        message = super().get_unique_error_message(unique_check)
        for field in unique_check:
            if field in self.field_names:
                message = message.replace(
                    f'"{field}"', f'"{self.field_names[field]}"'
                )
        return message


class VersionInlineFormSet(RussianUniqueFieldsFormSet):
    field_names = {
        "version": "версия",
        "effective_date": "дата начала действия",
    }


class ElementInlineFormSet(RussianUniqueFieldsFormSet):
    field_names = {"code": "код элемента"}
