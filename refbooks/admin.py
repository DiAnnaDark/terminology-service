from django.contrib import admin
from django.db.models import OuterRef, Subquery
from .models import Refbook, RefbookElement, RefbookVersion

admin.site.site_header = "Сервис терминологии"
admin.site.site_title = "Сервис терминологии"
admin.site.index_title = "Управление справочниками"

class VersionInline(admin.TabularInline):
    model = RefbookVersion
    extra = 0
    show_change_link = True

class ElementInline(admin.TabularInline):
    model = RefbookElement
    extra = 0

@admin.register(Refbook)
class RefbookAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "current_version", "current_date")
    search_fields = ("code", "name")
    list_display_links = ("id", "name")
    inlines = (VersionInline,)

    def get_queryset(self, request):
        current = RefbookVersion.objects.filter(refbook_id=OuterRef("pk")).effective_on()
        return super().get_queryset(request).annotate(
            active_version=Subquery(current.values("version")[:1]),
            active_date=Subquery(current.values("effective_date")[:1]),
        )

    @admin.display(description="Текущая версия", ordering="active_version", empty_value="—")
    def current_version(self, obj):
        return obj.active_version

    @admin.display(description="Дата начала действия версии", ordering="active_date", empty_value="—")
    def current_date(self, obj):
        return obj.active_date

@admin.register(RefbookVersion)
class RefbookVersionAdmin(admin.ModelAdmin):
    list_display = ("refbook_code", "refbook_name", "version", "effective_date")
    list_select_related = ("refbook",)
    search_fields = ("refbook__code", "refbook__name", "version")
    autocomplete_fields = ("refbook",)
    inlines = (ElementInline,)

    @admin.display(description="Код справочника", ordering="refbook__code")
    def refbook_code(self, obj):
        return obj.refbook.code

    @admin.display(description="Наименование справочника", ordering="refbook__name")
    def refbook_name(self, obj):
        return obj.refbook.name

@admin.register(RefbookElement)
class RefbookElementAdmin(admin.ModelAdmin):
    list_display = ("version", "code", "value")
    list_select_related = ("version__refbook",)
    search_fields = ("code", "value", "version__refbook__code")
    autocomplete_fields = ("version",)
