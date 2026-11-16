from django.db import migrations


APPLICATION_TABLES = (
    "accounts_user",
    "parking_vehicle",
    "parking_parkingfacility",
    "parking_parkinglocation",
    "parking_parkingsession",
    "parking_parkingreference",
    "parking_parkingtimer",
)


def enable_application_table_rls(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    quote_name = schema_editor.quote_name
    with schema_editor.connection.cursor() as cursor:
        for table_name in APPLICATION_TABLES:
            cursor.execute(
                f"ALTER TABLE {quote_name(table_name)} ENABLE ROW LEVEL SECURITY"
            )


def disable_application_table_rls(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    quote_name = schema_editor.quote_name
    with schema_editor.connection.cursor() as cursor:
        for table_name in reversed(APPLICATION_TABLES):
            cursor.execute(
                f"ALTER TABLE {quote_name(table_name)} DISABLE ROW LEVEL SECURITY"
            )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        ("parking", "0002_parkingsession_unique_active_session_per_vehicle"),
    ]

    operations = [
        migrations.RunPython(
            enable_application_table_rls,
            reverse_code=disable_application_table_rls,
        ),
    ]
