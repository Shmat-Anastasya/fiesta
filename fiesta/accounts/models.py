from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class AccountManager(BaseUserManager):
    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError("Нужна почта")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("is_active", True)
        return self.create_user(email, password, **extra)


class Account(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        CUSTOMER = "customer", "Пользователь"
        SPECIALIST = "specialist", "Специалист"

    email = models.EmailField("Почта", unique=True)
    role = models.CharField(
        "Роль",
        max_length=20,
        choices=Role.choices,
        default=Role.CUSTOMER,
    )
    is_active = models.BooleanField("Активна", default=True)
    is_staff = models.BooleanField("Доступ в админку", default=False)
    date_joined = models.DateTimeField("Регистрация", auto_now_add=True)
    telegram_link_code = models.CharField(
        "Код Telegram",
        max_length=64,
        unique=True,
        null=True,
        blank=True,
    )
    telegram_chat_id = models.CharField("Чат Telegram", max_length=64, blank=True)
    telegram_is_connected = models.BooleanField("Бот привязан", default=False)
    telegram_connected_at = models.DateTimeField(
        "Когда привязан",
        null=True,
        blank=True,
    )

    objects = AccountManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "account"
        verbose_name = "Учётная запись"
        verbose_name_plural = "Учётные записи"

    def __str__(self):
        return self.email


class UserProfile(models.Model):
    account = models.OneToOneField(
        Account,
        on_delete=models.CASCADE,
        related_name="user_profile",
        verbose_name="Учётная запись",
    )
    first_name = models.CharField("Имя", max_length=100)
    last_name = models.CharField("Фамилия", max_length=100)
    patronymic = models.CharField("Отчество", max_length=100, blank=True)
    birth_date = models.DateField("День рождения", null=True, blank=True)
    phone = models.CharField("Телефон", max_length=30, blank=True)
    city = models.CharField("Город", max_length=100, default="Минск")
    photo = models.ImageField("Фото", upload_to="profiles/", blank=True)
    instagram = models.CharField("Instagram", max_length=200, blank=True)
    telegram = models.CharField("Telegram", max_length=200, blank=True)
    pinterest = models.CharField("Pinterest", max_length=200, blank=True)

    class Meta:
        db_table = "user_profiles"
        verbose_name = "Профиль пользователя"
        verbose_name_plural = "Профили пользователей"

    def __str__(self):
        return f"{self.last_name} {self.first_name}"


class SpecialistProfile(models.Model):
    account = models.OneToOneField(
        Account,
        on_delete=models.CASCADE,
        related_name="specialist_profile",
        verbose_name="Учётная запись",
    )
    first_name = models.CharField("Имя", max_length=100)
    last_name = models.CharField("Фамилия", max_length=100)
    patronymic = models.CharField("Отчество", max_length=100, blank=True)
    birth_date = models.DateField("День рождения", null=True, blank=True)
    phone = models.CharField("Телефон", max_length=30, blank=True)
    city = models.CharField("Город", max_length=100, default="Минск")
    photo = models.ImageField("Фото", upload_to="profiles/", blank=True)
    instagram = models.CharField("Instagram", max_length=200, blank=True)
    telegram = models.CharField("Telegram", max_length=200, blank=True)
    pinterest = models.CharField("Pinterest", max_length=200, blank=True)
    category = models.ForeignKey(
        "catalog.Category",
        on_delete=models.PROTECT,
        related_name="specialists",
        verbose_name="Категория",
    )
    description = models.TextField("Описание", blank=True)
    career_start = models.DateField("Начало карьеры", null=True, blank=True)
    discount_text = models.CharField("Дополнительно", max_length=255, blank=True)

    class Meta:
        db_table = "specialist_profiles"
        verbose_name = "Профиль специалиста"
        verbose_name_plural = "Профили специалистов"

    def __str__(self):
        return f"{self.last_name} {self.first_name}"


class ContactMessage(models.Model):
    name = models.CharField("Имя", max_length=100)
    email = models.EmailField("Почта")
    text = models.TextField("Текст")
    created_at = models.DateTimeField("Когда отправлено", auto_now_add=True)
    is_read = models.BooleanField("Прочитано", default=False)

    class Meta:
        db_table = "contact_message"
        verbose_name = "Сообщение администратору"
        verbose_name_plural = "Сообщения администратору"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} — {self.email}"


class AdminLog(models.Model):
    actor = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="admin_logs",
        verbose_name="Администратор",
    )
    action = models.CharField("Действие", max_length=200)
    entity = models.CharField("Таблица", max_length=100)
    entity_id = models.PositiveIntegerField("Номер записи")
    detail = models.TextField("Пояснение", blank=True)
    created_at = models.DateTimeField("Когда сделано", auto_now_add=True)

    class Meta:
        db_table = "admin_log"
        verbose_name = "Запись журнала"
        verbose_name_plural = "Журнал администратора"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} — {self.entity}"