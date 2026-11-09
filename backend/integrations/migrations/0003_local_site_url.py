from django.db import migrations, models


def update_local_url(apps, schema_editor):
    settings = apps.get_model("integrations", "IntegrationSettings")
    settings.objects.filter(site_url="http://127.0.0.1:5177").update(site_url="http://127.0.0.1:5173")


class Migration(migrations.Migration):
    dependencies = [("integrations", "0002_alter_integrationsettings_site_url")]
    operations = [
        migrations.AlterField(model_name="integrationsettings", name="site_url", field=models.URLField(default="http://127.0.0.1:5173", help_text="В production — HTTPS. Адрес возврата после оплаты формируется автоматически.", verbose_name="Адрес витрины")),
        migrations.RunPython(update_local_url, migrations.RunPython.noop),
    ]
