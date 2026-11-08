import csv
import io
import json
from pathlib import Path
from openpyxl import Workbook
from openpyxl.drawing.image import Image as ExcelImage
from PIL import Image as RasterImage
from django.http import HttpResponse
from .importing import COLUMNS


def export_products(queryset, excel=True):
    columns = list(COLUMNS.values())
    book = Workbook() if excel else None
    sheet = book.active if book else None
    if sheet:
        sheet.title = "Товары"
        sheet.append(columns)
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        if excel
        else "text/csv; charset=utf-8-sig"
    )
    response["Content-Disposition"] = (
        'attachment; filename="atelier-noir-products.'
        + ("xlsx" if excel else "csv")
        + '"'
    )
    writer = None
    if not excel:
        response.write("\ufeff")
        writer = csv.writer(response, delimiter=";")
        writer.writerow(columns)
    row_number = 2
    for product in queryset.select_related("category").prefetch_related(
        "images", "variants"
    ):
        image = product.images.first()
        for index, variant in enumerate(product.variants.all()):
            values = [
                variant.sku,
                product.name,
                product.slug,
                product.category.name,
                product.description,
                float(variant.price),
                variant.stock,
                variant.size,
                variant.color,
                variant.color_hex,
                json.dumps(product.characteristics, ensure_ascii=False),
                Path(image.image.name).name
                if image and (not excel or index == 0)
                else "",
                "Да" if variant.active else "Нет",
                product.weight,
            ]
            if excel:
                sheet.append(values)
                for cell in sheet[row_number]:
                    if isinstance(cell.value, str):
                        cell.data_type = "s"
                if (
                    image
                    and index == 0
                    and image.image.storage.exists(image.image.name)
                ):
                    buffer = io.BytesIO()
                    with RasterImage.open(image.image.path) as raster:
                        raster.convert("RGB").save(buffer, "PNG")
                    buffer.seek(0)
                    picture = ExcelImage(buffer)
                    picture.width = 65
                    picture.height = 85
                    sheet.add_image(picture, f"L{row_number}")
                    sheet.row_dimensions[row_number].height = 68
                row_number += 1
            else:
                writer.writerow(
                    [
                        "'" + v
                        if isinstance(v, str)
                        and v.startswith(("=", "+", "-", "@", "\t", "\r"))
                        else v
                        for v in values
                    ]
                )
    if excel:
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
        for col in sheet.columns:
            sheet.column_dimensions[col[0].column_letter].width = 24
        stream = io.BytesIO()
        book.save(stream)
        response.write(stream.getvalue())
    return response
