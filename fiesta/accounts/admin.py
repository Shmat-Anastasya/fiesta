from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import Account, AdminLog, ContactMessage, SpecialistProfile, UserProfile


class AccountCreationForm(UserCreationForm):
    class Meta:
        model = Account
        fields = ("email",)


class AccountChangeForm(UserChangeForm):
    class Meta:
        model = Account
        fields = "__all__"


@admin.register(Account)
class AccountAdmin(UserAdmin):
    form = AccountChangeForm
    add_form = AccountCreationForm
    model = Account
    ordering = ("email",)
    list_display = ("email", "role", "is_staff", "is_active")
    search_fields = ("email",)
    readonly_fields = ("last_login", "date_joined")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Роль", {"fields": ("role",)}),
        ("Права", {"fields": ("is_active", "is_staff", "is_superuser")}),
        (
            "Telegram",
            {
                "fields": (
                    "telegram_link_code",
                    "telegram_chat_id",
                    "telegram_is_connected",
                    "telegram_connected_at",
                )
            },
        ),
        ("Даты", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "is_staff", "is_active"),
            },
        ),
    )

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("last_name", "first_name", "city", "account")
    search_fields = ("last_name", "first_name", "account__email")


@admin.register(SpecialistProfile)
class SpecialistProfileAdmin(admin.ModelAdmin):
    list_display = ("last_name", "first_name", "category", "city", "account")
    search_fields = ("last_name", "first_name", "account__email")

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "is_read", "created_at")
    list_filter = ("is_read",)
    search_fields = ("name", "email", "text")

@admin.register(AdminLog)
class AdminLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "entity", "entity_id")
    list_filter = ("entity",)
    search_fields = ("action", "entity", "detail")    