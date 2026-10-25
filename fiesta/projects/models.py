from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Project(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "В процессе"
        COMPLETED = "completed", "Завершён"

    owner = models.ForeignKey(
        "accounts.UserProfile",
        on_delete=models.CASCADE,
        related_name="projects",
        verbose_name="Владелец",
    )
    event_type = models.ForeignKey(
        "catalog.EventType",
        on_delete=models.PROTECT,
        related_name="projects",
        verbose_name="Тип мероприятия",
    )
    title = models.CharField("Название", max_length=200)
    event_date = models.DateField("Дата")
    description = models.TextField("Описание", blank=True)
    status = models.CharField(
        "Статус",
        max_length=20,
        choices=Status.choices,
        default=Status.IN_PROGRESS,
    )
    created_at = models.DateTimeField("Когда создан", auto_now_add=True)

    class Meta:
        db_table = "project"
        verbose_name = "Проект"
        verbose_name_plural = "Проекты"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class RoleCandidate(models.Model):
    class Status(models.TextChoices):
        SELECTED = "selected", "Выбран"
        INVITED = "invited", "Приглашён"
        ACCEPTED = "accepted", "Принял"
        DECLINED = "declined", "Отклонил"

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="role_candidates",
        verbose_name="Проект",
    )
    role_title = models.CharField("Роль", max_length=100)
    category = models.ForeignKey(
        "catalog.Category",
        on_delete=models.PROTECT,
        related_name="role_candidates",
        verbose_name="Категория",
        null=True,
        blank=True,
    )
    specialist = models.ForeignKey(
        "accounts.SpecialistProfile",
        on_delete=models.CASCADE,
        related_name="role_candidates",
        verbose_name="Специалист",
    )
    status = models.CharField(
        "Статус",
        max_length=20,
        choices=Status.choices,
        default=Status.SELECTED,
    )
    invitation_message = models.TextField("Текст приглашения", blank=True)
    decided_at = models.DateTimeField("Когда решил", null=True, blank=True)
    sort_order = models.PositiveIntegerField("Порядок", default=0)

    class Meta:
        db_table = "role_candidate"
        verbose_name = "Участник роли"
        verbose_name_plural = "Участники ролей"
        constraints = [
            models.UniqueConstraint(
                fields=["project", "role_title", "specialist"],
                name="unique_role_candidate",
            )
        ]
        ordering = ["sort_order"]

    def __str__(self):
        return f"{self.role_title} — {self.specialist}"


class SavedTeam(models.Model):
    owner = models.ForeignKey(
        "accounts.UserProfile",
        on_delete=models.CASCADE,
        related_name="saved_teams",
        verbose_name="Владелец",
    )
    title = models.CharField("Название", max_length=200)
    created_at = models.DateTimeField("Когда сохранена", auto_now_add=True)

    class Meta:
        db_table = "saved_team"
        verbose_name = "Сохранённая команда"
        verbose_name_plural = "Сохранённые команды"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class SavedTeamMember(models.Model):
    team = models.ForeignKey(
        SavedTeam,
        on_delete=models.CASCADE,
        related_name="members",
        verbose_name="Команда",
    )
    role_title = models.CharField("Роль", max_length=100)
    category = models.ForeignKey(
        "catalog.Category",
        on_delete=models.PROTECT,
        related_name="saved_team_members",
        verbose_name="Категория",
        null=True,
        blank=True,
    )
    specialist = models.ForeignKey(
        "accounts.SpecialistProfile",
        on_delete=models.CASCADE,
        related_name="saved_team_memberships",
        verbose_name="Специалист",
    )
    sort_order = models.PositiveIntegerField("Порядок", default=0)

    class Meta:
        db_table = "saved_team_member"
        verbose_name = "Участник сохранённой команды"
        verbose_name_plural = "Участники сохранённых команд"
        ordering = ["sort_order"]

    def __str__(self):
        return f"{self.role_title} — {self.specialist}"


class Favorite(models.Model):
    customer = models.ForeignKey(
        "accounts.UserProfile",
        on_delete=models.CASCADE,
        related_name="favorites",
        verbose_name="Пользователь",
    )
    specialist = models.ForeignKey(
        "accounts.SpecialistProfile",
        on_delete=models.CASCADE,
        related_name="favorites",
        verbose_name="Специалист",
    )
    created_at = models.DateTimeField("Когда добавлен", auto_now_add=True)

    class Meta:
        db_table = "favorite"
        verbose_name = "Избранное"
        verbose_name_plural = "Избранное"
        constraints = [
            models.UniqueConstraint(
                fields=["customer", "specialist"],
                name="unique_favorite",
            )
        ]

    def __str__(self):
        return f"{self.customer} — {self.specialist}"


class Conversation(models.Model):
    client = models.ForeignKey(
        "accounts.UserProfile",
        on_delete=models.CASCADE,
        related_name="conversations",
        verbose_name="Пользователь",
    )
    specialist = models.ForeignKey(
        "accounts.SpecialistProfile",
        on_delete=models.CASCADE,
        related_name="conversations",
        verbose_name="Специалист",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="conversations",
        verbose_name="Проект",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField("Когда начат", auto_now_add=True)

    class Meta:
        db_table = "conversation"
        verbose_name = "Диалог"
        verbose_name_plural = "Диалоги"
        ordering = ["-created_at"]

    def __str__(self):
        if self.project_id:
            return f"{self.client} — {self.specialist} ({self.project})"
        return f"{self.client} — {self.specialist}"


class Message(models.Model):
    class Kind(models.TextChoices):
        TEXT = "text", "Текст"
        PHOTO = "photo", "Фотография"
        FILE = "file", "Файл"
        VOICE = "voice", "Голосовое"

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name="Диалог",
    )
    sender = models.ForeignKey(
        "accounts.Account",
        on_delete=models.CASCADE,
        related_name="sent_messages",
        verbose_name="Отправитель",
    )
    text = models.TextField("Текст", blank=True)
    kind = models.CharField(
        "Вид",
        max_length=20,
        choices=Kind.choices,
        default=Kind.TEXT,
    )
    attachment = models.FileField("Вложение", upload_to="messages/", blank=True)
    created_at = models.DateTimeField("Когда отправлено", auto_now_add=True)
    read_at = models.DateTimeField("Когда прочитано", null=True, blank=True)

    class Meta:
        db_table = "message"
        verbose_name = "Сообщение"
        verbose_name_plural = "Сообщения"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sender} — {self.get_kind_display()}"


class Review(models.Model):
    author = models.ForeignKey(
        "accounts.UserProfile",
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name="Автор",
    )
    specialist = models.ForeignKey(
        "accounts.SpecialistProfile",
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name="Специалист",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name="Проект",
    )
    rating = models.PositiveSmallIntegerField(
        "Оценка",
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    text = models.TextField("Текст")
    reply = models.TextField("Ответ", blank=True)
    reply_at = models.DateTimeField("Когда ответил", null=True, blank=True)
    is_hidden = models.BooleanField("Скрыт", default=False)
    created_at = models.DateTimeField("Когда оставлен", auto_now_add=True)

    class Meta:
        db_table = "review"
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"
        constraints = [
            models.UniqueConstraint(
                fields=["author", "specialist", "project"],
                name="unique_review",
            ),
            models.CheckConstraint(
                condition=models.Q(rating__gte=1, rating__lte=5),
                name="review_rating_between_1_and_5",
            ),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.author} — {self.specialist} ({self.rating})"


class ReviewPhoto(models.Model):
    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name="photos",
        verbose_name="Отзыв",
    )
    image = models.ImageField("Изображение", upload_to="reviews/")
    sort_order = models.PositiveIntegerField("Порядок", default=0)

    class Meta:
        db_table = "review_photo"
        verbose_name = "Фото отзыва"
        verbose_name_plural = "Фото отзывов"
        ordering = ["sort_order", "pk"]

    def __str__(self):
        return f"{self.review} — {self.sort_order}"
