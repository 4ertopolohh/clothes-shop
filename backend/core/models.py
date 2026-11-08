from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings


class Singleton(models.Model):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        return cls.objects.get_or_create(pk=1)[0]


class StoreSettings(Singleton):
    brand = models.CharField(
        "Название магазина", max_length=100, default="ATELIER NOIR"
    )
    tagline = models.CharField(
        "Подпись логотипа", max_length=120, default="CONTEMPORARY UNIFORM"
    )
    announcement = models.CharField(
        "Сообщение в верхней полосе",
        max_length=200,
        default="Новая коллекция · Доставка по России",
    )
    hero_title = models.CharField(
        "Заголовок первого экрана", max_length=200, default="Искусство\nбыть собой."
    )
    hero_text = models.TextField(
        "Описание первого экрана",
        default="Вещи, в которых важны крой, ощущение ткани и свобода движения. Ничего лишнего.",
    )
    hero_image = models.ImageField("Фото первого экрана", upload_to="site/", blank=True)
    about_title = models.CharField(
        "Заголовок о бренде", max_length=200, default="Меньше шума.\nБольше смысла."
    )
    about_text = models.TextField(
        "О бренде",
        default="Одежда без лишнего декора, в которой качество силуэта говорит громче логотипа. Точные линии, спокойные оттенки и свобода движения.",
    )
    about_image = models.ImageField("Фото о бренде", upload_to="site/", blank=True)
    email = models.EmailField("Публичная почта", default="hello@ateliernoir.example")
    phone = models.CharField("Публичный телефон", max_length=40, blank=True)
    address = models.CharField("Адрес", max_length=250, blank=True)
    legal_details = models.TextField(
        "Реквизиты продавца",
        blank=True,
        help_text="Заполните перед публичным запуском магазина.",
    )
    local_test_mode = models.BooleanField(
        "Локальный тестовый режим",
        default=True,
        help_text="Только для локальной разработки: без переводов денег и внешних уведомлений.",
    )
    reservation_minutes = models.PositiveIntegerField(
        "Резерв заказа, минут", default=30
    )

    class Meta:
        verbose_name = "Настройки магазина"
        verbose_name_plural = "Настройки магазина"

    def clean(self):
        if self.local_test_mode and not settings.LOCAL_DEVELOPMENT:
            raise ValidationError("Локальный режим запрещён в production.")
        if not 5 <= self.reservation_minutes <= 1440:
            raise ValidationError(
                {"reservation_minutes": "Укажите от 5 до 1440 минут."}
            )

    def __str__(self):
        return self.brand


class Page(models.Model):
    slug = models.SlugField("Адрес страницы", unique=True)
    title = models.CharField("Заголовок", max_length=200)
    description = models.CharField("SEO-описание", max_length=300, blank=True)
    body = models.TextField(
        "Текст",
        help_text="Обычный текст. Пустая строка разделяет абзацы; HTML не исполняется.",
    )
    published = models.BooleanField("Опубликована", default=True)
    updated_at = models.DateTimeField("Обновлена", auto_now=True)

    class Meta:
        verbose_name = "Страница"
        verbose_name_plural = "Страницы и документы"

    def __str__(self):
        return self.title
