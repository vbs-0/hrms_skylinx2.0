"""
Signals for the skylinx_theme app
"""

# themes/signals.py
# Define your skylinx_theme signals here
from django.db.models.signals import post_migrate
from django.db.utils import OperationalError, ProgrammingError
from django.dispatch import receiver

from .models import THEMES_DATA, SkylinxColorTheme


@receiver(post_migrate)
def create_default_themes(sender, **kwargs):
    """
    Create default color skylinx_theme after migration
    """
    # Only run for the skylinx_theme app
    if sender.name != "skylinx_theme":
        return

    # Check if skylinx_theme already exist
    try:
        # Table may not exist yet in some migration orders
        if SkylinxColorTheme.objects.exists():
            return
    except (OperationalError, ProgrammingError):
        # Table not created yet — skip silently
        return

    print("Creating default color themes...")
    created_count = 0

    for theme_data in THEMES_DATA:
        try:
            theme, created = SkylinxColorTheme.objects.get_or_create(
                name=theme_data["name"], defaults=theme_data
            )
            if created:
                created_count += 1
                print(f"[OK] Created theme: {theme.name}")
            else:
                print(f"- Theme already exists: {theme.name}")
        except Exception as e:
            print(f"[ERROR] Error creating theme {theme_data['name']}: {str(e)}")

    print(f"\nSuccessfully created {created_count} themes.")
