from rest_framework import serializers
from .models import Refbook, RefbookElement

class ListQuerySerializer(serializers.Serializer):
    date = serializers.RegexField(r"^\d{4}-\d{2}-\d{2}$", required=False, help_text="Дата ГГГГ-ММ-ДД; например 2022-10-01.")

    def validate_date(self, value):
        return serializers.DateField(input_formats=["%Y-%m-%d"]).run_validation(value)

class VersionQuerySerializer(serializers.Serializer):
    version = serializers.CharField(max_length=50, required=False, trim_whitespace=False,
        help_text="Например 1.0. Без параметра выбирается текущая версия на сегодняшнюю дату.")

class CheckQuerySerializer(VersionQuerySerializer):
    code = serializers.CharField(max_length=100, trim_whitespace=False, help_text="Код элемента, например J00.")
    value = serializers.CharField(max_length=300, trim_whitespace=False, help_text="Точное значение элемента.")

class RefbookSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    class Meta:
        model = Refbook
        fields = ("id", "code", "name")

class ElementSerializer(serializers.ModelSerializer):
    class Meta:
        model = RefbookElement
        fields = ("code", "value")

class RefbookListSerializer(serializers.Serializer):
    refbooks = RefbookSerializer(many=True)

class ElementListSerializer(serializers.Serializer):
    elements = ElementSerializer(many=True)

class CheckResultSerializer(serializers.Serializer):
    valid = serializers.BooleanField()

class NotFoundSerializer(serializers.Serializer):
    detail = serializers.CharField()

class QueryErrorSerializer(serializers.Serializer):
    date = serializers.ListField(child=serializers.CharField(), required=False)
    version = serializers.ListField(child=serializers.CharField(), required=False)
    code = serializers.ListField(child=serializers.CharField(), required=False)
    value = serializers.ListField(child=serializers.CharField(), required=False)
