from django.contrib import admin

from .models import (
    AvailabilityException,
    AvailabilityRule,
    Category,
    CategoryPriceField,
    DetailOption,
    DirectionRequest,
    EventType,
    Photo,
    ServicePackage,
    SpecialistDetail,
    SpecialistEventType,
    SpecialistPrice,
    Video,
)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_hidden", "sort_order")
    search_fields = ("name",)

@admin.register(CategoryPriceField)
class CategoryPriceFieldAdmin(admin.ModelAdmin):
    list_display = ("category", "kind", "label", "sort_order")
    list_filter = ("category",)

@admin.register(DetailOption)
class DetailOptionAdmin(admin.ModelAdmin):
    list_display = ("category", "group_title", "title", "sort_order")
    list_filter = ("category",)
    search_fields = ("title", "group_title")

@admin.register(EventType)
class EventTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "sort_order")
    search_fields = ("name",)

@admin.register(SpecialistPrice)
class SpecialistPriceAdmin(admin.ModelAdmin):
    list_display = ("specialist", "price_field", "amount")
    list_filter = ("price_field__category",)

@admin.register(SpecialistDetail)
class SpecialistDetailAdmin(admin.ModelAdmin):
    list_display = ("specialist", "option")
    list_filter = ("option__category",)

@admin.register(SpecialistEventType)
class SpecialistEventTypeAdmin(admin.ModelAdmin):
    list_display = ("specialist", "event_type")
    list_filter = ("event_type",)

@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ("specialist", "kind", "album_title", "is_cover", "sort_order")
    list_filter = ("kind",)

@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ("specialist", "title", "sort_order")
    search_fields = ("title",)

@admin.register(ServicePackage)
class ServicePackageAdmin(admin.ModelAdmin):
    list_display = ("specialist", "title", "season_from", "season_to", "is_hidden")
    list_filter = ("is_hidden",)
    search_fields = ("title",)

@admin.register(DirectionRequest)
class DirectionRequestAdmin(admin.ModelAdmin):
    list_display = ("proposed_name", "specialist", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("proposed_name",)

@admin.register(AvailabilityRule)
class AvailabilityRuleAdmin(admin.ModelAdmin):
    list_display = ("specialist", "start_date", "frequency", "occurrence_count")
    list_filter = ("frequency",)

@admin.register(AvailabilityException)
class AvailabilityExceptionAdmin(admin.ModelAdmin):
    list_display = ("rule", "date")