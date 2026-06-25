"""
Run all in-process APScheduler jobs in ONE dedicated process.

Schedulers are gated off in the web workers (see skylinx/scheduler_guard.py).
This command is the single place they run. systemd starts it with
RUN_SCHEDULERS=1; the schedulers start during app loading, and this process
just stays alive to keep their background threads running.
"""

import time

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run all background schedulers in a single dedicated process."

    def handle(self, *args, **options):
        import os

        if os.environ.get("RUN_SCHEDULERS", "").lower() not in (
            "1",
            "true",
            "yes",
            "on",
        ):
            self.stderr.write(
                "RUN_SCHEDULERS is not set — schedulers were gated off and will "
                "NOT run. Start with RUN_SCHEDULERS=1."
            )
            return

        self.stdout.write("Schedulers running. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            self.stdout.write("Stopping schedulers.")
