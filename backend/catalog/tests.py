import io
import tempfile
from pathlib import Path
from PIL import Image
from openpyxl import Workbook
from openpyxl.drawing.image import Image as ExcelImage
from django.test import TestCase, override_settings
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from .models import ImportSettings, ImportJob, Product, Variant
from .importing import COLUMNS, validate_job, apply_job


class ImportTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        override = override_settings(
            MEDIA_ROOT=Path(self.tmp.name),
            PRIVATE_IMPORT_ROOT=Path(self.tmp.name) / "private",
        )
        override.enable()
        self.addCleanup(override.disable)
        self.profile = ImportSettings.objects.create()

    def workbook(self, price=1200):
        book = Workbook()
        sheet = book.active
        sheet.append(list(COLUMNS.values()))
        sheet.append(
            [
                "TEST-M",
                "Тестовая рубашка",
                "test-shirt",
                "Рубашки",
                "Описание",
                price,
                5,
                "M",
                "Чёрный",
                "#171717",
                '{"Состав":"Хлопок"}',
                "",
                "Да",
                500,
            ]
        )
        pic = io.BytesIO()
        Image.new("RGB", (20, 20), "black").save(pic, "PNG")
        pic.seek(0)
        sheet.add_image(ExcelImage(pic), "L2")
        result = io.BytesIO()
        book.save(result)
        return result.getvalue()

    def job(self, price=1200):
        job = ImportJob(profile=self.profile)
        job.file.save("test.xlsx", ContentFile(self.workbook(price)))
        return job

    def test_embedded_excel_photo_import_is_previewed_then_applied_once(self):
        job = self.job()
        validate_job(job)
        job.refresh_from_db()
        self.assertEqual(job.status, "validated", job.report)
        self.assertEqual(Product.objects.count(), 0)
        apply_job(job)
        job.refresh_from_db()
        apply_job(job)
        self.assertEqual(Product.objects.count(), 1)
        self.assertEqual(Variant.objects.get().stock, 5)
        self.assertTrue(
            Product.objects.get()
            .images.get()
            .image.storage.exists(Product.objects.get().images.get().image.name)
        )

    def test_invalid_row_never_changes_catalog(self):
        job = self.job(-1)
        validate_job(job)
        job.refresh_from_db()
        self.assertEqual(job.status, "error")
        self.assertIn("Строка 2", job.report)
        with self.assertRaises(ValidationError):
            apply_job(job)
        self.assertEqual(Product.objects.count(), 0)

    def test_excel_export_with_photo_can_be_imported_again(self):
        from .exporting import export_products

        job = self.job()
        validate_job(job)
        apply_job(job)
        response = export_products(Product.objects.all(), excel=True)
        second = ImportJob(profile=self.profile)
        second.file.save("roundtrip.xlsx", ContentFile(response.content))
        validate_job(second)
        second.refresh_from_db()
        self.assertEqual(second.status, "validated", second.report)
        apply_job(second)
        self.assertEqual(Variant.objects.count(), 1)

    def test_import_template_and_notification_preview_require_staff_access(self):
        job = self.job()
        self.assertEqual(self.client.get(job.file.url).status_code, 302)
        self.assertEqual(
            self.client.get("/admin/catalog/importjob/template/").status_code, 302
        )
        self.assertEqual(
            self.client.get("/admin/integrations/notification/1/preview/").status_code,
            302,
        )
        user = get_user_model().objects.create_superuser(
            "staff", "staff@example.test", "long-random-test-password"
        )
        self.client.force_login(user)
        self.assertEqual(self.client.get(job.file.url).status_code, 200)
        response = self.client.get("/admin/catalog/importjob/template/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b"PK"))
