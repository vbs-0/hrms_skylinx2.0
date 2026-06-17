# 🧪 Django Test Suite — Error & Failure Report

**Date:** June 17, 2026  
**Project:** Skylinx HRMS 2.0  
**Command:** `venv/Scripts/python.exe manage.py test --verbosity=2 --no-input`  
**Environment:** Python 3.11, Django 5.2, SQLite in-memory test DB

---

## Summary

| Status | Count | Percentage |
|--------|-------|------------|
| ✅ Passed | 46 | 67.6% |
| ❌ Errors | 11 | 16.2% |
| ⚠️ Failed | 1 | 1.5% |
| ⏭️ Skipped | 10 | 14.7% |
| **Total** | **68** | **100%** |

---

## Root Cause Categories

There are **3 distinct root causes** behind all 12 non-passing tests:

| # | Root Cause | Errors | Failures | Total |
|---|-----------|--------|----------|-------|
| 1 | `dynamic_fields` not in `INSTALLED_APPS` | 1 | 0 | **1** |
| 2 | Sidebar/context-processor crashes in test environment | 8 | 0 | **8** |
| 3 | Notification test API format incompatibilities | 2 | 1 | **3** |

---

## Root Cause 1: `dynamic_fields` Not in `INSTALLED_APPS`

### Error

```
ERROR: dynamic_fields.migrations (unittest.loader._FailedTest.dynamic_fields.migrations)
```

```
ImportError: Failed to import test module: dynamic_fields.migrations
  File "dynamic_fields/migrations/__init__.py", line 1, in <module>
    from dynamic_fields import signals
  File "dynamic_fields/signals.py", line 9, in <module>
    from dynamic_fields.models import DynamicField
  File "dynamic_fields/models.py", line 59, in <module>
    class DynamicField(models.Model):
  ...
RuntimeError: Model class dynamic_fields.models.DynamicField doesn't declare an
explicit app_label and isn't in an application in INSTALLED_APPS.
```

### Affected Files

| File | Line | Issue |
|------|------|-------|
| `dynamic_fields/migrations/__init__.py` | 1 | `from dynamic_fields import signals` — imports signals at migration discovery time |
| `dynamic_fields/signals.py` | 9 | `from dynamic_fields.models import DynamicField` — imports model at module level |
| `dynamic_fields/models.py` | 59 | `class DynamicField(models.Model)` — no `app_label` in `Meta` class |
| `skylinx/settings.py` | — | `dynamic_fields` is **not listed** in `INSTALLED_APPS` |

### Root Cause Chain

1. Django's test runner discovers `dynamic_fields/migrations/` as a potential test module.
2. `dynamic_fields/migrations/__init__.py` eagerly imports `signals` at line 1.
3. `signals.py` imports `DynamicField` from `models.py`.
4. `DynamicField` has no `app_label` in its `Meta` class (unlike `Choice` which does).
5. Django raises `RuntimeError` because the model can't be registered.

### Fix Options

**Option A (Recommended):** Add `'dynamic_fields'` to `INSTALLED_APPS` in `skylinx/settings.py` and add `app_label = 'dynamic_fields'` to `DynamicField.Meta`.

**Option B:** Add `app_label = 'dynamic_fields'` to the `DynamicField.Meta` class in `dynamic_fields/models.py` and remove the eager import from `dynamic_fields/migrations/__init__.py` (move it inside a function or remove it entirely since signals should be imported via `AppConfig.ready()`).

---

## Root Cause 2: Sidebar/Context-Processor Crashes (8 Errors)

### Common Pattern

All 8 errors share the same trigger chain:

1. A test renders a template (via `self.client.get()` or `render()`).
2. The `get_MENUS` context processor (`skylinx/config.py:107`) runs on every template render.
3. `get_MENUS` calls `sidebar(request)` which iterates over all sidebar apps.
4. The sidebar iteration calls accessibility functions that assume a fully authenticated user with an `Employee` record.
5. The test user has no `Employee` object → `RelatedObjectDoesNotExist` or no `session` → `AttributeError`.

### Error Breakdown by Sub-Cause

#### Sub-Cause 2a: `SkylinxUser has no employee_get` (6 errors)

**Trigger:** `project/methods.py` line 86 — `user.employee_get` without a `hasattr` guard.

```python
# project/methods.py, line 86
def any_task_manager(user):
    employee = user.employee_get  # ← Crashes if user has no employee
    ...
```

This is called from `project/sidebar.py:56` via the sidebar accessibility chain:
```
skylinx/config.py:107 → sidebar() → project/sidebar.py:56 → any_task_manager(user) → project/methods.py:86
```

**Affected Tests:**

| Test | File | Line |
|------|------|------|
| `AdminTest.test_list` | `notifications/tests/tests.py` | 810 |
| `NotificationTestPages.test_all_messages_page` | `notifications/tests/tests.py` | 308 |
| `NotificationTestPages.test_unread_messages_pages` | `notifications/tests/tests.py` | 318 |
| `NotificationTestPages.test_delete_messages_pages` | `notifications/tests/tests.py` | 407 |
| `NotificationTestPages.test_next_pages` | `notifications/tests/tests.py` | 362 |
| `NotificationTestPages.test_soft_delete_messages_manager` | `notifications/tests/tests.py` | 433 |

**Full Traceback (representative):**
```
File "skylinx/config.py", line 107, in get_MENUS
    sidebar(request)
File "skylinx/config.py", line 62, in sidebar
    or accessibility(
File "project/sidebar.py", line 56, in menu_accessibilty
    or any_task_manager(user)
File "project/methods.py", line 86, in any_task_manager
    employee = user.employee_get
  File "django/db/models/fields/related_descriptors.py", line 531, in __get__
    raise self.RelatedObjectDoesNotExist(
skylinx_auth.models.SkylinxUser.employee_get.RelatedObjectDoesNotExist:
    SkylinxUser has no employee_get.
```

#### Sub-Cause 2b: `'WSGIRequest' object has no attribute 'session'` (1 error)

**Trigger:** `employee/sidebar.py` line 122 — `request.session.session_key` without a `hasattr` guard on `session`.

```python
# employee/sidebar.py, line 122
def employee_accessibility(request, submenu, user_perms, *args, **kwargs):
    cache_key = request.session.session_key + "accessibility_filter"  # ← Crashes
    ...
```

**Affected Test:**

| Test | File | Line |
|------|------|------|
| `NotificationTestPages.test_live_update_tags` | `notifications/tests/tests.py` | 675 |

**Full Traceback:**
```
File "skylinx/config.py", line 107, in get_MENUS
    sidebar(request)
File "skylinx/config.py", line 84, in sidebar
    if not accessibility or accessibility(
File "employee/sidebar.py", line 122, in employee_accessibility
    cache_key = request.session.session_key + "accessibility_filter"
AttributeError: 'WSGIRequest' object has no attribute 'session'
```

#### Sub-Cause 2c: `PayrollSettings.company_id` assignment error (1 error)

**Trigger:** `payroll/context_processors.py` line 19 — tries to assign a string `"all"` to a ForeignKey field.

```python
# payroll/context_processors.py, line 19
def default_currency(request):
    if models.PayrollSettings.objects.first() is None:
        settings = models.PayrollSettings()
        settings.company_id = getattr(request, "selected_company_instance", None)
        # ^^ When request.selected_company_instance is the string "all", this crashes
```

**Affected Test:**

| Test | File | Line |
|------|------|------|
| `AdminTest.test_list` | `notifications/tests/tests.py` | 810 |

**Full Traceback:**
```
File "payroll/context_processors.py", line 19, in default_currency
    settings.company_id = getattr(request, "selected_company_instance", None)
  File "django/db/models/fields/related_descriptors.py", line 288, in __set__
    raise ValueError(
ValueError: Cannot assign "'all'": "PayrollSettings.company_id" must be a "Company" instance.
```

### Fix Options

**Option A (Recommended):** Make `get_MENUS` / `sidebar()` fail gracefully when called in test context:

```python
# skylinx/config.py — in sidebar()
def sidebar(request):
    try:
        if not request.user.is_anonymous:
            ...
    except Exception:
        pass  # Silently skip sidebar build in test/non-session contexts
```

**Option B:** Guard individual problematic calls:

| File | Line | Fix |
|------|------|-----|
| `project/methods.py:86` | `any_task_manager()` | Add `employee = getattr(user, 'employee_get', None); if employee is None: return False` |
| `project/methods.py:92` | `any_task_member()` | Same guard |
| `employee/sidebar.py:122` | `employee_accessibility()` | Add `if not hasattr(request, 'session') or not request.session: return False` |
| `payroll/context_processors.py:19` | `default_currency()` | Check `isinstance(company, Company)` before assignment, or use `try/except` |

---

## Root Cause 3: Notification Test API Format Incompatibilities (3 Tests)

These tests are from `django-notifications-hq`'s original test suite. The Skylinx customizations to the notification views and settings have changed the response format.

### Error 3a: `NotificationManagersTest.test_mark_all_deleted_manager_without_soft_delete` (FAIL)

```python
# notifications/tests/tests.py, line 247
@override_settings(NOTIFICATIONS_SOFT_DELETE=False)
def test_mark_all_deleted_manager_without_soft_delete(self):
    self.assertRaises(ImproperlyConfigured, Notification.objects.active)
    # ↑ Expected ImproperlyConfigured to be raised, but it wasn't
```

**Issue:** The test expects `Notification.objects.active()` to raise `ImproperlyConfigured` when `NOTIFICATIONS_SOFT_DELETE=False`. However, `notifications/settings.py` uses `DJANGO_NOTIFICATIONS_CONFIG={"SOFT_DELETE": False}` (nested dict), while this test uses the flat `NOTIFICATIONS_SOFT_DELETE=False` setting. The Skylinx notification manager likely reads from the nested config, so the flat setting is ignored and `active()` works fine.

**Fix:** Update the test to use the Skylinx-style config:
```python
@override_settings(DJANGO_NOTIFICATIONS_CONFIG={"SOFT_DELETE": False})
```
Or update the notification manager to respect both config styles.

### Error 3b: `NotificationTestExtraData.test_extra_data` (ERROR)

```python
# notifications/tests/tests.py, line 741
def test_extra_data(self):
    ...
    data["unread_list"][0]["data"]["url"]
    # ↑ IndexError: list index out of range — unread_list is empty
```

**Issue:** The test sends a notification with `extra_data` (`url`, `other_content` kwargs) and expects to read it back from `live_unread_notification_list`. The Skylinx notification views appear to filter or strip extra data, resulting in an empty `unread_list` or missing `data` field.

**Fix:** Check if the Skylinx notification views (`notifications/views.py`) override the default `live_unread_notification_list` view and filter out extra data. Update the view to preserve extra data, or update the test to match the current behavior.

### Error 3c: `NotificationTestPages.test_unread_all_objects` (ERROR)

```python
# notifications/tests/tests.py, line 661
def test_unread_all_objects(self):
    ...
    notification["action_object_url"]
    # ↑ KeyError: 'action_object_url'
```

**Issue:** The test expects the notification API response to include `action_object_url`, `target_url`, and `actor_url` keys. The Skylinx notification views don't include these URL fields in their serialized output.

**Fix:** Check `notifications/views.py` — the `live_unread_notification_list` view likely serializes notifications without the URL fields. Add them back, or update the test to match the current response schema.

---

## Skipped Tests (10)

All 10 skipped tests are from `notifications/tests/sample_notifications/tests.py` and are skipped with the message:

```
'Running tests on standard django-notifications models'
```

These are part of the `django-notifications-hq` upstream test suite and are intentionally skipped when running against the custom Skylinx notification models. **No action needed.**

---

## Passing Tests (46)

### `leave` app — 28/28 ✅

| Test Class | Tests |
|---|---|
| `PaymentTypeChoicesTest` | 1 |
| `LeaveTypeGetPaymentPercentageTest` | 6 |
| `LeaveTypePaymentTypeDisplayTest` | 3 |
| `LeaveTypeConditionModelTest` | 4 |
| `GenderConditionTest` | 5 |
| `MaritalStatusConditionTest` | 2 |
| `MultipleConditionsTest` | 2 |
| `NoConditionsTest` | 1 |
| `OncePerEmploymentConditionTest` | 2 |

### `notifications` app — 18/28 ✅

| Test Class | Tests |
|---|---|
| `NotificationTest` | 4 |
| `NotificationManagersTest` | 7 of 8 |
| `NotificationTestPages` | 5 of 13 |
| `TagTest` | 1 |

---

## Recommended Fix Priority

| Priority | Issue | Effort | Impact |
|----------|-------|--------|--------|
| 🔴 P0 | Guard `user.employee_get` in `project/methods.py` | 5 min | Fixes 6 test errors |
| 🔴 P0 | Add `app_label` to `DynamicField.Meta` + clean up `migrations/__init__.py` | 10 min | Fixes 1 test error |
| 🟡 P1 | Guard `request.session` in `employee/sidebar.py:122` | 2 min | Fixes 1 test error |
| 🟡 P1 | Fix `payroll/context_processors.py` company_id assignment | 5 min | Fixes 1 test error |
| 🟡 P1 | Fix `SOFT_DELETE` config mismatch in notification test | 5 min | Fixes 1 test failure |
| 🟢 P2 | Update notification tests for Skylinx API format | 30 min | Fixes 2 test errors |
| ⚪ P3 | Add tests for remaining ~30 apps with zero coverage | Days | Coverage gap |

---

## Quick-Fix Checklist

- [ ] `project/methods.py:86` — Add `getattr(user, 'employee_get', None)` guard in `any_task_manager()`
- [ ] `project/methods.py:92` — Same guard in `any_task_member()`
- [ ] `employee/sidebar.py:122` — Check `hasattr(request, 'session')` before accessing `session_key`
- [ ] `payroll/context_processors.py:19` — Validate `company_id` is a `Company` instance before assignment
- [ ] `dynamic_fields/models.py:67` — Add `app_label = 'dynamic_fields'` to `DynamicField.Meta`
- [ ] `dynamic_fields/migrations/__init__.py:1` — Remove or defer eager signal import
- [ ] `notifications/tests/tests.py:247` — Update `@override_settings` to use `DJANGO_NOTIFICATIONS_CONFIG`
- [ ] `notifications/tests/tests.py:661,741` — Update assertions for Skylinx notification API format
