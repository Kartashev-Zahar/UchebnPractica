from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


def proverit_foto(file):
    if file.size > 2 * 1024 * 1024:
        raise ValidationError("Размер фотографии не должен превышать 2 МБ.")
    if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise ValidationError("Можно загрузить JPG, PNG или WEBP.")


class Kategoriya(models.Model):
    nazvanie = models.CharField("Название категории", max_length=100)

    class Meta:
        verbose_name = "категория"
        verbose_name_plural = "категории"
        ordering = ["nazvanie"]

    def __str__(self):
        return self.nazvanie


class ModelInstrumenta(models.Model):
    nazvanie = models.CharField("Название модели", max_length=150)
    kategoriya = models.ForeignKey(
        Kategoriya, on_delete=models.CASCADE, related_name="modeli",
        verbose_name="категория",
    )
    opisanie = models.TextField("Описание", blank=True)
    foto = models.CharField("Имя изображения", max_length=40, default="drel")
    foto_fajl = models.FileField(
        "Файл изображения", upload_to="instrumenty/", blank=True,
        validators=[proverit_foto],
    )
    cena_za_sutki = models.PositiveIntegerField("Цена за сутки")
    zalog = models.PositiveIntegerField("Размер залога")

    class Meta:
        verbose_name = "модель инструмента"
        verbose_name_plural = "модели инструмента"
        ordering = ["nazvanie"]
        constraints = [
            models.CheckConstraint(condition=models.Q(cena_za_sutki__gt=0), name="model_cena_positive"),
        ]

    def __str__(self):
        return self.nazvanie


class Ekzemplyar(models.Model):
    model = models.ForeignKey(
        ModelInstrumenta, on_delete=models.CASCADE, related_name="ekzemplyary",
        verbose_name="модель инструмента",
    )
    seriinij_nomer = models.CharField("Серийный номер", max_length=50, unique=True)
    ispraven = models.BooleanField("Исправен", default=True)
    svoboden = models.BooleanField("Свободен", default=True)

    class Meta:
        verbose_name = "экземпляр инструмента"
        verbose_name_plural = "экземпляры инструмента"
        ordering = ["seriinij_nomer"]

    def __str__(self):
        return self.seriinij_nomer


class Raskhodnik(models.Model):
    nazvanie = models.CharField("Название расходника", max_length=100)
    cena = models.PositiveIntegerField("Цена")

    class Meta:
        verbose_name = "расходник"
        verbose_name_plural = "расходники"
        ordering = ["nazvanie"]
        constraints = [
            models.CheckConstraint(condition=models.Q(cena__gt=0), name="raskhodnik_cena_positive"),
        ]

    def __str__(self):
        return self.nazvanie


class Dogovor(models.Model):
    POLUCHENIE = "Оформлен"
    VOZVRAT = "Возвращен"
    STATUS_CHOICES = [(POLUCHENIE, POLUCHENIE), (VOZVRAT, VOZVRAT)]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="dogovory",
        verbose_name="пользователь",
    )
    ekzemplyar = models.ForeignKey(
        Ekzemplyar, on_delete=models.PROTECT, related_name="dogovory",
        verbose_name="экземпляр инструмента",
    )
    osnastka = models.ManyToManyField(
        "Raskhodnik", blank=True, related_name="dogovory", verbose_name="расходники",
    )
    data_nachala = models.DateField("Дата начала аренды")
    data_vozvrata = models.DateTimeField("Планируемая дата возврата")
    srok_dnej = models.PositiveIntegerField("Срок аренды, дней")
    summa = models.PositiveIntegerField("Сумма аренды")
    status = models.CharField("Статус", max_length=20, choices=STATUS_CHOICES, default=POLUCHENIE)
    data_fakt_vozvrata = models.DateTimeField("Фактическая дата возврата", null=True, blank=True)

    class Meta:
        verbose_name = "договор аренды"
        verbose_name_plural = "договоры аренды"
        ordering = ["-data_nachala", "id"]
        constraints = [
            models.CheckConstraint(condition=models.Q(srok_dnej__gte=1, srok_dnej__lte=60), name="dogovor_srok_1_60"),
        ]

    def __str__(self):
        return f"Договор №{self.id}"


class Tarif(models.Model):
    ot_dney = models.PositiveIntegerField("Минимальный срок, дней", unique=True)
    skidka = models.PositiveIntegerField("Скидка, %", default=0)

    class Meta:
        verbose_name = "тариф"
        verbose_name_plural = "тарифы"
        ordering = ["ot_dney"]
        constraints = [
            models.CheckConstraint(condition=models.Q(ot_dney__gte=1), name="tarif_days_positive"),
            models.CheckConstraint(condition=models.Q(skidka__lte=100), name="tarif_discount_0_100"),
        ]

    def __str__(self):
        return f"От {self.ot_dney} суток: скидка {self.skidka}%"


class Zalog(models.Model):
    dogovor = models.OneToOneField(
        Dogovor, on_delete=models.CASCADE, related_name="zalog", verbose_name="договор",
    )
    summa = models.PositiveIntegerField("Сумма залога")
    ostatok = models.PositiveIntegerField("Остаток залога")

    class Meta:
        verbose_name = "залог"
        verbose_name_plural = "залоги"
        ordering = ["dogovor_id"]
        constraints = [
            models.CheckConstraint(condition=models.Q(ostatok__lte=models.F("summa")), name="zalog_ostatok_lte_summa"),
        ]

    def __str__(self):
        return f"Залог по договору №{self.dogovor_id}"


class AktProverki(models.Model):
    dogovor = models.OneToOneField(
        Dogovor, on_delete=models.CASCADE, related_name="akt_proverki", verbose_name="договор",
    )
    ispraven = models.BooleanField("Инструмент исправен", default=True)
    kommentarij = models.CharField("Комментарий", max_length=250, blank=True)

    class Meta:
        verbose_name = "акт проверки"
        verbose_name_plural = "акты проверки"
        ordering = ["dogovor_id"]

    def __str__(self):
        return f"Проверка договора №{self.dogovor_id}"


class Uderzhanie(models.Model):
    dogovor = models.OneToOneField(
        Dogovor, on_delete=models.CASCADE, related_name="uderzhanie", verbose_name="договор",
    )
    summa = models.PositiveIntegerField("Сумма удержания", default=0)
    prichina = models.CharField("Причина удержания", max_length=250)

    class Meta:
        verbose_name = "удержание"
        verbose_name_plural = "удержания"
        ordering = ["dogovor_id"]

    def __str__(self):
        return f"Удержание по договору №{self.dogovor_id}"
