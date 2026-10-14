from django.db.models import Exists, OuterRef
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Refbook, RefbookVersion
from .serializers import (CheckQuerySerializer, CheckResultSerializer, ElementListSerializer,
    ElementSerializer, ListQuerySerializer, NotFoundSerializer, QueryErrorSerializer, DateQueryErrorSerializer,
    RefbookListSerializer, RefbookSerializer, VersionQuerySerializer)


def parse_query(serializer_class, request):
    # A plain dict preserves explicit empty values: DRF treats blank optional
    # fields in a QueryDict as omitted HTML form inputs.
    serializer = serializer_class(data=request.query_params.dict())
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


def resolve_version(refbook_id, version=None):
    refbook = get_object_or_404(Refbook, pk=refbook_id)
    if version is not None:
        result = refbook.versions.filter(version=version).first()
    else:
        result = refbook.versions.effective_on().first()
    if result is None:
        raise NotFound("Версия справочника не найдена." if version is not None else "У справочника нет текущей версии.")
    return result


class RefbookListView(APIView):
    @extend_schema(
        summary="Список справочников", parameters=[ListQuerySerializer],
        description="GET /refbooks/?date=2022-10-01. Без date возвращаются все справочники. С date — только имеющие хотя бы одну версию с датой начала <= date. Версии без даты не учитываются.",
        responses={200: RefbookListSerializer, 400: DateQueryErrorSerializer},
        examples=[OpenApiExample("Список", value={"refbooks": [{"id": "1", "code": "MS1", "name": "Специальности медицинских работников"}]}, response_only=True)],
    )
    def get(self, request):
        query = parse_query(ListQuerySerializer, request)
        books = Refbook.objects.all()
        if "date" in query:
            active = RefbookVersion.objects.filter(refbook_id=OuterRef("pk")).effective_on(query["date"])
            books = books.filter(Exists(active))
        return Response({"refbooks": RefbookSerializer(books, many=True).data})


class ElementListView(APIView):
    @extend_schema(
        summary="Элементы справочника", parameters=[VersionQuerySerializer],
        description="GET /refbooks/1/elements?version=1.0. Без version выбирается последняя вступившая в силу версия (дата <= сегодня, Europe/Moscow). Явно можно запросить любую существующую версию, включая будущую и без даты. Пустая существующая версия возвращает пустой список.",
        responses={200: ElementListSerializer, 400: QueryErrorSerializer, 404: NotFoundSerializer},
        examples=[OpenApiExample("Элементы", value={"elements": [{"code": "1", "value": "Врач-терапевт"}]}, response_only=True)],
    )
    def get(self, request, id):
        query = parse_query(VersionQuerySerializer, request)
        version = resolve_version(id, query.get("version"))
        return Response({"elements": ElementSerializer(version.elements.all(), many=True).data})


class CheckElementView(APIView):
    @extend_schema(
        summary="Проверка элемента", parameters=[CheckQuerySerializer],
        description="GET /refbooks/1/check_element?code=1&value=Врач-терапевт&version=1.0. Код и значение должны совпасть у одного элемента выбранной версии. Сравнение точное: регистр и пробелы значимы. Отсутствие элемента — 200 и valid=false; отсутствие справочника/версии — 404.",
        responses={200: CheckResultSerializer, 400: QueryErrorSerializer, 404: NotFoundSerializer},
        examples=[OpenApiExample("Найден", value={"valid": True}, response_only=True),
                  OpenApiExample("Не найден", value={"valid": False}, response_only=True)],
    )
    def get(self, request, id):
        query = parse_query(CheckQuerySerializer, request)
        version = resolve_version(id, query.get("version"))
        return Response({"valid": version.elements.filter(code=query["code"], value=query["value"]).exists()})
