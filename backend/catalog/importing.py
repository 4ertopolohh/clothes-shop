import csv
import hashlib
import io
import json
import re
import zipfile
from decimal import Decimal, InvalidOperation
from pathlib import PurePosixPath
from PIL import Image
from openpyxl import Workbook, load_workbook
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils.text import slugify
from .models import Category, Product, ProductImage, Variant, ImportJob

COLUMNS = {
    "sku": "Артикул",
    "name": "Название",
    "slug": "Адрес товара",
    "category": "Категория",
    "description": "Описание",
    "price": "Цена",
    "stock": "Количество",
    "size": "Размер",
    "color": "Цвет",
    "color_hex": "Цвет HEX",
    "characteristics": "Характеристики",
    "image": "Фото",
    "active": "В наличии",
    "weight": "Вес, г",
}


def template_bytes():
    book = Workbook()
    sheet = book.active
    sheet.title = "Товары"
    sheet.append(list(COLUMNS.values()))
    sheet.append(
        [
            "AN-NEW-M-BLACK",
            "Рубашка «Линия»",
            "rubashka-liniya",
            "Рубашки",
            "Свободная рубашка.",
            11900,
            10,
            "M",
            "Чёрный",
            "#171717",
            '{"Состав":"100% хлопок","Уход":"30 °C"}',
            "shirt.jpg",
            "Да",
            500,
        ]
    )
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    from openpyxl.styles import Font, PatternFill

    for cell in sheet[1]:
        cell.font = Font(color="FFFFFF", bold=True)
        cell.fill = PatternFill("solid", fgColor="252522")
    for column in sheet.columns:
        sheet.column_dimensions[column[0].column_letter].width = 24
    guide = book.create_sheet("Инструкция")
    guide.append(["Импорт ATELIER NOIR"])
    for line in [
        "Одна строка = один артикул / размер / цвет. Разные варианты одной вещи используют одинаковый Адрес товара.",
        "Фото: вставьте изображение в строку Excel либо укажите имя файла из приложенного ZIP. Сетевые URL не загружаются.",
        "Характеристики — JSON-объект с текстовыми значениями. Цена в рублях, количество — целое неотрицательное.",
        "В наличии: Да / Нет. Нет отключает вариант. Нулевое количество запрещает покупку.",
        "Сначала действие «Проверить», затем «Применить». При ошибках таблица не применяется.",
    ]:
        guide.append([line])
    guide.column_dimensions["A"].width = 130
    result = io.BytesIO()
    book.save(result)
    return result.getvalue()


def safe_zip(data, max_bytes=40 * 1024 * 1024):
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
        infos = archive.infolist()
        if len(infos) > 5000 or sum(i.file_size for i in infos) > max_bytes:
            raise ValidationError("Архив слишком большой после распаковки.")
        if any(i.file_size > 15 * 1024 * 1024 for i in infos):
            raise ValidationError("Слишком большой файл в архиве.")
        return archive
    except zipfile.BadZipFile:
        raise ValidationError("Некорректный ZIP или Excel.") from None


def normalize_image(data):
    if len(data) > 10 * 1024 * 1024:
        raise ValidationError("Фото больше 10 МБ.")
    try:
        with Image.open(io.BytesIO(data)) as picture:
            if picture.width * picture.height > 25_000_000:
                raise ValidationError("Фото превышает 25 мегапикселей.")
            if picture.format not in ("JPEG", "PNG", "WEBP"):
                raise ValidationError("Фото должно быть JPG, PNG или WebP.")
            picture.load()
            picture = picture.convert("RGB")
            picture.thumbnail((1800, 2200))
            output = io.BytesIO()
            picture.save(output, "WEBP", quality=86)
            return output.getvalue()
    except (OSError, ValueError, Image.DecompressionBombError):
        raise ValidationError("Не удалось прочитать изображение.") from None


def read_rows(job):
    if job.file.size > 15 * 1024 * 1024:
        raise ValidationError("Размер таблицы превышает 15 МБ.")
    job.file.open("rb")
    data = job.file.read()
    job.file.close()
    embedded = {}
    if job.file.name.lower().endswith(".xlsx"):
        safe_zip(data, 70 * 1024 * 1024).close()
        try:
            book = load_workbook(io.BytesIO(data), data_only=True)
            sheet = book.worksheets[0]
            if (
                sheet.max_row > min(job.profile.max_rows, 5000) + 1
                or sheet.max_column > 100
            ):
                raise ValidationError("Превышено ограничение числа строк или колонок.")
            rows = list(sheet.iter_rows(values_only=True))
            for image in sheet._images:
                anchor = getattr(image.anchor, "_from", None)
                if anchor is not None:
                    embedded[anchor.row + 1] = image._data()
            book.close()
        except ValidationError:
            raise
        except Exception:
            raise ValidationError(
                "Не удалось прочитать Excel. Используйте шаблон .xlsx."
            ) from None
    elif job.file.name.lower().endswith(".csv"):
        try:
            text = data.decode("utf-8-sig")
            dialect = csv.Sniffer().sniff(text[:4096], delimiters=";,\t")
            rows = list(csv.reader(io.StringIO(text), dialect))
        except (UnicodeError, csv.Error):
            raise ValidationError(
                "CSV должен быть UTF-8 с разделителем ; или ,."
            ) from None
    else:
        raise ValidationError("Поддерживаются .xlsx и .csv.")
    if not rows:
        raise ValidationError("Таблица пуста.")
    if len(rows) > min(job.profile.max_rows, 5000) + 1:
        raise ValidationError("Превышен лимит строк профиля.")
    headers = [str(x or "").strip() for x in rows[0]]
    mapping = {
        k: headers.index(job.profile.column_map.get(k, v))
        if job.profile.column_map.get(k, v) in headers
        else headers.index(k)
        if k in headers
        else None
        for k, v in COLUMNS.items()
    }
    for required in ("sku", "name", "category", "price", "stock", "size", "color"):
        if mapping[required] is None:
            raise ValidationError("Отсутствует колонка: " + COLUMNS[required])
    photos = {}
    if job.photos:
        if job.photos.size > 30 * 1024 * 1024:
            raise ValidationError("ZIP больше 30 МБ.")
        job.photos.open("rb")
        with safe_zip(job.photos.read(), 80 * 1024 * 1024) as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                name = PurePosixPath(info.filename.replace("\\", "/")).name
                if name.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                    if name in photos:
                        raise ValidationError(
                            "В ZIP есть повторяющиеся имена фото: " + name
                        )
                    photos[name] = archive.read(info)
        job.photos.close()
    parsed = []
    errors = []
    seen = set()
    options = set()
    for number, values in enumerate(rows[1:], 2):
        if not any(v is not None and str(v).strip() for v in values):
            continue
        row = {
            key: str(
                values[index]
                if index < len(values) and values[index] is not None
                else ""
            ).strip()
            if index is not None
            else ""
            for key, index in mapping.items()
        }
        try:
            if any(not row[k] for k in ("sku", "name", "category", "size", "color")):
                raise ValueError(
                    "Заполните артикул, название, категорию, размер и цвет."
                )
            if (
                len(row["sku"]) > 80
                or len(row["name"]) > 200
                or len(row["size"]) > 20
                or len(row["color"]) > 50
                or len(row["category"]) > 100
            ):
                raise ValueError("Слишком длинное текстовое значение.")
            row["price"] = Decimal(row["price"].replace(",", "."))
            if (
                not row["price"].is_finite()
                or row["price"] <= 0
                or row["price"] > Decimal("99999999.99")
                or row["price"] != row["price"].quantize(Decimal(".01"))
            ):
                raise ValueError(
                    "Цена должна быть положительной, максимум 2 знака после запятой."
                )
            stock_value = Decimal(row["stock"])
            if (
                not stock_value.is_finite()
                or stock_value != int(stock_value)
                or not 0 <= stock_value <= 1000000
            ):
                raise ValueError("Количество должно быть целым от 0 до 1000000.")
            row["stock"] = int(stock_value)
            row["weight"] = int(row["weight"] or 700)
            if not 1 <= row["weight"] <= 50000:
                raise ValueError("Вес должен быть от 1 до 50000 г.")
            row["slug"] = (
                slugify(row["slug"])
                or slugify(row["name"])
                or "product-" + hashlib.sha256(row["name"].encode()).hexdigest()[:12]
            )
            if len(row["slug"]) > 50:
                raise ValueError("Адрес товара длиннее 50 символов.")
            row["color_hex"] = row["color_hex"] or "#171717"
            if not re.fullmatch("#[0-9a-fA-F]{6}", row["color_hex"]):
                raise ValueError("Цвет HEX: #171717.")
            row["characteristics"] = json.loads(row["characteristics"] or "{}")
            if not isinstance(row["characteristics"], dict) or any(
                not isinstance(v, str) for v in row["characteristics"].values()
            ):
                raise ValueError("Характеристики: JSON-объект с текстовыми значениями.")
            row["active"] = row["active"].casefold() not in ("нет", "false", "0", "no")
            if row["sku"] in seen:
                raise ValueError("Артикул повторяется в таблице.")
            option = (row["slug"], row["size"], row["color"])
            if option in options:
                raise ValueError("Размер и цвет повторяются для одного товара.")
            seen.add(row["sku"])
            options.add(option)
            existing = (
                Variant.objects.select_related("product").filter(sku=row["sku"]).first()
            )
            if existing and not job.profile.update_existing:
                raise ValueError("Артикул существует; обновление отключено.")
            if existing and existing.reserved > row["stock"]:
                raise ValueError("Количество меньше действующего резерва.")
            if existing and existing.product.slug != row["slug"]:
                raise ValueError("Артикул уже принадлежит другому товару.")
            if (
                Variant.objects.filter(
                    product__slug=row["slug"], size=row["size"], color=row["color"]
                )
                .exclude(sku=row["sku"])
                .exists()
            ):
                raise ValueError("Размер и цвет заняты другим артикулом.")
            image = embedded.get(number)
            if row["image"] and not image:
                image = photos.get(row["image"])
                if not image:
                    raise ValueError(
                        "Фото не найдено в ZIP. Укажите имя файла или вставьте фото в Excel."
                    )
            row["photo_data"] = normalize_image(image) if image else None
            if (
                not row["photo_data"]
                and not ProductImage.objects.filter(product__slug=row["slug"]).exists()
            ):
                # A different variant of this product in this file can supply its shared photo.
                row["needs_photo"] = True
            parsed.append(row)
        except (
            ValueError,
            TypeError,
            InvalidOperation,
            ValidationError,
            OverflowError,
        ) as exc:
            errors.append(f"Строка {number}: {str(exc)[:250]}")
    photographed = {r["slug"] for r in parsed if r["photo_data"]}
    for row in parsed:
        if row.get("needs_photo") and row["slug"] not in photographed:
            errors.append(f"{row['sku']}: для нового товара требуется фото.")
    if not parsed and not errors:
        errors.append("Нет строк товаров.")
    if errors:
        raise ValidationError(errors[:80])
    return parsed


def validate_job(job):
    if job.status == "applied":
        return
    try:
        rows = read_rows(job)
        job.status = "validated"
        job.report = f"Проверено: {len(rows)} вариантов, {len({r['slug'] for r in rows})} товаров. Ошибок нет. Можно применить импорт."
    except ValidationError as exc:
        job.status = "error"
        job.report = "\n".join(exc.messages)
    job.save(update_fields=["status", "report"])


def apply_job(job):
    if job.status == "applied":
        return
    if job.status != "validated":
        raise ValidationError("Сначала проверьте импорт.")
    rows = read_rows(job)
    created_files = []
    try:
        with transaction.atomic():
            current = ImportJob.objects.select_for_update().get(pk=job.pk)
            if current.status == "applied":
                return
            attached = set()
            for row in rows:
                category, _ = Category.objects.get_or_create(
                    name=row["category"],
                    defaults={
                        "slug": slugify(row["category"])
                        or "category-"
                        + hashlib.sha256(row["category"].encode()).hexdigest()[:10]
                    },
                )
                product, _ = Product.objects.update_or_create(
                    slug=row["slug"],
                    defaults={
                        "name": row["name"],
                        "category": category,
                        "description": row["description"],
                        "characteristics": row["characteristics"],
                        "weight": row["weight"],
                    },
                )
                variant = Variant.objects.filter(sku=row["sku"]).first()
                if variant and row["stock"] < variant.reserved:
                    raise ValidationError(
                        "Резерв изменился после проверки. Проверьте импорт ещё раз."
                    )
                Variant.objects.update_or_create(
                    sku=row["sku"],
                    defaults={
                        "product": product,
                        **{
                            k: row[k]
                            for k in (
                                "size",
                                "color",
                                "color_hex",
                                "price",
                                "stock",
                                "active",
                            )
                        },
                    },
                )
                if row["photo_data"] and product.pk not in attached:
                    photo = ProductImage(
                        product=product,
                        alt=product.name,
                        position=product.images.count(),
                    )
                    photo.image.save(
                        row["slug"] + ".webp",
                        ContentFile(row["photo_data"]),
                        save=False,
                    )
                    created_files.append(photo.image)
                    photo.save()
                    attached.add(product.pk)
            current.status = "applied"
            current.report = f"Импорт применён: {len(rows)} вариантов."
            current.save(update_fields=["status", "report"])
    except Exception:
        for image in created_files:
            image.storage.delete(image.name)
        raise
