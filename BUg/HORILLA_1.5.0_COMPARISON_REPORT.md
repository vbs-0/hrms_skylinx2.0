# Horilla HR Comparison Report: `v2.0.0-beta.1` → `1.5.0`

## Summary

This report compares the external Horilla HR release path from `v2.0.0-beta.1` to `1.5.0` against our current `hrms_skylinx2.0` codebase.

- External compare repo: `https://github.com/horilla/horilla-hr/compare/v2.0.0-beta.1...1.5.0`
- Release page: `https://github.com/horilla/horilla-hr/releases/tag/1.5.0`
- External diff includes: `242` commits, `300` changed files.
- External release note: "Includes major security patches for CVE's."

Our code is based on the Horilla `2.0.0-beta.1` lineage and has diverged with custom work. This report identifies major fix categories, which areas appear covered by our code, and which risk areas may still need review.

---

## Methodology

1. Fetched the external release metadata and comparison summary via GitHub API.
2. Selected key fix commits from the compare diff by category.
3. Searched our repository for corresponding modules, functions, and patterns.
4. Identified overlaps and potential gaps based on code evidence.

---

## Key external fix areas

### 1. Payroll

- [04dd5cc] `https://github.com/horilla/horilla-hr/commit/04dd5cc` — `[FIX] PAYROLL: #769`
- [395d7f] `https://github.com/horilla/horilla-hr/commit/395d7fa` — `[FIX] PAYROLL: Isolate allowances and deductions per company to prevent cross-company visibility and edits`
- [1607a1f] `https://github.com/horilla/horilla-hr/commit/1607a1f` — `[FIX] PAYROLL: Fixed reimbursements for leave type options loading`
- [8406067] `https://github.com/horilla/horilla-hr/commit/8406067` — `[UPDT] PAYROLL: Avoid duplicate allowances by checking existence before appending in def allowances_deductions_tab(request, emp_id): function`

### 2. Horilla views / pagination / HTMX

- [5223c63] `https://github.com/horilla/horilla-hr/commit/5223c63` — `[FIX] HORILLA_VIEWS: Ensure consistent pagination by ordering queryset in record_queryset_paginator()`
- [72888d6] `https://github.com/horilla/horilla-hr/commit/72888d6` — `[UPDT] HORILLA_VIEWS: Updated HorillaFormView class get_context_data function by adding hx_target in context`
- [232e469] `https://github.com/horilla/horilla-hr/commit/232e469` — `[UPDT] HORILLA: Add HX-Refresh response handling to login_required for HTMX requests`
- [b950991] `https://github.com/horilla/horilla-hr/commit/b950991` — `fix: remove redundant AccessibilityMiddleware entry from middleware list (#781)`

### 3. Attendance

- [96263dd] `https://github.com/horilla/horilla-hr/commit/96263dd` — `[UPDT] ATTENDANCE: Consolidate checkbox handlers into reusable functions for attendance tables`
- [8a74adc] `https://github.com/horilla/horilla-hr/commit/8a74adc` — `[FIX] ATTENDANCE: Fixed work record export issue`
- [fdfb049] `https://github.com/horilla/horilla-hr/commit/fdfb049` — `[UPDT] ATTENDANCE: Support CSV format for attendance import alongside Excel`

### 4. Leave

- [193df46] `https://github.com/horilla/horilla-hr/commit/193df46` — `[UPDT] LEAVE: Improve performance of employee_available_leave_count view`
- [0da929f] `https://github.com/horilla/horilla-hr/commit/0da929f` — `[FIX] LEAVE: Prevent duplicate compensatory leave types by excluding current instance in model validation`
- [1278d4b] `https://github.com/horilla/horilla-hr/commit/1278d4b` — `[FIX] LEAVE: Leave Request Email Issue In Outlook`

### 5. Recruitment

- [6ea5e96] `https://github.com/horilla/horilla-hr/commit/6ea5e96` — `[FIX] RECRUITMENT: Fixed unique constraint issue in candidate_conversion function`
- [ecef5ae] `https://github.com/horilla/horilla-hr/commit/ecef5ae` — `[FIX] RECRUITMENT: #787`
- [2af0810] `https://github.com/horilla/horilla-hr/commit/2af0810` — `[FIX] RECRUITMENT: #803`

### 6. Automations / MailAutomation

- [97a5b4e] `https://github.com/horilla/horilla-hr/commit/97a5b4e` — `[UPDT] HORILLA_AUTOMATIONS: Updated MailAutomation model method_title field max_length attribute`
- [72fd43f] `https://github.com/horilla/horilla-hr/commit/72fd43f` — `[UPDT] HORILLA_AUTOMATIONS: #720`

### 7. Base / Announcement / Notifications

- [e4580d2] `https://github.com/horilla/horilla-hr/commit/e4580d2` — `[FIX] BASE: Resolved issue in announcement, employees didn't get the notification`
- [a4d062c] `https://github.com/horilla/horilla-hr/commit/a4d062c` — `[FIX] BASE: Restrict Group users_count to selected company context`

### 8. Geofencing

- [3e51b3e] `https://github.com/horilla/horilla-hr/commit/3e51b3e` — `[FIX] GEOFENCING: Geofence setupcheck api`
- [b571f7e] `https://github.com/horilla/horilla-hr/commit/b571f7e` — `[FIX] GEOFENCING: Geofence setupcheck api`

### 9. Backup / Google authentication

- [eb5a3bf] `https://github.com/horilla/horilla-hr/commit/eb5a3bf` — `[FIX] HORILLA_BACKUP: Google service file authentication issue`

### 10. Static / Select2 / UI

- [67bce92] `https://github.com/horilla/horilla-hr/commit/67bce92` — `[FIX] STATIC: Prevent duplicate Select2 containers by destroying existing instances before reinitialization`

---

## Our code coverage and matched areas

### Modules with strong overlap

- `skylinx/group_by.py` — contains `record_queryset_paginator()` with safe ordering logic.
- `skylinx/decorators.py` — contains `login_required` HTMX `HX-Refresh` logic.
- `skylinx_automations/models.py` and `skylinx_automations/signals.py` — contain `MailAutomation`, `method_title`, and email/notification handling.
- `leave/views.py` — contains `employee_available_leave_count()`.
- `recruitment/views/views.py` — contains `candidate_conversion()`.
- `employee/views.py` and `payroll/views/component_views.py` — contain `allowances_deductions_tab()` variants.
- `base/methods.py` — contains `Group.users_count` restricted to company context.
- `geofencing/views.py` — implements geofencing employee location checks.
- `skylinx_theme` and `static/htmx` — include HTMX and notification UI behavior.

### Evidence of matching fixes

- `record_queryset_paginator` already orders by `created_at` or `id` when no ordering is present.
- `HX-Refresh` is already returned from `login_required` and several view handlers.
- `MailAutomation` currently has `method_title` and fallback email handling code.
- `Group.users_count` is already company-scoped in `base/methods.py`.

---

## Potential issues and gaps in our code

### 1. Payroll allowance/deduction ID bug

In `payroll/views/component_views.py`, the current `allowances_deductions_tab()` implementation sets both:

- `allowance_ids = json.dumps([instance.id for instance in employee_deductions])`
- `deduction_ids = json.dumps([instance.id for instance in employee_deductions])`

This is almost certainly wrong and should be reviewed. The external fix specifically targeted duplicate allowance handling and likely expected separate allowance/deduction ID sets.

### 2. Geofencing setup-check gap

Our `geofencing/views.py` implements location check APIs, but there is no clear `setupcheck` API endpoint or request name matching the external fix. That suggests our geofence validation flow may differ or may still miss the external fix.

### 3. Leave performance fix

The external `193df46` fix is specifically about performance in `employee_available_leave_count`. Our view is present and functional, but it may still benefit from the same optimization.

### 4. Candidate conversion unique constraint

We have `candidate_conversion()` in `recruitment/views/views.py`. The external fix was for a unique constraint issue, and our implementation currently catches `IntegrityError`, but the underlying model behavior should be audited.

### 5. Announcement notification reliability

The external fix in `base` addressed announcement delivery and employee notification. Our repository contains announcement and notification paths, but the exact same scenario is not proven resolved without a targeted audit.

### 6. Select2 / HTMX duplicate handling

The compare shows multiple static/UI changes to prevent duplicate `Select2` initialization and manage HTMX updates. Our search did not uncover a direct matching patch, so this area should be reviewed, especially in JS init code and dynamically loaded forms.

### 7. Backup Google auth and automation robustness

- `HORILLA_BACKUP` fix for Google service authentication appears externally fixed.
- Our `skylinx_backup` code should be reviewed for the same compatibility.
- `HORILLA_AUTOMATIONS` fix around `from_email` and `reply_to` fallback should be verified even though relevant code exists.

### 8. General divergence and custom behavior

Our repository has customizations and renamed modules (`skylinx_...`, `hrms_skylinx2.0`), so not every external commit can be matched directly. The compare history indicates there are many changed files in `horilla_api`, `employee`, `load_data`, `base`, `leave`, `payroll`, `biometric`, `project`, and `pms`, which may hide additional mismatches.

---

## Recommended next actions

1. Review `payroll/views/component_views.py` and fix the allowance/deduction ID generation bug.
2. Audit `geofencing` API endpoints against the external `setupcheck` semantics.
3. Benchmark and potentially optimize `leave/views.py` `employee_available_leave_count()`.
4. Audit `recruitment/views/views.py` `candidate_conversion()` against duplicate employee creation and unique constraint handling.
5. Verify announcement notification delivery logic in `base/announcement.py` and related templates.
6. Review UI/JS around `Select2` and HTMX reinitialization to ensure duplicate container handling is fixed.
7. Verify backup auth behavior in `skylinx_backup` against external Google service file fixes.

---

## References

- External release: `https://github.com/horilla/horilla-hr/releases/tag/1.5.0`
- External compare: `https://github.com/horilla/horilla-hr/compare/v2.0.0-beta.1...1.5.0`

### Primary commit references

- `https://github.com/horilla/horilla-hr/commit/04dd5cc`
- `https://github.com/horilla/horilla-hr/commit/395d7fa`
- `https://github.com/horilla/horilla-hr/commit/1607a1f`
- `https://github.com/horilla/horilla-hr/commit/8406067`
- `https://github.com/horilla/horilla-hr/commit/5223c63`
- `https://github.com/horilla/horilla-hr/commit/72888d6`
- `https://github.com/horilla/horilla-hr/commit/232e469`
- `https://github.com/horilla/horilla-hr/commit/b950991`
- `https://github.com/horilla/horilla-hr/commit/96263dd`
- `https://github.com/horilla/horilla-hr/commit/8a74adc`
- `https://github.com/horilla/horilla-hr/commit/fdfb049`
- `https://github.com/horilla/horilla-hr/commit/193df46`
- `https://github.com/horilla/horilla-hr/commit/0da929f`
- `https://github.com/horilla/horilla-hr/commit/1278d4b`
- `https://github.com/horilla/horilla-hr/commit/6ea5e96`
- `https://github.com/horilla/horilla-hr/commit/ecef5ae`
- `https://github.com/horilla/horilla-hr/commit/2af0810`
- `https://github.com/horilla/horilla-hr/commit/97a5b4e`
- `https://github.com/horilla/horilla-hr/commit/72fd43f`
- `https://github.com/horilla/horilla-hr/commit/e4580d2`
- `https://github.com/horilla/horilla-hr/commit/a4d062c`
- `https://github.com/horilla/horilla-hr/commit/3e51b3e`
- `https://github.com/horilla/horilla-hr/commit/b571f7e`
- `https://github.com/horilla/horilla-hr/commit/eb5a3bf`
- `https://github.com/horilla/horilla-hr/commit/67bce92`

---

## Notes

This report is based on the external compare summary from GitHub and the present local repository search. It is not a full patch-level diff, but it highlights the strongest likely overlaps and risk areas.
