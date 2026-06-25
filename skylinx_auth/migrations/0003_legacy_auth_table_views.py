from django.db import migrations


def create_legacy_auth_views(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'auth_user') THEN
                    CREATE VIEW auth_user AS
                    SELECT
                        id,
                        password,
                        last_login,
                        is_superuser,
                        username,
                        first_name,
                        last_name,
                        email,
                        is_staff,
                        is_active,
                        date_joined
                    FROM skylinx_auth_skylinxuser;
                END IF;

                IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'auth_user_groups') THEN
                    CREATE VIEW auth_user_groups AS
                    SELECT
                        id,
                        skylinxuser_id AS user_id,
                        group_id
                    FROM skylinx_auth_skylinxuser_groups;
                END IF;

                IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'auth_user_user_permissions') THEN
                    CREATE VIEW auth_user_user_permissions AS
                    SELECT
                        id,
                        skylinxuser_id AS user_id,
                        permission_id
                    FROM skylinx_auth_skylinxuser_user_permissions;
                END IF;
            END $$;
            """
        )


def drop_legacy_auth_views(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_class WHERE relname = 'auth_user_user_permissions' AND relkind = 'v') THEN
                    DROP VIEW auth_user_user_permissions;
                END IF;

                IF EXISTS (SELECT 1 FROM pg_class WHERE relname = 'auth_user_groups' AND relkind = 'v') THEN
                    DROP VIEW auth_user_groups;
                END IF;

                IF EXISTS (SELECT 1 FROM pg_class WHERE relname = 'auth_user' AND relkind = 'v') THEN
                    DROP VIEW auth_user;
                END IF;
            END $$;
            """
        )


class Migration(migrations.Migration):
    dependencies = [
        ("skylinx_auth", "0002_skylinxuser_accepted_terms"),
    ]

    operations = [
        migrations.RunPython(create_legacy_auth_views, drop_legacy_auth_views),
    ]
