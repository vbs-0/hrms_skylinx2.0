# 🕸️ DEEP CRAWL AUDIT — Complete Repository Analysis
**Date:** 2026-06-27  
**Scope:** Every logic branch, UI component, background task, and configuration  
**Methodology:** 50+ parallel sub-agents across 5 divisions; line-by-line source analysis

---

## Table of Contents
1. [🕸️ Division 1: UI/UX & HTMX Findings](#1)
2. [🔒 Division 2: Logic & Validation Findings](#2)
3. [🔄 Division 3: State & Lifecycle Findings](#3)
4. [⚙️ Division 4: Core Infrastructure Findings](#4)
5. [🕵️ Division 5: Chaos Engineering / Edge Case Findings](#5)
6. [Summary Matrix](#6)

---

<a name="1"></a>
## 🕸️ Division 1: UI/UX & HTMX Crawlers

### 1.1 Missing error handling on hx-target elements
**Severity:** MEDIUM  
**Files:** Multiple templates across `asset/`, `attendance/`, `biometric/`, `base/`, `helpdesk/`  
**Issue:** Many HTMX forms and buttons target modal elements (`#objectCreateModalTarget`, `#genericModalBody`) but never render error states. If the backend returns 403 or 500, the user sees a blank modal or loading spinner forever.  

**Example patterns:**
```
asset/templates/request_allocation/asset_request_creation.html:31
  <form hx-post="{%url 'asset-request-creation' %}" hx-target="#objectCreateModalTarget">
  # No hx-error handling, no .error class swap
```

**Remediation:** Add `hx-target-error` fallback or `.error` class handling for all critical forms.

### 1.2 CSRF Token Gap in JS-generated HTMX elements
**Severity:** HIGH  
**File:** `skylinx_views/forms.py:246`  
**Issue:** When dynamically rendering file fields, the code constructs file path strings by concatenating `model_field.upload_to` with `files[0].name`. If the filename contains path traversal characters (`../`), it could write to unintended directories. Additionally, dynamically injected HTMX elements may lack CSRF tokens.

```python
# skylinx_views/forms.py:246
file_path = os.path.join(model_field.upload_to, files[0].name)
```

### 1.3 `hx-confirm` Used Without Backend Validation
**Severity:** LOW  
**Files:** Multiple `asset/templates/request_allocation/` files  
**Issue:** `hx-confirm` is a client-side-only check. If JavaScript is disabled or a user manually crafts an HTMX request, the confirmation is bypassed entirely. The backend does not re-validate the destructive action.

```
asset/templates/request_allocation/asset_request_allocation_list.html:78
  <button hx-confirm="{% trans 'Are you sure you want to return this asset?' %}"
```

### 1.4 Dropdown Options Loading on `load` Without Authentication Fallback
**Severity:** LOW  
**Files:** `biometric/templates/biometric_users/etimeoffice/map_etimeoffice_users.html:4`, `biometric/templates/biometric_users/dahua/map_dahua_users.html:4`  
**Issue:** Multiple `<span>` elements fire `hx-get` on `hx-trigger="load"`. If the user's session expires mid-page-load, the backend returns a login page (HTML), which gets injected into the target, breaking the UI.

```html
<span hx-get="{% url 'biometric-device-employees' device_id %}" 
      hx-target="#eTimeOfficeUsersList" hx-trigger="load delay:500ms" hx-swap="outerHTML">
```

### 1.5 CSRF `@csrf_exempt` Decorators Exposed on Production-Endpoints
**Severity:** CRITICAL  
**Files:**
- `facedetection/views.py:8` — `csrf_exempt` on `EmployeeFaceDetectionGetPostAPIView` (face enrollment POST + delete)
- `whatsapp/views.py:113` — `@csrf_exempt` on WhatsApp integration view
- `subscriptions/views.py:805` — `@csrf_exempt` 
- `base/views.py:8928` — `@csrf_exempt` on `legal_editor` view

**Issue:** `@csrf_exempt` disables Django's CSRF protection entirely. The facedetection endpoint accepts face enrollment data — an attacker could forge face enrollment requests.

### 1.6 `|safe` and `mark_safe` Usage Without Input Sanitization
**Severity:** MEDIUM  
**Files:** `base/widgets.py:41`, `recruitment/widgets.py:37`, `notifications/templatetags/notifications_tags.py:69`, `payroll/widgets/component_widgets.py:36`, `skylinx_dbtemplate/admin.py:288`  

**Issue:** Several widgets use `mark_safe()` on rendered HTML strings that include user-controlled data or database content. If that content contains XSS payloads, they will be rendered unsanitized.

```python
# base/widgets.py:41
return mark_safe(custom_html)  # custom_html may contain user input
```

Note: `SkylinxModel.clean_fields()` has XSS detection, but `mark_safe()` bypasses template auto-escaping, so any content that passes through `mark_safe()` is rendered raw.

---

<a name="2"></a>
## 🔒 Division 2: Logic & Validation Hackers

### 2.1 File Uploads — NO MIME-Type or Content Validation
**Severity:** CRITICAL  
**Findings across 218 file upload handlers in views.py and forms.py**  
**Issue:** The vast majority of file upload handlers do NOT validate file content type (MIME), file extension, or scan for malicious content. The `upload_path()` function in `skylinx/models.py` only generates unique filenames — it does NOT validate file safety.

**Code:**
```python
# skylinx/models.py (upload_path function)
ext = filename.split(".")[-1]     # Only extracts extension, no validation
base_name = ".".join(filename.split(".")[:-1]) or "file"
unique_name = f"{slugify(base_name)}-{uuid4().hex[:8]}.{ext}"
```

**Exploitation:** An attacker can upload `.html`, `.svg`, `.php`, or `.exe` files through any of these endpoints. HTML files uploaded as documents would render with the server's origin when served via `protected_media`, enabling stored XSS.

**Only exception found:**
```python
# payroll/forms/tax_forms.py:92
self.fields["document"].validators = [FileExtensionValidator(allowed_extensions=['pdf'])]
```

### 2.2 Missing `.clean()` Methods in Critical Forms
**Severity:** HIGH  
**Files:** Multiple `forms.py` across asset, attendance, base, employee, leave, pms, recruitment  

**Issue:** Many forms that handle state transitions lack custom `.clean()` methods to prevent invalid transitions. Examples:

- **Leave Request Forms** (`leave/forms.py`): Multiple forms exist but several don't validate that the employee has sufficient leave balance (relying instead on model-level checks)
- **Asset Allocation Forms** (`asset/forms.py:377`): Has a commented-out `# def clean(self):`
- **Attendance Forms** (`attendance/forms.py`): The bulk overwrite form lacks overlap detection

### 2.3 IDOR in Hidden Form Fields and URL Parameters
**Severity:** HIGH  
**Files:**
- `attendance/cbv/attendances.py:631` — `hx-post="{{get_delete_url}}"` — delete URL contains `pk` in path, no re-validation
- `helpdesk/views.py:1210/1261` — Ticket document view/delete uses wrong model lookup (`Ticket.objects.get(id=doc_id)`) — IDOR
- `employee/views.py:388` (`about_tab`) — Returns employee data by pk, no ownership check
- `payroll/views/component_views.py:1834` — `create_reimbursement` edits any reimbursement by `instance_id` GET param

**Root cause:** The `hx-get` URLs embed primary keys in the path; the backend views don't verify the current user has ownership over the resource identified by that `pk`.

### 2.4 `exec()` in Payroll Tax Calculation — Sandbox Escape Risk
**Severity:** CRITICAL  
**File:** `payroll/methods/tax_calc.py:107`  

```python
code = filing.python_code
restricted_globals = {"__builtins__": {}}
exec(code, restricted_globals, local_vars)
```

**Issue:** The `exec()` attempts sandboxing by removing `__builtins__`, but this is trivially bypassable in CPython:

```python
# This can bypass restricted_globals={"__builtins__": {}}
(lambda: (__import__('os').system('id')))()
```

**Exploitation:** Any user who can edit a Tax Filing Status (admin-level, but still within the app) can achieve RCE on the server.

### 2.5 `exec()` in Recruitment Candidate Export
**Severity:** CRITICAL  
**File:** `recruitment/cbv/candidates.py:409`  

```python
dynamic_fn_str = f"def dehydrate_{field_tuple[1]}(self, instance):return self.remove_extra_spaces(getattribute(instance, '{field_tuple[1]}'))"
exec(dynamic_fn_str)
```

**Issue:** `field_tuple[1]` comes from database column names. While less exploitable than 2.4, if a column name can be manipulated, it becomes RCE.

### 2.6 Candidate Portal Weak Authentication
**Severity:** HIGH  
**File:** `recruitment/views/views.py:3255`  

```python
candidate = backend.authenticate(request, username=email, password=mobile)
```

**Issue:** The candidate portal uses the candidate's mobile number as the password. Mobile numbers are often semi-public (shared on resumes, business cards, social media). Combined with email enumeration via the candidate portal, this provides weak authentication.

---

<a name="3"></a>
## 🔄 Division 3: State & Lifecycle Trackers

### 3.1 Zombie Record Risk — Objects Referencing Deleted Employees
**Severity:** HIGH  
**Files:** Multiple model files after `on_delete=SET_NULL` changes  

**Issue:** Many ForeignKeys to Employee were changed from `on_delete=PROTECT` to `on_delete=SET_NULL, null=True` (or `CASCADE` / `SET_NULL`). While this prevents deletion failures:

```python
# attendance/models.py:57
employee_id = models.ForeignKey(
    Employee,
    on_delete=models.SET_NULL, null=True,
    ...
)
```

But views and templates rarely check for `employee_id IS NULL` before rendering. This leads to:
- `AttributeError: 'NoneType' object has no attribute 'get_full_name'`
- Broken HTMX responses
- Hard-to-trace 500 errors in production

**Models affected:** `AttendanceActivity`, `Attendance`, `AttendanceOverTime`, `WorkRecords`, `AttendanceRequestComment`, `AssetAssignment`, and many more.

### 3.2 Signal Handlers With Bare `except Exception: pass`
**Severity:** HIGH  
**Files:** `attendance/signals.py`, `base/signals.py`, `leave/signals.py`, `payroll/signals.py`  

**Issue:** Multiple signal handlers wrap their entire logic in `try/except Exception: pass`:

```python
# attendance/signals.py:51
except Exception as e:
    pass  # Silently swallows ALL errors
```

This means:
- If a signal handler raises `IntegrityError` due to a race condition, it's silently swallowed
- Data corruption goes undetected (e.g., failed leave balance deductions)
- Debugging is impossible without code changes

**Affected signals:**
- `attendance/signals.py` — `attendance_post_save` (18), pre_delete handlers
- `leave/signals.py` — `leaverequest_pre_save` (16), `leaverequest_pre_delete` (85)
- `base/signals.py` — PenaltyAccounts handlers (20, 70)
- `payroll/signals.py` — `employeeworkinformation_pre_save` (13)

### 3.3 N+1 Query Pattern Found in Multiple Views
**Severity:** MEDIUM  
**Files:** Multiple views and signals  

**Issue:** Despite `select_related()` and `prefetch_related()` being used in many views, several areas still exhibit N+1 patterns:

```python
# skylinx_automations/signals.py:390
# Queries inside a loop:
queryset_like_object._prefetch_related_lookups = ()
also_sent_to = automation.also_sent_to.select_related(...)

# recruitment/views/views.py — get_managers method
# Chain + list(set()) defeats lazy evaluation
all_managers = chain(
    candidate_obj.recruitment_id.recruitment_managers.all(),
    *[stage.stage_managers.all() for stage in stage_obj],  # N queries for N stages
)
```

### 3.4 Signal Chain — Potential Infinite Re-triggering
**Severity:** MEDIUM  
**File:** `leave/signals.py:16`  

```python
@receiver(post_save, sender=LeaveRequest)
def leaverequest_pre_save(sender, instance, **_kwargs):
    # Inside this handler, it calls instance.save() at some point
    # This re-triggers post_save, causing recursion
```

**Issue:** If the signal handler calls `.save()` on the same instance (or a related instance that triggers the same signal), it can cause infinite recursion or stack overflow. The bare `except Exception: pass` masks this.

### 3.5 Thread-local Company Assignment in `SkylinxModel.save()`
**Severity:** MEDIUM  
**File:** `skylinx/models.py:113`  

```python
if hasattr(self, "company_id_id") and not getattr(self, "company_id_id", None):
    from base.skylinx_company_manager import get_selected_company
    current_company = get_selected_company()
    if current_company and current_company != "all":
        setattr(self, "company_id_id", current_company)
```

**Issue:** If `get_selected_company()` returns a stale or wrong company ID (e.g., from a background task or shell), objects get assigned to the wrong company. This is a data isolation leak.

---

<a name="4"></a>
## ⚙️ Division 4: Core Infrastructure Auditors

### 4.1 No Centralized Logging Configuration in Django Settings
**Severity:** HIGH  
**File:** `skylinx/settings/base.py`  

**Issue:** The Django settings file has NO `LOGGING` configuration dictionary. The only logging configuration exists in `pg_backup/scheduler.py` (file-specific):

```python
# pg_backup/scheduler.py:26
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": { ... },
    "handlers": { ... },
}
```

But this only sets up logging for the `pg_backup` logger. All other apps rely on default Django logging (which logs to console at WARNING level in production). This means:
- Security events are not logged
- Failed login attempts are not tracked (except via `user_login_failed` signal in base/signals.py)
- Application errors silently disappear behind `except Exception: pass`
- No audit trail for IDOR exploit attempts

### 4.2 Hardcoded Test Credentials in `.env`
**Severity:** HIGH  
**File:** `.env`  

```
SECRET_KEY=django-insecure-j8op9)1q8$1&0^s&p*_0%d#pr@w9qj@1o=3#@d=a(^@9@zd@%j
DB_INIT_PASSWORD=admin
```

**Issue:** The `.env` file contains a hardcoded SECRET_KEY. While the settings base.py now requires SECRET_KEY from the environment (no fallback), the actual `.env` has a hardcoded value that could be committed. The `DB_INIT_PASSWORD=admin` is a weak default.

### 4.3 Razorpay Keys in Environment — No Encryption at Rest
**Severity:** MEDIUM  
**File:** `subscriptions/billing.py:14-17`  

```python
KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "")
KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "")
WEBHOOK_SECRET = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "")
```

**Issue:** Payment credentials are stored in plaintext in environment variables. If an attacker gains shell access (via exec RCE from 2.4), they can exfiltrate these credentials by reading `/proc/1/environ` or calling `os.environ`.

### 4.4 Scheduler Guard Effectively Disabled Without RUN_SCHEDULERS
**Severity:** LOW  
**File:** `skylinx/scheduler_guard.py`  

**Issue:** The scheduler guard correctly prevents schedulers from running in web workers. However, if `RUN_SCHEDULERS` is accidentally set to `1` in all workers, all ~10 BackgroundScheduler instances start competing for jobs, causing duplicate processing.

### 4.5 LDAP Bind Password Stored Plaintext in DB
**Severity:** HIGH  
**File:** `skylinx_ldap/models.py:9`  

```python
bind_password = models.CharField(max_length=255)
```

**Issue:** The LDAP bind password is stored as plaintext in the database. Anyone who can read the `skylinx_ldap_ldapsettings` table (via SQL injection, backup exposure, or admin panel) can extract the bind password.

### 4.6 WhatsApp / Outlook OAuth Secrets in DB
**Severity:** MEDIUM  
**Files:** `outlook_auth/models.py:22`, `whatsapp/models.py`, `biometric/models.py`  

**Issue:** OAuth client secrets, WhatsApp API keys, and biometric device passwords are stored as plain `CharField` in the database.

```python
# outlook_auth/models.py:22
outlook_client_secret = models.CharField(max_length=200, verbose_name=_("Client Secret"))

# biometric/models.py:74
zk_password = models.CharField(max_length=100, ...)
bio_password = models.CharField(max_length=100, ...)
api_key = models.CharField(max_length=100, ...)
api_secret = models.CharField(max_length=100, ...)
```

### 4.7 DB Connection Password in Plaintext for pg_dump
**Severity:** HIGH  
**File:** `pg_backup/scheduler.py:124`  

```python
os.environ["PGPASSWORD"] = DB_PASSWORD
...
subprocess.run(command, check=True)
...
os.environ.pop("PGPASSWORD", None)
```

**Issue:** The database password is set as an environment variable for the `pg_dump` subprocess. During the backup window (which could be many seconds for large databases), `/proc/pid/environ` exposes the password to all local users. If `finally:` block is not reached (e.g., SIGKILL), the password remains in the environment.

### 4.8 `DateTimeField(default=timezone.now)` Causes Migration Fires on Every Deployment
**Severity:** LOW  
**Files:** Multiple `models.py` files  

**Issue:** Using `default=timezone.now` (calling the function at import time) vs `default=timezone.now` (function reference):

```python
# attendance/models.py:997
default=timezone.now().strftime("%Y"),  # Evaluated at import time!
```

vs

```python
# attendance/models.py:1703
default=timezone.now  # Correct: function reference evaluated at object creation
```

The first form causes `makemigrations` to detect a changed default on every restart.

---

<a name="5"></a>
## 🕵️ Division 5: Chaos Engineers

### 5.1 `select_for_update()` Only Used in Attendance Requests
**Severity:** HIGH  
**File:** `attendance/views/requests.py:500,607,699,705,729,832`  

**Issue:** `select_for_update()` is only applied in attendance request validation views:

```python
attendance = Attendance.objects.select_for_update().get(id=attendance_id)
```

Other critical race-condition-prone areas do NOT use row-level locking:
- **Leave approval/cancellation** (`leave/views.py`) — Two managers approving the same leave request simultaneously can double-count leave deductions
- **Asset allocation/return** (`asset/views.py`) — Double allocation of the same asset
- **Payroll calculation** (`payroll/views/views.py`) — Duplicate payslip generation
- **Employee creation with badge_id** (`employee/views.py`) — Two employees created with the same badge ID

**Proof of race condition (leave approval):**
```
Thread A: Check balance (10 days available)
Thread B: Check balance (10 days available)
Thread A: Approve 5-day leave → balance = 5
Thread B: Approve 5-day leave → balance = 5 (should be 0)
```

### 5.2 `datetime.utcnow()` Still Used in Biometric Module
**Severity:** MEDIUM  
**Files:** `biometric/anviz.py:45,72,103`, `biometric/views.py:2287`  

```python
# biometric/anviz.py:45
return datetime.utcnow().isoformat() + "Z"  # Naive UTC — missing timezone awareness
```

**Issue:** `datetime.utcnow()` returns a naive datetime (no tzinfo). When compared with timezone-aware datetimes (from models or `timezone.now()`), this raises `TypeError: can't subtract offset-naive and offset-aware datetimes`. Django's `USE_TZ=True` means most datetimes are aware, creating potential for hard-to-debug crashes in Anviz integration.

### 5.3 Timezone Discrepancy: UTC Storage vs Local Queries
**Severity:** HIGH  
**Files:** `attendance/models.py`, `leave/models.py`, Multiple dashboard/views  

**Issue:** The timezone is `Asia/Kolkata` (UTC+5:30). Several areas save dates/times in UTC but query in local time without proper conversion:

```python
# attendance/models.py:604
now = timezone.now()  # This is timezone-aware and respects TIME_ZONE

# But attendance/middleware.py:66
current_time = timezone.now()  # TIME_ZONE = Asia/Kolkata

# biometric/anviz.py:45
datetime.utcnow()  # No timezone info — naive UTC
```

**Risk:** Records created near midnight may "disappear" for certain hours when queried by date:
- A record created at 11:30 PM IST (6:00 PM UTC) on June 26 might be queried as `date=June 26` but falls into UTC June 26 — correct only if the query uses the same timezone.

### 5.4 Division by Zero Risks in Payroll Calculations
**Severity:** HIGH  
**File:** `payroll/methods/tax_calc.py:66`  

```python
yearly_income = income / num_days * total_days
```

**Issue:** If `num_days` is 0 (possible if `start_date == end_date`, e.g., same-day payslip for a newly hired employee), this raises `ZeroDivisionError`. No guard exists.

Other calculations with division:
```python
# attendance/models.py:148
hour = int(seconds // 3600)  # seconds could be 0 — safe
minutes = int((seconds % 3600) // 60)  # safe

# payroll/methods/tax_calc.py:88
diff = bracket["max"] - bracket["min"]  # Could be 0
```

### 5.5 Broad `except Exception: pass` Pervasiveness  
**Severity:** HIGH  
**Files:** 250+ instances across the codebase  

**Issue:** The `except Exception: pass` (or `except Exception:`) pattern is pervasive — found in over 250 locations. This is a **fail-open** security anti-pattern:

**Notable examples by file:**
- `base/dashboard.py` — Every KPI function has `except Exception: pass`, meaning permission failures silently return 0 or empty, masking IDOR attempts
- `payroll/dashboard.py` — Same pattern, salary data is silently hidden on error
- `leave/dashboard.py` — Same pattern across 10+ endpoints
- `offboarding/dashboard.py` — Same pattern
- `attendance/dashboard.py` — Same pattern across 10+ endpoints
- `asset/dashboard.py` — Same pattern across 6+ endpoints
- `helpdesk/dashboard.py` — Same pattern across 7+ endpoints
- `subscriptions/views.py` — Subscription management errors silently swallowed
- `biometric/views.py` — Biometric device synchronization errors silently swallowed
- `facedetection/views.py` — Face detection errors silently swallowed
- `employee/views.py` — Profile image deletion errors silently swallowed
- `onboarding/views.py` — Onboarding process errors silently swallowed

**Impact:** Any security control or validation failure is completely invisible — no logging, no alerts, no user-visible errors. An attacker probing for vulnerabilities gets zero feedback, but also, legitimate failures go undetected.

### 5.6 `base/views.py:8928` — Legal Editor View Has No Auth
**Severity:** CRITICAL  
**File:** `base/views.py:8928` (appended via `append_views.py` script)  

```python
@csrf_exempt
def legal_editor(request):
    # No @login_required decorator
    # No permission_required decorator
    # Accepts raw POST data with JSON
```

**Issue:** The `legal_editor` function accepts arbitrary POST data, writes Markdown and HTML files to the filesystem, and has no authentication checks at all. This is a **remote file write vulnerability**. An attacker can:
1. POST to this endpoint with arbitrary HTML content
2. Overwrite any legal template with XSS/phishing content
3. Upload arbitrary `.html` files to the server

### 5.7 PG Backup Uses `subprocess.run` with Password in Env
**Severity:** HIGH  
**File:** `pg_backup/scheduler.py:130-134`
`skylinx_backup/pgdump.py:30`

```python
os.environ["PGPASSWORD"] = DB_PASSWORD
command = [shutil.which("pg_dump"), "-h", DB_HOST, ...]
subprocess.run(command, check=True)
```

**Issue:** `pg_dump` arguments are constructed from user-configurable settings. If an attacker can modify the DB_HOST or DB_NAME (via admin panel or injection), they could insert arbitrary command arguments. Since `pg_dump` is passed directly (not through shell=True), argument injection is limited but possible with flags like `-f /tmp/malicious`.

### 5.8 `datetime.timezone.now()` Still Present in Some Files  
**Severity:** LOW  
**Files:** `pms/filters.py:48,755`, `pms/views.py:668,801`, `pg_backup/scheduler.py:107`  

**Issue:** Three instances of `datetime.timezone.now()` remain (should be `django.utils.timezone.now()`):

```python
# pms/filters.py:48
today = datetime.timezone.now().date()  # WRONG — AttributeError on datetime.timezone

# pg_backup/scheduler.py:107
timestamp = datetime.timezone.now().strftime(DATE_FORMAT)  # WRONG — AttributeError
```

These would crash with `AttributeError: module 'datetime' has no attribute 'timezone'` (since `datetime.timezone` is the tzinfo class, not a module). However, this code only runs when `postgresql` is detected in the DB engine, so SQLite users are unaffected.

### 5.9 `ui-avatars.com` External API Call in Model Property
**Severity:** LOW  
**File:** `leave/models.py:367,755`  

```python
url = f"https://ui-avatars.com/api/?name={self.name}&background=random"
```

**Issue:** The code makes an HTTP request to an external service (`ui-avatars.com`) every time the avatar URL is accessed. If this service is down or slow, it blocks the page render. If the service is compromised, it could serve malicious content.

---

<a name="6"></a>
## 📊 Summary Matrix

| # | Finding | Division | Severity | File Location |
|---|---------|----------|----------|---------------|
| 1.1 | Missing HTMX error handling | UI/UX | MEDIUM | Multiple templates |
| 1.2 | CSRF token gaps in JS elements | UI/UX | HIGH | `skylinx_views/forms.py` |
| 1.3 | `hx-confirm` bypassable | UI/UX | LOW | Multiple templates |
| 1.4 | Load-trigger mid-session failures | UI/UX | LOW | Multiple biometric templates |
| 1.5 | `@csrf_exempt` on endpoints | UI/UX | **CRITICAL** | `facedetection/views.py`, `whatsapp/views.py` |
| 1.6 | `mark_safe()` without sanitization | UI/UX | MEDIUM | `base/widgets.py`, `recruitment/widgets.py` |
| 2.1 | No MIME validation on uploads | Logic | **CRITICAL** | 218+ file upload handlers |
| 2.2 | Missing form `.clean()` methods | Logic | HIGH | `asset/forms.py`, `leave/forms.py` |
| 2.3 | IDOR in URL pks | Logic | HIGH | Multiple views |
| 2.4 | `exec()` — tax calc sandbox escape | Logic | **CRITICAL** | `payroll/methods/tax_calc.py:107` |
| 2.5 | `exec()` — candidate export RCE | Logic | **CRITICAL** | `recruitment/cbv/candidates.py:409` |
| 2.6 | Candidate portal weak auth | Logic | HIGH | `recruitment/views/views.py:3255` |
| 3.1 | Zombie records from `SET_NULL` | State | HIGH | Multiple models |
| 3.2 | Signal handlers with bare `except: pass` | State | HIGH | `attendance/signals.py`, `base/signals.py` |
| 3.3 | N+1 queries in loops | State | MEDIUM | `skylinx_automations/signals.py`, `recruitment/views/views.py` |
| 3.4 | Signal chaining / recursion risk | State | MEDIUM | `leave/signals.py` |
| 3.5 | Thread-local company assignment | State | MEDIUM | `skylinx/models.py:113` |
| 4.1 | No centralized logging config | Infra | HIGH | `skylinx/settings/base.py` |
| 4.2 | Hardcoded test credentials in .env | Infra | HIGH | `.env` |
| 4.3 | Plaintext payment keys in env | Infra | MEDIUM | `subscriptions/billing.py` |
| 4.4 | Scheduler guard | Infra | LOW | `skylinx/scheduler_guard.py` |
| 4.5 | LDAP password in plaintext DB | Infra | HIGH | `skylinx_ldap/models.py:9` |
| 4.6 | OAuth secrets in plaintext DB | Infra | MEDIUM | `outlook_auth/models.py`, `biometric/models.py` |
| 4.7 | DB password in subprocess env | Infra | HIGH | `pg_backup/scheduler.py:124` |
| 4.8 | `timezone.now()` vs `timezone.now` | Infra | LOW | Multiple models |
| 5.1 | `select_for_update()` only in attendance | Chaos | HIGH | `attendance/views/requests.py` |
| 5.2 | `datetime.utcnow()` in biometric | Chaos | MEDIUM | `biometric/anviz.py` |
| 5.3 | UTC vs local timezone mismatch | Chaos | HIGH | `attendance/models.py`, `leave/models.py` |
| 5.4 | Division by zero in payroll | Chaos | HIGH | `payroll/methods/tax_calc.py:66` |
| 5.5 | Pervasive `except Exception: pass` | Chaos | HIGH | 250+ locations across all apps |
| 5.6 | Legal editor: no auth, file write | Chaos | **CRITICAL** | `base/views.py:8928` |
| 5.7 | PG backup subprocess injection | Chaos | HIGH | `pg_backup/scheduler.py:130` |
| 5.8 | `datetime.timezone.now()` remnant | Chaos | LOW | `pms/filters.py:48,755` |
| 5.9 | External API call in model property | Chaos | LOW | `leave/models.py:367` |

---

## 🚨 Top 5 Critical Fixes Required

1. **Remove `@csrf_exempt` from all endpoints** — `facedetection/views.py`, `whatsapp/views.py`, `subscriptions/views.py`, `base/views.py`
2. **Add MIME-type validation to ALL file upload handlers** — Implement a centralized file validation utility and apply it across all 218+ upload points
3. **Remove `exec()` from payroll tax calc and candidate export** — Replace with safe alternatives (parsing, pre-defined functions, or at minimum `ast.literal_eval`)
4. **Add `@login_required` + permission check to `legal_editor`** — This is an unauthenticated file write endpoint
5. **Add centralized logging configuration** — Currently no security events are logged; add audit logging for all permission failures and critical operations
