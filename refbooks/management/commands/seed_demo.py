from datetime import date
from django.core.management.base import BaseCommand
from django.db import transaction
from refbooks.models import Refbook, RefbookElement, RefbookVersion

class Command(BaseCommand):
    help = "Создать демонстрационные справочники (повторный запуск не создаёт дубли и не перезаписывает данные)."

    @transaction.atomic
    def handle(self, *args, **options):
        data = [
            ("MS1", "Специальности медицинских работников", [("1", "Врач-терапевт"), ("2", "Травматолог-ортопед"), ("3", "Хирург")]),
            ("ICD-10", "Международный классификатор болезней МКБ-10", [("S99", "Другие и неуточненные травмы голеностопного сустава и стопы")]),
        ]
        for code, name, elements in data:
            book, _ = Refbook.objects.get_or_create(code=code, defaults={"name": name})
            version, _ = RefbookVersion.objects.get_or_create(refbook=book, version="1.0", defaults={"effective_date": date(2022, 1, 1)})
            for element_code, value in elements:
                RefbookElement.objects.get_or_create(version=version, code=element_code, defaults={"value": value})
            self.stdout.write(self.style.SUCCESS(f"{book.code}: id={book.pk}, версия={version.version}"))
