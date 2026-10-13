from django.db import models
from django.utils import timezone


class Refbook(models.Model):
    code = models.CharField("Код", max_length=100, unique=True)
    name = models.CharField("Наименование", max_length=300)
    description = models.TextField("Описание", blank=True)

    class Meta:
        verbose_name = "Справочник"
        verbose_name_plural = "Справочники"
        ordering = ["id"]

    def __str__(self):
        return f"{self.code} — {self.name}"


class RefbookVersionQuerySet(models.QuerySet):
    def effective_on(self, date=None):
        return self.filter(effective_date__lte=date or timezone.localdate()).order_by("-effective_date")


class RefbookVersion(models.Model):
    refbook = models.ForeignKey(Refbook, verbose_name="Справочник", related_name="versions", on_delete=models.CASCADE)
    version = models.CharField("Версия", max_length=50)
    effective_date = models.DateField("Дата начала действия", blank=True, null=True)
    objects = RefbookVersionQuerySet.as_manager()

    class Meta:
        verbose_name = "Версия справочника"
        verbose_name_plural = "Версии справочников"
        ordering = ["refbook_id", "-effective_date", "id"]
        constraints = [
            models.UniqueConstraint(fields=["refbook", "version"], name="unique_refbook_version"),
            models.UniqueConstraint(fields=["refbook", "effective_date"], name="unique_refbook_effective_date"),
        ]

    def __str__(self):
        return f"{self.refbook.code} — {self.version}"


class RefbookElement(models.Model):
    version = models.ForeignKey(RefbookVersion, verbose_name="Версия справочника", related_name="elements", on_delete=models.CASCADE)
    code = models.CharField("Код элемента", max_length=100)
    value = models.CharField("Значение элемента", max_length=300)

    class Meta:
        verbose_name = "Элемент справочника"
        verbose_name_plural = "Элементы справочников"
        ordering = ["id"]
        constraints = [models.UniqueConstraint(fields=["version", "code"], name="unique_version_element_code")]

    def __str__(self):
        return f"{self.code} — {self.value}"
