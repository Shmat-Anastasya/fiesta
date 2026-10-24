from django.contrib import admin

from .models import (
    Conversation,
    Favorite,
    Message,
    Project,
    Review,
    RoleCandidate,
    SavedTeam,
    SavedTeamMember,
)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "event_type", "event_date", "status")
    list_filter = ("status", "event_type")
    search_fields = ("title",)


@admin.register(RoleCandidate)
class RoleCandidateAdmin(admin.ModelAdmin):
    list_display = ("project", "role_title", "specialist", "status", "sort_order")
    list_filter = ("status", "category")
    search_fields = ("role_title",)


@admin.register(SavedTeam)
class SavedTeamAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "created_at")
    search_fields = ("title",)


@admin.register(SavedTeamMember)
class SavedTeamMemberAdmin(admin.ModelAdmin):
    list_display = ("team", "role_title", "specialist", "sort_order")
    search_fields = ("role_title",)


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("customer", "specialist", "created_at")


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("client", "specialist", "project", "created_at")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("conversation", "sender", "kind", "created_at", "read_at")
    list_filter = ("kind",)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("author", "specialist", "project", "rating", "is_hidden", "created_at")
    list_filter = ("is_hidden", "rating")
    search_fields = ("text", "reply")
