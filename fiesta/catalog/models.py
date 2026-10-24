from django.db import models


class Category(models.Model):
    name = models.CharField("Название", max_length=100, unique=True)
    description = models.TextField("Описание", blank=True)
    is_hidden = models.BooleanField("Скрыта", default=False)
    sort_order = models.PositiveIntegerField("Порядок", default=0)

    class Meta:
        db_table = "category"
        ordering = ["sort_order", "name"]
        verbose_name = "Категория"
        verbose_name_plural = "Категории"

    def __str__(self):
        return self.name

class CategoryPriceField(models.Model):
    class Kind(models.TextChoices):
        EVENT = "event", "За мероприятие"
        HOUR = "hour", "За час"
        PERSON = "person", "За человека"
        DAY = "day", "За день"

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="price_fields",
        verbose_name="Категория",
    )
    kind = models.CharField("Вид", max_length=20, choices=Kind.choices)
    label = models.CharField("Подпись", max_length=100)
    sort_order = models.PositiveIntegerField("Порядок", default=0)

    class Meta:
        db_table = "category_price_field"
        verbose_name = "Поле цены категории"
        verbose_name_plural = "Поля цены категории"
        constraints = [
            models.UniqueConstraint(
                fields=["category", "kind"],
                name="unique_category_price_kind",
            )
        ]
        ordering = ["sort_order"]

    def __str__(self):
        return f"{self.category} — {self.label}"

class DetailOption(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="detail_options",
        verbose_name="Категория",
    )
    group_title = models.CharField("Группа", max_length=100)
    title = models.CharField("Вариант", max_length=100)
    sort_order = models.PositiveIntegerField("Порядок", default=0)

    class Meta:
        db_table = "detail_option"
        verbose_name = "Вариант детали"
        verbose_name_plural = "Варианты деталей"
        constraints = [
            models.UniqueConstraint(
                fields=["category", "group_title", "title"],
                name="unique_detail_option",
            )
        ]
        ordering = ["group_title", "sort_order"]

    def __str__(self):
        return f"{self.group_title}: {self.title}"

class EventType(models.Model):
    name = models.CharField("Название", max_length=100, unique=True)
    sort_order = models.PositiveIntegerField("Порядок", default=0)

    class Meta:
        db_table = "event_type"
        verbose_name = "Тип мероприятия"
        verbose_name_plural = "Типы мероприятий"
        ordering = ["sort_order"]

    def __str__(self):
        return self.name


class SpecialistPrice(models.Model):
    specialist = models.ForeignKey(
        "accounts.SpecialistProfile",
        on_delete=models.CASCADE,
        related_name="prices",
        verbose_name="Специалист",
    )
    price_field = models.ForeignKey(
        CategoryPriceField,
        on_delete=models.PROTECT,
        related_name="specialist_prices",
        verbose_name="Поле цены",
    )
    amount = models.DecimalField("Сумма", max_digits=10, decimal_places=2)

    class Meta:
        db_table = "specialist_price"
        verbose_name = "Цена специалиста"
        verbose_name_plural = "Цены специалистов"
        constraints = [
            models.UniqueConstraint(
                fields=["specialist", "price_field"],
                name="unique_specialist_price",
            )
        ]

    def __str__(self):
        return f"{self.specialist} — {self.amount}"


class SpecialistDetail(models.Model):
    specialist = models.ForeignKey(
        "accounts.SpecialistProfile",
        on_delete=models.CASCADE,
        related_name="details",
        verbose_name="Специалист",
    )
    option = models.ForeignKey(
        DetailOption,
        on_delete=models.PROTECT,
        related_name="specialist_details",
        verbose_name="Вариант",
    )

    class Meta:
        db_table = "specialist_detail"
        verbose_name = "Отмеченная деталь"
        verbose_name_plural = "Отмеченные детали"
        constraints = [
            models.UniqueConstraint(
                fields=["specialist", "option"],
                name="unique_specialist_detail",
            )
        ]

    def __str__(self):
        return f"{self.specialist} — {self.option}"


class SpecialistEventType(models.Model):
    specialist = models.ForeignKey(
        "accounts.SpecialistProfile",
        on_delete=models.CASCADE,
        related_name="event_types",
        verbose_name="Специалист",
    )
    event_type = models.ForeignKey(
        EventType,
        on_delete=models.PROTECT,
        related_name="specialist_event_types",
        verbose_name="Тип мероприятия",
    )

    class Meta:
        db_table = "specialist_event_type"
        verbose_name = "Подходит для"
        verbose_name_plural = "Подходит для"
        constraints = [
            models.UniqueConstraint(
                fields=["specialist", "event_type"],
                name="unique_specialist_event_type",
            )
        ]

    def __str__(self):
        return f"{self.specialist} — {self.event_type}"


class Photo(models.Model):
    class Kind(models.TextChoices):
        MAIN = "main", "Главное фото"
        ALBUM = "album", "Фотография альбома"

    specialist = models.ForeignKey(
        "accounts.SpecialistProfile",
        on_delete=models.CASCADE,
        related_name="photos",
        verbose_name="Специалист",
    )
    kind = models.CharField("Вид", max_length=20, choices=Kind.choices)
    album_title = models.CharField("Название альбома", max_length=50, blank=True)
    image = models.ImageField("Изображение", upload_to="photos/")
    is_cover = models.BooleanField("Обложка", default=False)
    sort_order = models.PositiveIntegerField("Порядок", default=0)

    class Meta:
        db_table = "photo"
        verbose_name = "Фотография"
        verbose_name_plural = "Фотографии"
        ordering = ["sort_order"]

    def __str__(self):
        if self.kind == self.Kind.ALBUM and self.album_title:
            return f"{self.album_title} — {self.sort_order}"
        return f"Главное фото — {self.sort_order}"


class Video(models.Model):
    specialist = models.ForeignKey(
        "accounts.SpecialistProfile",
        on_delete=models.CASCADE,
        related_name="videos",
        verbose_name="Специалист",
    )
    title = models.CharField("Название", max_length=50)
    url = models.URLField("Ссылка", max_length=500)
    sort_order = models.PositiveIntegerField("Порядок", default=0)

    class Meta:
        db_table = "video"
        verbose_name = "Видео"
        verbose_name_plural = "Видео"
        ordering = ["sort_order"]

    def __str__(self):
        return self.title


class ServicePackage(models.Model):
    specialist = models.ForeignKey(
        "accounts.SpecialistProfile",
        on_delete=models.CASCADE,
        related_name="packages",
        verbose_name="Специалист",
    )
    title = models.CharField("Название", max_length=200)
    description = models.TextField("Описание", blank=True)
    included = models.TextField("Что входит", blank=True)
    hours = models.PositiveIntegerField("Часы", null=True, blank=True)
    season_from = models.DecimalField("Цена в сезон, от", max_digits=10, decimal_places=2)
    season_to = models.DecimalField("Цена в сезон, до", max_digits=10, decimal_places=2)
    is_hidden = models.BooleanField("Скрыт", default=False)

    class Meta:
        db_table = "service_package"
        verbose_name = "Пакет услуг"
        verbose_name_plural = "Пакеты услуг"

    def __str__(self):
        return self.title


class DirectionRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "На рассмотрении"
        APPROVED = "approved", "Одобрена"
        REJECTED = "rejected", "Отклонена"

    specialist = models.ForeignKey(
        "accounts.SpecialistProfile",
        on_delete=models.CASCADE,
        related_name="direction_requests",
        verbose_name="Специалист",
    )
    proposed_name = models.CharField("Название", max_length=100)
    comment = models.TextField("Пояснение", blank=True)
    status = models.CharField(
        "Статус",
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField("Когда подана", auto_now_add=True)
    decided_at = models.DateTimeField("Когда рассмотрена", null=True, blank=True)

    class Meta:
        db_table = "direction_request"
        verbose_name = "Заявка на категорию"
        verbose_name_plural = "Заявки на категорию"
        ordering = ["-created_at"]

    def __str__(self):
        return self.proposed_name


class AvailabilityRule(models.Model):
    class Frequency(models.TextChoices):
        ONCE = "once", "Один день"
        WEEKLY = "weekly", "Каждую неделю"
        MONTHLY = "monthly", "Каждый месяц"
        YEARLY = "yearly", "Каждый год"

    class MonthlyMode(models.TextChoices):
        DAY_OF_MONTH = "day_of_month", "То же число"
        NTH_WEEKDAY = "nth_weekday", "Такой же день недели месяца"

    specialist = models.ForeignKey(
        "accounts.SpecialistProfile",
        on_delete=models.CASCADE,
        related_name="availability_rules",
        verbose_name="Специалист",
    )
    start_date = models.DateField("Первый день")
    frequency = models.CharField("Повтор", max_length=20, choices=Frequency.choices)
    weekdays = models.CharField("Дни недели", max_length=20, blank=True)
    monthly_mode = models.CharField(
        "Месячный режим",
        max_length=20,
        choices=MonthlyMode.choices,
        blank=True,
    )
    occurrence_count = models.PositiveIntegerField(
        "Число повторов",
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "availability_rule"
        verbose_name = "Правило занятости"
        verbose_name_plural = "Правила занятости"

    def __str__(self):
        return f"{self.specialist} — {self.start_date}"


class AvailabilityException(models.Model):
    rule = models.ForeignKey(
        AvailabilityRule,
        on_delete=models.CASCADE,
        related_name="exceptions",
        verbose_name="Правило",
    )
    date = models.DateField("Дата")

    class Meta:
        db_table = "availability_exception"
        verbose_name = "Исключение из правила"
        verbose_name_plural = "Исключения из правил"
        constraints = [
            models.UniqueConstraint(
                fields=["rule", "date"],
                name="unique_availability_exception",
            )
        ]
        ordering = ["date"]

    def __str__(self):
        return f"{self.rule} — {self.date}"