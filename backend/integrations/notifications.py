import httpx
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string
from core.models import StoreSettings
from orders.models import Order
from .models import IntegrationSettings, Notification, OperationLog
from .providers import local_mode, ProviderError
from .secrets import decrypt


def deliver(notification):
    c = IntegrationSettings.get()
    if notification.status in ("sent", "simulated"):
        return
    try:
        mock = local_mode()
        if not mock:
            if notification.audience == "telegram":
                if (
                    not c.telegram_enabled
                    or not c.telegram_secret_encrypted
                    or not c.telegram_chat_id
                ):
                    raise ProviderError("Заполните настройки Telegram в админке.")
                result = httpx.post(
                    "https://api.telegram.org/bot"
                    + decrypt(c.telegram_secret_encrypted)
                    + "/sendMessage",
                    json={
                        "chat_id": c.telegram_chat_id,
                        "text": notification.text[:4000],
                    },
                    timeout=10,
                )
                result.raise_for_status()
                if not result.json().get("ok"):
                    raise ProviderError("Telegram не принял сообщение.")
            else:
                if not c.smtp_enabled or not c.smtp_host:
                    raise ProviderError("Заполните настройки SMTP в админке.")
                connection = get_connection(
                    host=c.smtp_host,
                    port=c.smtp_port,
                    username=c.smtp_user,
                    password=decrypt(c.smtp_secret_encrypted),
                    use_tls=c.smtp_security == "tls",
                    use_ssl=c.smtp_security == "ssl",
                    timeout=10,
                )
                mail = EmailMultiAlternatives(
                    notification.subject,
                    notification.text,
                    c.from_email,
                    [notification.recipient],
                    connection=connection,
                )
                mail.attach_alternative(notification.html, "text/html")
                mail.send(fail_silently=False)
        notification.status = "simulated" if mock else "sent"
        notification.error = ""
        OperationLog.objects.create(
            provider="telegram" if notification.audience == "telegram" else "email",
            operation=notification.event,
            reference=notification.order.number,
            mock=mock,
            message="Уведомление обработано.",
        )
    except Exception:
        notification.status = "failed"
        notification.error = (
            "Не удалось отправить. Проверьте настройки и повторите из админки."
        )
    notification.save(update_fields=["status", "error"])


def queue_notifications(order_id, event):
    order = Order.objects.prefetch_related("items").get(pk=order_id)
    store = StoreSettings.get()
    c = IntegrationSettings.get()
    for audience, recipient in [
        ("customer", order.email),
        ("store", c.admin_email),
        ("telegram", c.telegram_chat_id or "local-admin"),
    ]:
        subject = f"{'Заказ оформлен' if event == 'created' else 'Оплата получена'} · {order.number} · {store.brand}"
        html = render_to_string(
            "emails/order.html",
            {
                "order": order,
                "store": store,
                "event": event,
                "audience": audience,
                "order_url": c.site_url.rstrip("/") + "/order/" + order.token,
            },
        )
        text = render_to_string(
            "emails/order.txt",
            {
                "order": order,
                "store": store,
                "event": event,
                "audience": audience,
                "order_url": c.site_url.rstrip("/") + "/order/" + order.token,
            },
        )
        notification, _ = Notification.objects.get_or_create(
            order=order,
            event=event,
            audience=audience,
            defaults={
                "recipient": recipient,
                "subject": subject,
                "html": html,
                "text": text,
            },
        )
        deliver(notification)
