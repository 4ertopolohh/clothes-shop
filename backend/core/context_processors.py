from django.conf import settings


def admin_mode(request):
    if not request.path.startswith("/admin/"):
        return {}
    from .models import StoreSettings

    return {
        "local_test_mode": settings.LOCAL_DEVELOPMENT
        and StoreSettings.get().local_test_mode
    }
