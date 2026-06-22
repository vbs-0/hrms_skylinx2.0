"""
Single switch for every in-process APScheduler job.

Each app starts its own BackgroundScheduler at import time. Run inside every
gunicorn worker, those jobs hammered the DB on short intervals and slowed the
whole app. This patches BackgroundScheduler.start() to a no-op unless the env
var RUN_SCHEDULERS is truthy — so web workers never run jobs. Only the dedicated
`manage.py run_schedulers` process (started with RUN_SCHEDULERS=1) runs them.

Imported from skylinx/__init__.py so the patch is in place before any app's
scheduler module loads.

ponytail: one monkeypatch gates all ~10 schedulers, vs. editing each one's
start guard. Set RUN_SCHEDULERS=1 in the dedicated scheduler service (and in
local dev if you want jobs to fire under runserver).
"""

import os


def _enabled():
    return os.environ.get("RUN_SCHEDULERS", "").lower() in ("1", "true", "yes", "on")


def install():
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except ImportError:
        return

    if getattr(BackgroundScheduler, "_skylinx_gated", False):
        return  # idempotent

    real_start = BackgroundScheduler.start

    def gated_start(self, *args, **kwargs):
        if _enabled():
            return real_start(self, *args, **kwargs)
        return None  # no-op in web workers

    BackgroundScheduler.start = gated_start
    BackgroundScheduler._skylinx_gated = True
