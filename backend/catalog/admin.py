from django.contrib import admin, messages
from django.core.exceptions import ValidationError, PermissionDenied
from django.http import HttpResponse
from django.urls import path
from django.utils.html import format_html
from .models import Category, Product, ProductImage, Variant, ImportSettings, ImportJob
from .importing import validate_job, apply_job, template_bytes


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "position"]
    list_editable = ["position"]
    prepopulated_fields = {"slug": ("name",)}


class ImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0
    fields = ["image", "alt", "position", "preview"]
    readonly_fields = ["preview"]

    @admin.display(description="Превью")
    def preview(self, obj):
        return (
            format_html('<img src="{}" width="65" alt="">', obj.image.url)
            if obj.image
            else "—"
        )


class VariantInline(admin.TabularInline):
    model = Variant
    extra = 0
    fields = [
        "sku",
        "size",
        "color",
        "color_hex",
        "price",
        "stock",
        "reserved",
        "active",
    ]
    readonly_fields = ["reserved"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    actions = ["export_excel", "export_csv"]

    @admin.action(description="Экспорт товаров в Excel с фото", permissions=["view"])
    def export_excel(self, request, queryset):
        from .exporting import export_products

        return export_products(queryset, excel=True)

    @admin.action(description="Экспорт товаров в CSV", permissions=["view"])
    def export_csv(self, request, queryset):
        from .exporting import export_products

        return export_products(queryset, excel=False)

    list_display = ["name", "category", "active", "is_new", "position", "preview"]
    list_filter = ["category", "active", "is_new"]
    search_fields = ["name", "variants__sku"]
    list_editable = ["active", "is_new", "position"]
    inlines = [ImageInline, VariantInline]
    prepopulated_fields = {"slug": ("name",)}
    fieldsets = [
        (
            "Товар",
            {"fields": ("name", "slug", "category", "description", "characteristics")},
        ),
        ("Витрина", {"fields": ("active", "badge", "is_new", "position")}),
        (
            "Упаковка для расчёта СДЭК",
            {"fields": ("weight", "length", "width", "height")},
        ),
    ]

    @admin.display(description="Фото")
    def preview(self, obj):
        photo = obj.images.first()
        return (
            format_html('<img src="{}" width="40" alt="">', photo.image.url)
            if photo
            else "Нет фото"
        )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("category")
            .prefetch_related("images")
        )


@admin.register(Variant)
class VariantAdmin(admin.ModelAdmin):
    list_display = [
        "sku",
        "product",
        "size",
        "color",
        "price",
        "stock",
        "reserved",
        "available",
        "active",
    ]
    list_filter = ["active", "size", "color", "product__category"]
    search_fields = ["sku", "product__name"]
    readonly_fields = ["reserved", "available"]
    list_editable = ["price", "stock", "active"]

    @admin.display(description="Доступно")
    def available(self, obj):
        return obj.available


@admin.register(ImportSettings)
class ImportSettingsAdmin(admin.ModelAdmin):
    list_display = ["title", "update_existing", "max_rows"]


@admin.register(ImportJob)
class ImportJobAdmin(admin.ModelAdmin):
    list_display = ["__str__", "profile", "status", "created_at"]
    list_filter = ["status"]
    actions = ["validate_import", "apply_import"]
    readonly_fields = ["status", "report", "created_at", "template_link"]
    fields = [
        "template_link",
        "profile",
        "file",
        "photos",
        "status",
        "report",
        "created_at",
    ]

    @admin.display(description="Шаблон и инструкция")
    def template_link(self, obj):
        return format_html(
            '<a href="{}">Скачать Excel-шаблон с примером и инструкцией</a>',
            "/admin/catalog/importjob/template/",
        )

    def get_urls(self):
        return [
            path(
                "files/<path:name>",
                self.admin_site.admin_view(self.private_file),
                name="catalog_private_import_file",
            ),
            path(
                "template/",
                self.admin_site.admin_view(self.template_view),
                name="catalog_import_template",
            ),
        ] + super().get_urls()

    def private_file(self, request, name):
        from django.shortcuts import get_object_or_404
        from django.db.models import Q
        from django.http import FileResponse
        from pathlib import Path

        job = get_object_or_404(ImportJob, Q(file=name) | Q(photos=name))
        if not self.has_view_permission(request, job):
            raise PermissionDenied
        uploaded = job.file if job.file.name == name else job.photos
        return FileResponse(
            uploaded.storage.open(name, "rb"),
            as_attachment=True,
            filename=Path(name).name,
        )

    def template_view(self, request):
        if not self.has_add_permission(request):
            raise PermissionDenied
        response = HttpResponse(
            template_bytes(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = (
            'attachment; filename="atelier-noir-import.xlsx"'
        )
        return response

    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields + (
            ["file", "photos", "profile"] if obj and obj.status == "applied" else []
        )

    def save_model(self, request, obj, form, change):
        if change and any(
            x in form.changed_data for x in ("file", "photos", "profile")
        ):
            obj.status = "new"
            obj.report = "Файлы изменены. Выполните проверку повторно."
        super().save_model(request, obj, form, change)

    @admin.action(description="1. Проверить выбранные импорты", permissions=["change"])
    def validate_import(self, request, queryset):
        for job in queryset:
            validate_job(job)
        self.message_user(
            request, "Проверка завершена. Откройте результат каждого импорта."
        )

    @admin.action(
        description="2. Применить проверенные импорты", permissions=["change"]
    )
    def apply_import(self, request, queryset):
        if (
            not request.user.has_perm("catalog.add_product")
            or not request.user.has_perm("catalog.change_product")
            or not request.user.has_perm("catalog.change_variant")
        ):
            raise PermissionDenied
        for job in queryset:
            try:
                apply_job(job)
                self.message_user(request, f"{job}: применён.")
            except ValidationError as exc:
                self.message_user(request, "; ".join(exc.messages), messages.ERROR)
            except Exception:
                self.message_user(
                    request,
                    "Импорт не применён. Проверьте файл, ограничения и совпадения артикулов.",
                    messages.ERROR,
                )
