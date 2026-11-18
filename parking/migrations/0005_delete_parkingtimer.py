from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("parking", "0004_enable_django_framework_table_rls"),
    ]

    operations = [
        migrations.DeleteModel(
            name="ParkingTimer",
        ),
    ]
