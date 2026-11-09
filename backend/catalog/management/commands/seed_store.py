import json
from io import BytesIO
from PIL import Image
import secrets
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import httpx
from django.core.management.base import BaseCommand, CommandError
from django.core.files.base import ContentFile
from django.conf import settings
from django.contrib.auth import get_user_model
from catalog.models import Category, Product, ProductImage, Variant, ImportSettings
from catalog.importing import normalize_image, template_bytes
from core.models import StoreSettings, Page
from integrations.models import IntegrationSettings
from orders.models import PromoCode

SLUGS = [
    "palto-liniya",
    "zhaket-kontur",
    "kurtka-ten",
    "longsliv-takt",
    "top-pauza",
    "bryuki-obyom",
    "rubashka-pole",
    "pidzhak-arhiv",
    "futbolka-baza",
    "plate-tishina",
    "bomber-oblako",
    "bryuki-vektor",
    "tunika-sloy",
    "rubashka-svet",
    "top-ritm",
    "palto-plastika",
]
COLORS = {"Чёрный": "#171717", "Графит": "#57585a", "Молочный": "#e3dfd3"}


class Command(BaseCommand):
    help = "Идемпотентно подготовить каталог, локальные фото, страницы, профиль импорта и локального администратора."

    def handle(self, *args, **options):
        rows = json.loads(
            (Path(__file__).resolve().parents[2] / "seed.json").read_text(
                encoding="utf-8"
            )
        )
        cache = settings.MEDIA_ROOT / "seed"
        cache.mkdir(parents=True, exist_ok=True)

        def photo(row):
            target = cache / (row[3] + ".webp")
            if target.exists():
                return target
            for attempt in range(3):
                try:
                    response = httpx.get(
                        "https://images.unsplash.com/" + row[3],
                        params={"auto": "format", "fit": "crop", "w": 1200, "q": 85},
                        timeout=25,
                        follow_redirects=False,
                    )
                    response.raise_for_status()
                    target.write_bytes(normalize_image(response.content))
                    return target
                except Exception:
                    if attempt == 2:
                        return None
                    time.sleep(0.5)

        with ThreadPoolExecutor(max_workers=5) as pool:
            photos = list(pool.map(photo, rows))
        fallback = next((p for p in photos if p), None)
        if not fallback:
            raise CommandError(
                "Не удалось загрузить изображения. Повторите seed_store при доступе к Unsplash."
            )
        for index, row in enumerate(rows):
            name, category, price, _, colors, sizes, badge, description = row
            category_slug = {
                "Верхняя одежда": "outerwear",
                "Трикотаж": "knitwear",
                "Брюки": "trousers",
                "Рубашки": "shirts",
                "Футболки": "t-shirts",
                "Платья": "dresses",
            }[category]
            cat, _ = Category.objects.get_or_create(
                slug=category_slug, defaults={"name": category, "position": index}
            )
            product, created = Product.objects.get_or_create(
                slug=SLUGS[index],
                defaults={
                    "name": name,
                    "category": cat,
                    "description": description,
                    "badge": badge,
                    "is_new": bool(badge),
                    "position": index,
                    "characteristics": {
                        "Посадка": "Свободная",
                        "Сезон": "Всесезонная коллекция",
                        "Уход": "Следуйте инструкции на ярлыке изделия",
                    },
                },
            )
            if not product.images.exists():
                chosen = photos[index] or fallback
                img = ProductImage(product=product, alt=name)
                img.image.save(SLUGS[index] + ".webp", ContentFile(chosen.read_bytes()))
                if not photos[index]:
                    self.stdout.write(
                        f"{name}: исходное фото недоступно, использовано другое фото коллекции."
                    )
            # Кадрирование исходного снимка только для новых демонстрационных товаров.
            if created and index < 2 and photos[index]:
                with Image.open(photos[index]) as original:
                    width, height = original.size
                    cropped = original.crop((int(width * .12), int(height * .08), int(width * .88), int(height * .82)))
                    output = BytesIO()
                    cropped.save(output, format="WEBP", quality=85)
                detail = ProductImage(product=product, alt=f"{name} — фрагмент фотографии", position=1)
                detail.image.save(SLUGS[index] + "-detail.webp", ContentFile(output.getvalue()))
            for color_index, color in enumerate(colors.split(",")):
                for size in sizes.split(","):
                    Variant.objects.get_or_create(
                        sku=f"AN-{index + 1:03d}-{size}-{color_index + 1}",
                        defaults={
                            "product": product,
                            "size": size,
                            "color": color,
                            "color_hex": COLORS[color],
                            "price": price,
                            "stock": 8,
                        },
                    )
        store = StoreSettings.get()
        if not store.hero_image:
            store.hero_image.save(
                "hero.webp",
                ContentFile((photos[0] or fallback).read_bytes()),
                save=False,
            )
        if not store.about_image:
            store.about_image.save(
                "about.webp",
                ContentFile((photos[1] or fallback).read_bytes()),
                save=False,
            )
        store.save()
        IntegrationSettings.get()
        ImportSettings.objects.get_or_create(title="Стандартный импорт")
        PromoCode.objects.get_or_create(code="FORM10", defaults={"percent": 10})
        pages = {
            "delivery": (
                "Доставка и оплата",
                "Доставка СДЭК в пункт выдачи или курьером. Оплата онлайн.",
                "Выберите вещи, размер и цвет. Добавьте их в корзину и перейдите к оформлению — регистрация не нужна.\n\nДоставка СДЭК доступна в пункт выдачи и курьером. Введите название города и выберите его из списка. Для самовывоза выберите удобный пункт: его адрес и часы работы появятся рядом. Для курьерской доставки укажите улицу, дом и квартиру.\n\nСтоимость и ориентировочный срок доставки рассчитываются при оформлении. До подтверждения заказа вы увидите полную сумму с учётом скидки и доставки.\n\nПосле оформления вещи резервируются на ограниченное время. Перейдите к оплате со страницы заказа. Подтверждение оформления и оплаты отправляется на вашу электронную почту. Сохраните письмо и секретную ссылку на заказ.\n\nЕсли возник вопрос о доставке или заказе, напишите на почту магазина со страницы контактов.",
            ),
            "offer": (
                "Условия покупки",
                "Как оформить и получить заказ ATELIER NOIR.",
                "Перед оформлением проверьте название вещи, цвет, размер и количество. Изображения помогают оценить силуэт; оттенок на экране может зависеть от настроек устройства.\n\nЦена каждого варианта, скидка и стоимость доставки указаны в итогах заказа. Заказ оформляется после проверки доступного количества. Для получения необходимы имя, телефон, email и данные доставки.\n\nНеоплаченные вещи сохраняются в резерве до времени, указанного на странице заказа. Оплата выполняется по ссылке после оформления. Статус оплаты подтверждается сервером магазина.\n\nСохраните номер заказа и письмо с подтверждением. По вопросам покупки свяжитесь с магазином через страницу контактов.",
            ),
            "privacy": (
                "Конфиденциальность",
                "Обработка данных при оформлении заказа.",
                "Для оформления и доставки заказа магазин получает имя, телефон, электронную почту и адрес либо выбранный пункт выдачи. Эти сведения используются для обработки покупки, оплаты, доставки и сообщений о заказе.\n\nПри подключённых сервисах необходимые сведения передаются службе доставки и платёжному провайдеру в объёме, нужном для выполнения заказа. Данные банковской карты не вводятся на витрине и не сохраняются в базе магазина.\n\nКорзина хранится в вашем браузере. Обязательные технические cookies используются для защиты запросов. Регистрация и личный кабинет отсутствуют. Необязательная аналитика не подключена.\n\nДля вопросов об обработке данных и уточнения сведений по заказу используйте контакты магазина.",
            ),
            "returns": (
                "Обмен и возврат",
                "Свяжитесь с магазином по вопросам обмена и возврата.",
                "Если вещь не подошла или возник вопрос к качеству, напишите на электронную почту магазина. Укажите номер заказа, название вещи и причину обращения. При необходимости приложите фотографии.\n\nСохраните вещь, ярлыки и подтверждение покупки. После обращения магазин сообщит порядок передачи товара и дальнейшие шаги.\n\nКонтакты для обращения доступны на странице «Контакты».",
            ),
        }
        for slug, (title, description, body) in pages.items():
            Page.objects.get_or_create(
                slug=slug,
                defaults={"title": title, "description": description, "body": body},
            )
        sample = settings.BASE_DIR / ".local" / "import-template.xlsx"
        sample.parent.mkdir(exist_ok=True)
        sample.write_bytes(template_bytes())
        if (
            settings.LOCAL_DEVELOPMENT
            and not get_user_model().objects.filter(username="admin").exists()
        ):
            password = secrets.token_urlsafe(18)
            get_user_model().objects.create_superuser(
                "admin", "admin@localhost.example", password
            )
            credential = settings.BASE_DIR / ".local" / "admin.txt"
            credential.write_text(
                "Django Admin: http://127.0.0.1:8000/admin/\nЛогин: admin\nПароль: "
                + password
                + "\n",
                encoding="utf-8",
            )
            credential.chmod(0o600)
            self.stdout.write(
                "Локальный администратор создан. Данные входа: backend/.local/admin.txt (вне Git)."
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"Готово: {Product.objects.count()} товаров, {Variant.objects.count()} вариантов. Повторный запуск не затирает данные."
            )
        )
