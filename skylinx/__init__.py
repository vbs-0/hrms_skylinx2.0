"""
init.py
"""

import sys

# Gate all in-process APScheduler jobs behind RUN_SCHEDULERS (off in web workers,
# on only in the dedicated `manage.py run_schedulers` process). Must run before
# any app's scheduler module imports.
try:
    from skylinx.scheduler_guard import install as _install_scheduler_guard

    _install_scheduler_guard()
except ImportError:
    pass

# Patch makemigrations and migrate to use SkylinxAutodetector.
#
# Django stores the autodetector as a class attribute on each command
# (`autodetector = MigrationAutodetector`), so we patch the class attribute
# directly — patching the module-level name has no effect.
#
# Django 6.x requires both commands to share the same autodetector class
# (system check commands.E001), so we always patch both.
try:
    from django.core.management.commands.makemigrations import Command as _MM
    from django.core.management.commands.migrate import Command as _Migrate

    from skylinx.inherit.autodetect import SkylinxAutodetector

    _MM.autodetector = SkylinxAutodetector
    _Migrate.autodetector = SkylinxAutodetector
except ImportError:
    pass
