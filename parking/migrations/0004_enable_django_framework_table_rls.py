from django.db import migrations


DJANGO_FRAMEWORK_TABLES = (
    "django_migrations",
    "django_content_type",
    "auth_permission",
    "auth_group",
    "auth_group_permissions",
    "accounts_user_groups",
    "accounts_user_user_permissions",
    "django_admin_log",
    "django_session",
)


def enable_framework_table_rls(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    quote_name = schema_editor.quote_name
    with schema_editor.connection.cursor() as cursor:
        for table_name in DJANGO_FRAMEWORK_TABLES:
            cursor.execute(
                f"ALTER TABLE {quote_name(table_name)} ENABLE ROW LEVEL SECURITY"
            )


def disable_framework_table_rls(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    quote_name = schema_editor.quote_name
    with schema_editor.connection.cursor() as cursor:
        for table_name in reversed(DJANGO_FRAMEWORK_TABLES):
            cursor.execute(
                f"ALTER TABLE {quote_name(table_name)} DISABLE ROW LEVEL SECURITY"
            )


class Migration(migrations.Migration):
    dependencies = [
        ("admin", "0003_logentry_add_action_flag_choices"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("parking", "0003_enable_application_table_rls"),
        ("sessions", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            enable_framework_table_rls,
            reverse_code=disable_framework_table_rls,
        ),
    ]
