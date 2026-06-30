"""
init.py
"""

import sys

# reportlab>=4 calls hashlib.md5(usedforsecurity=False), but that kwarg only
# exists on Python 3.9+. The server runs 3.8, so every PDF (payslips, leave
# reports, offer letters) crashes. Strip the kwarg on <3.9.
# ponytail: drop this shim once the server moves to Python 3.9+ or reportlab<4.
if sys.version_info < (3, 9):
    import hashlib as _hashlib

    _orig_md5 = _hashlib.md5

    def _md5_compat(*args, **kwargs):
        kwargs.pop("usedforsecurity", None)
        return _orig_md5(*args, **kwargs)

    _hashlib.md5 = _md5_compat

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
