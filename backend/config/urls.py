from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from core import api
from catalog import api as catalog_api
from orders import api as orders_api
from integrations import api as integrations_api

admin.site.site_header = "ATELIER NOIR · Управление магазином"
admin.site.site_title = "ATELIER NOIR"
admin.site.index_title = "Каталог, заказы и настройки"
urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/csrf/", api.CsrfView.as_view()),
    path("api/settings/", api.SettingsView.as_view()),
    path("api/catalog/", catalog_api.CatalogView.as_view()),
    path("api/catalog/facets/", catalog_api.FacetsView.as_view()),
    path("api/products/<slug:slug>/", catalog_api.ProductView.as_view()),
    path("api/pages/<slug:slug>/", api.PageView.as_view()),
    path("api/shipping/cities/", integrations_api.CitiesView.as_view()),
    path("api/shipping/points/", integrations_api.PickupView.as_view()),
    path("api/quote/", orders_api.QuoteView.as_view()),
    path("api/orders/", orders_api.CheckoutView.as_view()),
    path("api/orders/<str:token>/", orders_api.OrderView.as_view()),
    path("api/orders/<str:token>/payment/", orders_api.PaymentView.as_view()),
    path(
        "api/orders/<str:token>/local-payment/", orders_api.LocalPaymentView.as_view()
    ),
    path("api/webhooks/yookassa/", orders_api.WebhookView.as_view()),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
