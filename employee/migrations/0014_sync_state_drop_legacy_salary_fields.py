"""
State-only reconciliation.

Migration 0013 dropped the legacy columns (basic_salary, probation_end,
salary_hour) at the DB level via raw `DROP COLUMN IF EXISTS`, but did NOT
remove them from Django's migration *state*. The model no longer declares
them (they are now @property / replaced by ctc + probation_days +
salary_components), so the autodetector keeps wanting to generate a
RemoveField migration.

This migration removes the fields from STATE ONLY. The columns are already
gone on every database, so we must NOT emit another DROP COLUMN here -- doing
so is exactly what crashed production before ("column does not exist").
SeparateDatabaseAndState with empty database_operations = no SQL run.
"""

from django.db import migrations, models


def state_removes():
    fields = ["basic_salary", "probation_end", "salary_hour"]
    models_ = ["employeeworkinformation", "historicalemployeeworkinformation"]
    return [
        migrations.RemoveField(model_name=m, name=f)
        for m in models_
        for f in fields
    ]


class Migration(migrations.Migration):

    dependencies = [
        ("employee", "0013_probation_days_ctc_breakdown"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=state_removes(),
            database_operations=[],  # columns already dropped by 0013
        ),
    ]
