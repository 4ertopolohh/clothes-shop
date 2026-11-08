from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from core.storage import PrivateImportStorage


class Category(models.Model):
    name = models.CharField("Название", max_length=100, unique=True)
    slug = models.SlugField("Адрес", unique=True)
    position = models.PositiveIntegerField("Порядок", default=0)

    class Meta:
        ordering = ["position", "name"]
        verbose_name = "Категория"
        verbose_name_plural = "Категории"

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField("Название", max_length=200)
    slug = models.SlugField("Адрес", unique=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
        verbose_name="Категория",
    )
    description = models.TextField("Описание")
    characteristics = models.JSONField(
        "Характеристики",
        default=dict,
        blank=True,
        help_text='Объект: {"Состав": "100% хлопок", "Уход": "30 °C"}.',
    )
    badge = models.CharField("Метка", max_length=50, blank=True)
    is_new = models.BooleanField("Новинка", default=False)
    active = models.BooleanField("Опубликован", default=True)
    position = models.PositiveIntegerField("Порядок", default=0)
    weight = models.PositiveIntegerField("Вес, г", default=700)
    length = models.PositiveIntegerField("Длина упаковки, см", default=35)
    width = models.PositiveIntegerField("Ширина упаковки, см", default=25)
    height = models.PositiveIntegerField("Высота упаковки, см", default=8)
    updated_at = models.DateTimeField("Обновлён", auto_now=True)

    class Meta:
        ordering = ["position", "id"]
        verbose_name = "Товар"
        verbose_name_plural = "Товары"

    def clean(self):
        from django.core.exceptions import ValidationError

        if not isinstance(self.characteristics, dict) or any(
            not isinstance(k, str) or not isinstance(v, str)
            for k, v in self.characteristics.items()
        ):
            raise ValidationError(
                {
                    "characteristics": "Укажите объект с текстовыми названиями и значениями."
                }
            )

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images", verbose_name="Товар"
    )
    image = models.ImageField("Фото", upload_to="products/")
    alt = models.CharField("Описание изображения", max_length=200, blank=True)
    position = models.PositiveIntegerField("Порядок", default=0)

    class Meta:
        ordering = ["position", "id"]
        verbose_name = "Фотография"
        verbose_name_plural = "Фотографии"


class Variant(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="variants", verbose_name="Товар"
    )
    sku = models.CharField("Артикул", max_length=80, unique=True)
    size = models.CharField("Размер", max_length=20)
    color = models.CharField("Цвет", max_length=50)
    color_hex = models.CharField("Цвет HEX", max_length=7, default="#171717")
    price = models.DecimalField(
        "Цена, ₽",
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    stock = models.PositiveIntegerField(
        "Остаток, шт.",
        default=0,
        help_text="Физическое количество, включая резерв. Для продажи доступно: остаток минус резерв.",
    )
    reserved = models.PositiveIntegerField("В резерве, шт.", default=0, editable=False)
    active = models.BooleanField("Доступен к продаже", default=True)

    @property
    def available(self):
        return max(0, self.stock - self.reserved)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "size", "color"], name="unique_product_option"
            ),
            models.CheckConstraint(
                condition=models.Q(stock__gte=models.F("reserved")),
                name="stock_covers_reserve",
            ),
            models.CheckConstraint(
                condition=models.Q(price__gt=0), name="positive_variant_price"
            ),
        ]
        verbose_name = "Вариант товара"
        verbose_name_plural = "Размеры, цвета и остатки"

    def clean(self):
        import re
        from django.core.exceptions import ValidationError

        if not re.fullmatch(r"#[0-9a-fA-F]{6}", self.color_hex):
            raise ValidationError({"color_hex": "Формат: #171717."})
        if self.stock < self.reserved:
            raise ValidationError({"stock": "Остаток не может быть меньше резерва."})

    def __str__(self):
        return f"{self.sku} · {self.size} · {self.color}"


class ImportSettings(models.Model):
    def clean(self):
        from django.core.exceptions import ValidationError

        allowed = {
            "sku",
            "name",
            "slug",
            "category",
            "description",
            "price",
            "stock",
            "size",
            "color",
            "color_hex",
            "characteristics",
            "image",
            "active",
            "weight",
        }
        if not isinstance(self.column_map, dict) or any(
            k not in allowed or not isinstance(v, str) or not v.strip()
            for k, v in self.column_map.items()
        ):
            raise ValidationError(
                {
                    "column_map": 'Укажите объект соответствия колонок: {"sku": "Артикул"}. Значения должны быть непустыми строками.'
                }
            )
        if not 1 <= self.max_rows <= 5000:
            raise ValidationError({"max_rows": "Допустимо от 1 до 5000 строк."})

    title = models.CharField(
        "Название профиля", max_length=100, default="Стандартный импорт"
    )
    column_map = models.JSONField(
        "Соответствие колонок",
        default=dict,
        blank=True,
        help_text='Необязательно: {"sku": "Артикул", "name": "Наименование"}. Поддерживаются стандартные русские заголовки из шаблона.',
    )
    update_existing = models.BooleanField(
        "Обновлять существующие артикулы", default=True
    )
    max_rows = models.PositiveIntegerField("Максимум строк", default=2000)

    class Meta:
        verbose_name = "Профиль импорта"
        verbose_name_plural = "Настройки импорта"

    def __str__(self):
        return self.title


class ImportJob(models.Model):
    profile = models.ForeignKey(
        ImportSettings, on_delete=models.PROTECT, verbose_name="Профиль"
    )
    file = models.FileField(
        "Таблица Excel или CSV",
        upload_to="imports/",
        storage=PrivateImportStorage(),
        help_text="До 15 МБ. Одна строка = один артикул/размер/цвет. Фото: встроенное в Excel или имя файла из ZIP.",
    )
    photos = models.FileField(
        "Архив фотографий ZIP",
        upload_to="imports/",
        storage=PrivateImportStorage(),
        blank=True,
        help_text="Необязательно. Имена изображений укажите в колонке Фото.",
    )
    status = models.CharField(
        "Статус",
        max_length=20,
        default="new",
        choices=[
            ("new", "Новый"),
            ("validated", "Проверен"),
            ("applied", "Применён"),
            ("error", "Ошибки"),
        ],
    )
    report = models.TextField("Результат проверки", blank=True)
    created_at = models.DateTimeField("Создан", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Импорт товаров"
        verbose_name_plural = "Импорт Excel и CSV"

    def __str__(self):
        return f"Импорт №{self.pk}"
