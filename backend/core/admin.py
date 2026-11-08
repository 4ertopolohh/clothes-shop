from django.contrib import admin
from .models import StoreSettings, Page


class SingletonAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not self.model.objects.exists() and super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(StoreSettings)
class StoreSettingsAdmin(SingletonAdmin):
    fieldsets = [
        (
            "Бренд и контакты",
            {
                "fields": (
                    "brand",
                    "tagline",
                    "announcement",
                    "email",
                    "phone",
                    "address",
                    "legal_details",
                )
            },
        ),
        ("Первый экран", {"fields": ("hero_title", "hero_text", "hero_image")}),
        ("О бренде", {"fields": ("about_title", "about_text", "about_image")}),
        (
            "Оформление и разработка",
            {"fields": ("reservation_minutes", "local_test_mode")},
        ),
    ]


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ["title", "slug", "published", "updated_at"]
    list_filter = ["published"]
    search_fields = ["title", "body"]
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ["updated_at"]
