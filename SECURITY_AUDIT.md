# Security & Permission Audit — HRMS

Date: 2026-06-16. Read-only audit. No code was changed.

Access model in this codebase: the correct gate is
`filtersubordinates(request, queryset, perm)` (base/methods.py:297) — returns the
full queryset only if the user holds `perm` (HR/admin), otherwise only their
subordinates (reporting managers), otherwise nothing. Decorators live in
`skylinx/decorators.py`: `login_required`, `permission_required`,
`manager_can_enter`, `owner_can_enter`, `hx_request_required`.

The recurring root cause across the app: **views are gated only at the decorator
level (`@login_required`), with no row-level / object-level authorization.** Any
endpoint that fetches an object by `<int:pk>`/id without an ownership or
`filtersubordinates` check is an IDOR.

---

## CRITICAL

### Settings / deployment (skylinx/settings/base.py)
- **base.py:22** — `DEBUG` defaults to `True` if env var unset → stack traces, settings, SQL leak in prod.
- **base.py:23,33** — `SECRET_KEY` defaults to hardcoded `"django-insecure-default-key"` → forgeable sessions/CSRF/tokens.

### Authentication bypass / privilege escalation
- **employee/views.py:284 `profile_edit_access`** — NO decorator at all (not even login). Any/anonymous user can grant themselves profile-edit/feature access via `emp_id`/`feature` GET params.
- **helpdesk/decorators.py:45 `ticket_owner_can_enter`** — owner check ends with unfiltered `Ticket.objects.filter(assigned_to=...) or Ticket.objects.filter(created_by=...)`, which is truthy if the user owns/was-assigned *any* ticket. Defeats the decorator on `ticket_status_change`, `ticket_delete`, `view/delete_ticket_document`, `comment_create`, `approve_claim_request`, `update_priority`, `ticket_file_upload`.
- **recruitment/decorators.py:186 `candidate_login_required`** — grants access on mere presence of `session["candidate_id"]`; never ties the object to the candidate. Root cause of the candidate-portal IDORs below.

### Company-wide / cross-employee data exposure
- **base/dashboard.py (entire file)** — every KPI endpoint is `@login_required` only; leaks company-wide payroll totals, turnover, gender split, headcount, recruitment pipeline, leave stats, birthdays to any employee. `dashboard_pending_approvals` (line 710) ignores the user entirely and counts all company requests. Template (templates/dashboard.html) has only one perm check (line 896).
- **payroll/dashboard.py:39/251/486/532** — `payroll_kpi_data`, `payroll_top_earners`, `payroll_salary_distribution`, `payroll_component_breakdown`: org-wide salary/earnings to any employee, `@login_required` only.
- **employee/views.py:412 `allowances_deductions_tab`** — IDOR exposing any employee's salary/wage/allowances/deductions by pk.

### Candidate-portal / biometric IDOR
- **recruitment/views/views.py:3952 `file_upload` & :3982 `view_file`** — any logged-in candidate can read/overwrite any other candidate's documents (resumes/PII). No extension/content-type validation on upload.
- **facedetection/views.py:82 `EmployeeFaceDetectionGetPostAPIView`** — `@csrf_exempt` on face enrollment POST + delete.

---

## HIGH

### Payroll
- **payroll/views/views.py:514 `update_payslip_status_no_id`** — any employee can mass-`update()` any payslip's status (no perm/ownership). (id-based sibling at :483 is gated.)
- **payroll/views/views.py:935 `payslip_export` (dashboard)** — any employee can export all payslips (`@login_required` only). (Gated copy exists at component_views.py:1271.)
- **payroll/views/views.py:813/836** — `payslip_details`, `dashboard_department_chart`: sum net_pay over all payslips, `@login_required` only.
- **payroll/dashboard.py:170/218/298/371/431** — department cost, status pipeline, contract status, loan summary, reimbursement summary: org-wide, `@login_required` only.
- **payroll/views/component_views.py:1834 `create_reimbursement`** — IDOR: edit any reimbursement by `instance_id` GET param.
- **payroll/views/views.py:1847 `delete_payrollrequest_comment`** — delete any reimbursement comment by id.

### Employee / Leave
- **employee/cbv/document_request.py:141 `DocumentCreateForm`** — any employee can attach documents to any other employee's profile (`emp_id` from URL, no check).
- **employee/views.py:388 `about_tab`** — IDOR: any employee's personal data + leave balances by pk.
- **employee/views.py:3836 `employee_get_mail_log`**, **:3253 note_tab / add_note / update / delete / add_more_employee_files** — `manager_can_enter` only checks "is a manager," not that target is a subordinate → any manager reads/mutates any employee's notes/mail logs.
- **leave/views.py:2846 `user_request_one`**, **:3494 `leave_allocation_request_single_view`**, **:4106 `employee_available_leave_count`** — IDOR on leave requests/allocations/balances by id/param.

### Attendance
- **attendance/views/views.py:1871 `user_request_one_view`**, **:1916 `get_attendance_activities`** — IDOR read of any employee's attendance request/activities.
- **attendance/views/requests.py:300 `attendance_request_changes`** — IDOR write: raise/overwrite change-requests on any employee's attendance.
- **attendance/views/requests.py:396 `validate_attendance_request`** — discloses any attendance request's full diff by id.

### Recruitment / Offboarding
- **recruitment/views/views.py:1630 `candidate_export`** — exports full candidate table (no perm passed to export_data).
- **recruitment/views/views.py:2560 `candidate_select`/`candidate_select_filter`** — candidate enumeration, `@login_required` only.
- **recruitment/views/views.py:4078 `candidate_add_notes`** & **actions.py:162 `note_delete_individual`** (perm check commented out) — IDOR write/delete on stage notes.
- **offboarding/cbv/resignation.py:182 `ResignationLettersFormView`** — create/edit resignation letters for any employee by pk (feature-check commented out).

### PMS / Project / Helpdesk
- **pms/views.py:2138 `feedback_detailed_view_status`** — IDOR mutate any feedback's status.
- **pms/views.py:3966 `meeting_single_view`** — IDOR read any meeting.
- **project/views.py:1162 `update_project_task_status`**, **:975 `task_stage_change`** — IDOR mutate any task's status/stage.
- **helpdesk/views.py:1000 `ticket_individual_view`** — IDOR read any private ticket.
- **helpdesk/views.py:1210/1261 view/delete_ticket_document** — decorator does `Ticket.objects.get(id=doc_id)` (wrong model lookup) + bypass above → no effective access control.

### API / Auth / LDAP / Media
- **skylinx_api/.../auth/views.py:57 `LoginAPIView.post`** — prints plaintext password to logs.
- **skylinx_api/.../employee/views.py:48+** — serializers use `fields="__all__"` on Employee, work info, **bank details**, **disciplinary actions**, documents → wholesale exposure.
- **skylinx_api/api_decorators/base/decorators.py:33 `ManagerPermission`** — grants access to any reporting manager regardless of the specific perm requested.
- **base/views.py:7867 `protected_media`** — serves any private media file (payslips, documents, face images) to any authenticated user; `safe_join` blocks traversal but not cross-employee access. IDOR.
- **skylinx_ldap/views.py:14 `ldap_settings_view`** — `@login_required` only: any employee can view/overwrite LDAP URI, bind DN, **bind password** (stored plaintext, models.py:9).
- **settings base.py:24,35** `ALLOWED_HOSTS=["*"]`; **base.py:336** hardcoded `DB_INIT_PASSWORD` default.

### facedetection / geofencing
- **facedetection/views.py:112 delete & :199 `reset_employee_face`** — reset any employee's face data, gated by an unrelated `geofencing.add_localbackup` perm (wrong app), no ownership check (IDOR).
- **geofencing/views.py:38** — mass-assignment: passes raw `request.data` (not company-scoped) to serializer → can set `company_id` to another company.

---

## MEDIUM
- **payroll/views/views.py:1700/1810** — read/post comments on any reimbursement request by id.
- **recruitment** — candidate portal login uses email+phone-number-as-password with no throttling (views.py:3216); `update_document_title` (:3889), `stage_title_update` (:1386), `document_create`/`candidate_document_request` (:3860/:3824) lack perm/ownership.
- **onboarding/views.py:1868 `stage_name_update`** (no perm), **:1475 `get_status`** (status disclosure), **:1122 `user_creation`** returns raw exception text to anonymous visitors.
- **offboarding/views.py:1003 `create_resignation_request`** — file resignation against arbitrary employee.
- **attendance/views/views.py:1159 `on_time_view`** (org-wide list); **:2325–2504** attendance-request comment create/view/delete + comment-file delete (all IDOR).
- **leave/views.py:815 `leave_request_filter`** (manager_can_enter commented; leaks interview-clash existence), **:4236/4403** comment threads, **:4618 `view_clashes`** (colleagues' leave dates).
- **project/views.py:1283 `task_all_archive`** (perm commented), **:928 task_details**, **:1971 time_sheet_single_view** — IDOR.
- **pms/views.py:3226** weak perm string `pms.anonymousfeedback`.
- **biometric/views.py:1601/1647** bulk-delete swallow device/DB failures, still report success.
- **asset/views.py:138 `add_asset_report`** — no-id create path lacks `add_assetreport`.
- **API**: bank-details `get()` ignores scoped queryset (employee/views.py:266); `EmployeeTypeAPIView` no perm (:84); stacked bare-except in login (auth/views.py:73).
- **Settings**: no `SESSION_COOKIE_SECURE`/`CSRF_COOKIE_SECURE`/HSTS/SSL redirect; no DRF throttling → unlimited credential brute-force; LDAP bind DN hardcoded.

---

## LOW
- Sensitive JSON without `Cache-Control: no-store` (payroll_summary, turnover in base/dashboard.py).
- Pervasive `except Exception: pass` across dashboard.py, payroll dashboard, facedetection, geofencing, employee — masks errors and would mask a future permission failure (fail-open).
- `open_recruitments` sets `X-Frame-Options: ALLOW-FROM *` (clickjacking).
- `candidate_survey` writes uploads using attacker-supplied filename, no extension/type validation.
- Several API `.first()`/`.get()` without None guards → 500s on bad ids.
- Swagger/ReDoc public (`AllowAny`) exposes full API surface.

---

## /admin/ vs Settings UI
Django `/admin/` is `is_staff`-gated (not public), but operational config living
only in `/admin/` is a hardening gap: any staff user gets the raw admin with no
field-level guardrails. Candidates to surface in the in-app Settings UI instead
(and remove/restrict from admin) need a pass over each app's `admin.py`
registration — recommended as a follow-up.

---

## Verified clean (no action)
- Payslip PDF download (`payslip_pdf`, `view_payslip_pdf`) correctly checks
  `view_payslip` OR ownership — classic PDF IDOR is NOT present.
- `base/ess_dashboard.py` scopes every endpoint to the caller's own Employee.
- Notifications web + API scope to `request.user`.
- `outlook_auth` fully permission-gated; login `next`-param validated against host allowlist.
- Most attendance/asset/biometric/pms create-edit-delete CBVs are correctly
  gated; findings above are the gaps, not the norm.
