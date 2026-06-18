# 🏢 Skylinx HRMS 2.0 — Complete Feature Audit Report

**Generated:** June 17, 2026
**Project:** Skylinx HRMS 2.0
**Platform:** Django 5.2 / PostgreSQL / Redis / Docker

---

## 📋 Executive Summary

**Skylinx HRMS** is a comprehensive, open-source Human Resource Management System built on **Django 5.2** with **PostgreSQL**, **Redis**, and Docker orchestration. It features custom theming, Skylinx brand identity, and additional enhancements. The system spans **~30+ Django apps** covering the full employee lifecycle — from recruitment and onboarding through performance management to offboarding and exit management.

> **Overall Assessment:** Production-grade HRMS with comprehensive feature coverage across the entire employee lifecycle. Strong multi-tenancy, excellent audit trail, multiple communication channels, and extensive scheduled automation.

---

## 🔷 Module 1: Employee Management (`employee`)

### Features Present

| Feature | Status | Notes |
|---|---|---|
| Employee Profiles | ✅ Present | Basic info, contact, DOB, gender, marital status, profile image |
| Employee Work Information | ✅ Present | Department, job position, role, shift, work type, reporting manager, company, joining date, contract end, salary |
| Employee Bank Details | ✅ Present | Bank name, account number, branch, codes |
| Employee Tags | ✅ Present | Color-coded tagging system |
| Organization Chart | ✅ Present | Visual hierarchy via sidebar |
| Disciplinary Actions | ✅ Present | Warning, suspension, dismissal with auto-login block/unblock |
| Disciplinary Action Types | ✅ Present | Customizable action types |
| Employee Notes | ✅ Present | Notes with file attachments |
| Policies | ✅ Present | Company policies with visibility controls |
| Bonus Points | ✅ Present | Employee bonus/reward points with encashment |
| Employee General Settings | ✅ Present | Badge ID prefix configuration |
| Profile Edit Feature | ✅ Present | Self-service profile editing toggle |
| ESS Dashboard | ✅ Present | Employee self-service dashboard |
| Badge ID | ✅ Present | Unique badge ID with uniqueness constraint |
| Accessibility Restrictions | ✅ Present | Per-user feature visibility controls |

### Audit Notes

- **Security:** XSS detection in all text/char fields via `has_xss()`
- **Auth:** Auto-creates Django user on employee creation with default permissions
- **Performance:** Experience calculator runs via scheduler (every 4 hours)
- **Multi-tenancy:** All employee models use `SkylinxCompanyManager` for company isolation
- **Audit:** Work info and bonus points have full audit logging via `SkylinxAuditLog`

---

## 🔷 Module 2: Recruitment / Hiring (`recruitment`)

### Features Present

| Feature | Status | Notes |
|---|---|---|
| Recruitment Campaigns | ✅ Present | Job postings with start/end dates, vacancy tracking |
| Stages Pipeline | ✅ Present | Configurable pipeline stages (initial, test, interview, hired, cancelled) |
| Candidates | ✅ Present | Full candidate profiles, resume upload, ratings, source tracking |
| Interview Scheduling | ✅ Present | Schedule interviews with interviewers, date/time tracking |
| Candidate Rating | ✅ Present | 1-5 star rating per employee |
| Skill Zone (Talent Pool) | ✅ Present | Future-ready candidate talent pool |
| Rejected Candidates | ✅ Present | Tracking with reject reasons |
| Reject Reasons | ✅ Present | Configurable rejection reasons |
| Skills Management | ✅ Present | Skill library for job matching |
| Recruitment Surveys | ✅ Present | Custom survey questions (text, rating, checkbox, file upload, etc.) |
| Survey Templates | ✅ Present | Reusable survey templates |
| Candidate Self-Tracking | ✅ Present | Self-service status tracking portal |
| Candidate Document Requests | ✅ Present | Request documents from candidates |
| LinkedIn Integration | ✅ Present | Post jobs to LinkedIn, API token management |
| Resume Upload | ✅ Present | PDF resume storage |
| Recruitment Dashboard | ✅ Present | KPI overview |
| Offer Letter Management | ✅ Present | Status tracking (not sent → sent → accepted/rejected → joined) |
| Open Jobs Portal | ✅ Present | Public-facing open positions |

### Audit Notes

- **Scheduler:** Auto-closes recruitments past end date; auto-converts candidates whose email matches existing users
- **Audit:** Candidates and rejections have full audit history
- **Google Meet Integration:** Interview meetings can create Google Meet links
- **Multi-tenancy:** Company-scoped via `SkylinxCompanyManager`
- **Security:** Resume validation only accepts PDF; profile image validation

---

## 🔷 Module 3: Onboarding (`onboarding`)

### Features Present

| Feature | Status | Notes |
|---|---|---|
| Onboarding Stages | ✅ Present | Staged onboarding pipeline |
| Onboarding Tasks | ✅ Present | Configurable tasks per stage |
| Candidate-to-Employee Conversion | ✅ Present | Hire → onboard → employee flow |
| Onboarding Portal | ✅ Present | Candidate self-service portal with token |
| Task Management | ✅ Present | Task status tracking (todo, scheduled, ongoing, stuck, done) |
| Onboarding Dashboard | ✅ Present | Pipeline overview |

### Audit Notes

- **Signal-based:** Initial stage auto-created when Recruitment is saved via `post_save` signal
- **Audit:** Task history tracked via audit log
- **Proxy Model:** `OnboardingCandidate` is a proxy of `Candidate` for clean separation

---

## 🔷 Module 4: Offboarding / Exit Management (`offboarding`)

### Features Present

| Feature | Status | Notes |
|---|---|---|
| Offboarding Pipelines | ✅ Present | Configurable exit process stages |
| Stage Types | ✅ Present | Notice period, exit interview, work handover, FnF settlement, farewell, archived |
| Employee Assignment | ✅ Present | Add employees to offboarding process |
| Resignation Letters | ✅ Present | Request → Approve/Reject workflow |
| Notice Period Tracking | ✅ Present | Start/end dates with day count |
| Offboarding Tasks | ✅ Present | Task assignment per stage with status |
| Exit Reasons | ✅ Present | Reason collection with attachments |
| Offboarding Notes | ✅ Present | Employee notes during exit |
| Dashboard | ✅ Present | KPI overview |
| General Settings | ✅ Present | Enable/disable resignation requests |

### Audit Notes

- **Signal-based:** Default stages created on `Offboarding` save
- **Scheduler:** Disciplinary action auto-block/unblock runs every 60 seconds
- **Notifications:** Tasks send notification to employees
- **Integration:** Asset management link for tracking offboarding employee assets
- **Multi-tenancy:** Company-scoped

---

## 🔷 Module 5: Time & Attendance (`attendance`)

### Features Present

| Feature | Status | Notes |
|---|---|---|
| Attendance Recording | ✅ Present | Check-in/check-out with dates and times |
| Attendance Activities | ✅ Present | Multiple in/out activities per day |
| Work Records | ✅ Present | Daily work records with status (Present, Half-Day, Absent, Holiday, Conflict) |
| Overtime Tracking | ✅ Present | Worked hours vs minimum hours, overtime calculation |
| Hour Account (Monthly) | ✅ Present | Monthly overtime/pending hours summary |
| Late Come / Early Out Tracking | ✅ Present | Automated detection with penalties |
| Attendance Validation | ✅ Present | Validate/invalidate attendance records |
| Attendance Requests | ✅ Present | Create/update attendance via requests |
| Batch Attendance | ✅ Present | Bulk attendance entry |
| Grace Time Configuration | ✅ Present | Configurable grace periods for check-in/out |
| Validation Conditions | ✅ Present | Auto-approve OT, overtime cutoff, minimum OT to approve |
| Check In/Check Out Settings | ✅ Present | Enable/disable self check-in |
| IP Restriction | ✅ Present | Restrict attendance to allowed IPs |
| My Attendance | ✅ Present | Employee self-view |
| Dashboard | ✅ Present | KPI summaries, trends, department breakdowns |

### Audit Notes

- **Scheduler:** Work records auto-created every 30 min and daily at 00:30; OT recalculation on save
- **Penalty System:** Late/early records can trigger penalty deductions (to payroll)
- **Audit:** Full audit logging on attendance records
- **Integration:** Biometric devices feed attendance via face/geofencing config
- **Multi-tenancy:** Company-scoped
- **Complex Save Logic:** OT recalculated across all attendances in month on each save

---

## 🔷 Module 6: Leave / Time Off (`leave`)

### Features Present

| Feature | Status | Notes |
|---|---|---|
| Leave Types | ✅ Present | Configurable leave types with color, icon, paid/unpaid |
| Payment Types | ✅ Present | Fully paid, half paid, unpaid, custom percentage |
| Leave Assignment | ✅ Present | Assign leave balances to employees |
| Leave Requests | ✅ Present | Full request → approve → reject workflow |
| Leave Allocation Requests | ✅ Present | Request additional leave allocation |
| Compensatory Leave | ✅ Present | Leave earned from overtime work |
| Holidays Management | ✅ Present | Company holidays with recurring option |
| Company Leaves | ✅ Present | Recurring company-wide off days |
| Restricted Leaves | ✅ Present | Blackout dates per department/job position |
| Carryforward | ✅ Present | Configurable: no carryforward, carryforward, carryforward with expiry |
| Leave Reset | ✅ Present | Yearly/monthly/weekly auto-reset |
| Multiple Approval | ✅ Present | Multi-level conditional approval routing |
| Leave Clash Detection | ✅ Present | Detect overlapping leaves in same department/position |
| Past Leave Restriction | ✅ Present | Block past-date requests |
| Leave Conditions | ✅ Present | Gender, marital, nationality, department, etc. conditions |
| Dashboard | ✅ Present | KPI summaries, trends, utilization rates |
| Employee Dashboard | ✅ Present | Personal leave dashboard |
| Comments | ✅ Present | Comments on leave requests with file attachments |

### Audit Notes

- **Scheduler:** Leave reset runs every 20 seconds checking for reset dates
- **Signal:** `pre_scheduler` and `post_scheduler` signals for extensibility
- **Audit:** Leave requests and allocation requests have full audit history
- **Complex Logic:** `cal_effective_requested_days` accounts for holidays/company leaves
- **Multi-tenancy:** Company-scoped
- **Notifications:** Multiple approval managers get notified

---

## 🔷 Module 7: Payroll (`payroll`)

### Features Present

| Feature | Status | Notes |
|---|---|---|
| Contracts | ✅ Present | Employee contracts with status (active/expired) |
| Allowances | ✅ Present | Customizable allowance components |
| Deductions | ✅ Present | Customizable deduction components |
| Payslips | ✅ Present | Monthly payslip generation |
| Auto Payslip Generation | ✅ Present | Scheduled auto-generation per company |
| Loan / Advanced Salary | ✅ Present | Loan accounts with installment tracking |
| Encashments & Reimbursements | ✅ Present | Leave encashment, expense reimbursement |
| Federal Tax | ✅ Present | Tax filing status configuration |
| Employer Contributions | ✅ Present | Employer-side contribution calculation |
| Payroll Dashboard | ✅ Present | Payroll analytics |
| Payroll Settings | ✅ Present | General payroll configuration |

### Audit Notes

- **Scheduler:** Contract expiration check every 4 hours; auto-payslip generation every 3 hours
- **Complex Calculation:** Payroll calculation uses `payroll_calculation()` and `calculate_employer_contribution()`
- **Integration:** Penalty deductions auto-create payroll deductions via signals
- **Multi-tenancy:** Company-scoped payslip generation

---

## 🔷 Module 8: Performance Management / PMS (`pms`)

### Features Present

| Feature | Status | Notes |
|---|---|---|
| Objectives (OKRs) | ✅ Present | Create objectives with managers, assignees, duration |
| Key Results | ✅ Present | Key results with progress type (%, #, currency) |
| Employee Objectives | ✅ Present | Assign objectives to employees with status tracking |
| Employee Key Results | ✅ Present | Per-employee KR with current/target value tracking |
| 360° Feedback | ✅ Present | Multi-source feedback (manager, colleague, subordinate, others) |
| Question Templates | ✅ Present | Custom question types (text, rating, boolean, multi-choice, Likert) |
| Meetings | ✅ Present | Meeting management with question templates |
| Anonymous Feedback | ✅ Present | Anonymous feedback (general, employee, department, job position) |
| Bonus Points | ✅ Present | Configurable bonus points on objective/KR/project completion |
| Periods | ✅ Present | Time periods for OKR cycles |
| Cyclic Feedback | ✅ Present | Recurring/repeating feedback cycles |
| Dashboard | ✅ Present | Performance dashboard |
| Comments | ✅ Present | Comments on objectives with audit log |

### Audit Notes

- **Scheduler:** Cyclic feedback creation runs daily at 8 AM via cron
- **Bonus Points:** Configurable via `BonusPointSetting` with conditions (=, >, <, >=, <=)
- **Integration:** Google Meet links for PMS meetings via `skylinx_meet`
- **Audit:** Objectives, KRs, and feedback have full audit history
- **Multi-tenancy:** Company-scoped
- **Self-progress Update:** Configurable toggle for employee self-progress reporting

---

## 🔷 Module 9: Asset Management (`asset`)

### Features Present

| Feature | Status | Notes |
|---|---|---|
| Asset Categories | ✅ Present | Categorize assets |
| Asset Inventory | ✅ Present | Full asset records with tracking ID, purchase info, expiry |
| Asset Batches/Lots | ✅ Present | Group assets by batch number |
| Asset Allocation | ✅ Present | Assign assets to employees with condition tracking |
| Asset Requests | ✅ Present | Request → Approve → Reject workflow |
| Asset Return | ✅ Present | Return with condition, status, images |
| Asset Reports | ✅ Present | Asset reporting with document attachments |
| Asset Dashboard | ✅ Present | KPI summaries and charts |
| Expiry Notifications | ✅ Present | Notify before asset expiry |
| Auto Mark Expired | ✅ Present | Auto-set expired assets to Not-Available |
| Reassignment | ✅ Present | Reassign assets between employees |
| Quantity Tracking | ✅ Present | Multi-unit asset quantity management |

### Audit Notes

- **Scheduler:** Expiry notifications daily; expired assets marked daily
- **Notifications:** System bot sends asset expiry notifications
- **Multi-tenancy:** Company-scoped via category/assignment
- **Integration:** Document expiry notifications from Document module

---

## 🔷 Module 10: Project & Task Management (`project`)

### Features Present

| Feature | Status | Notes |
|---|---|---|
| Projects | ✅ Present | Projects with managers, members, status, dates |
| Project Stages | ✅ Present | Customizable stage pipeline (Todo, etc.) |
| Tasks | ✅ Present | Tasks with managers, members, status, stages |
| Timesheets | ✅ Present | Time tracking per project/task |
| Dashboard | ✅ Present | Project/Task overview |
| File Attachments | ✅ Present | Project and task file uploads |
| Project/Task Status | ✅ Present | New, in progress, completed, on hold, cancelled, expired |

### Audit Notes

- **Auto-stages:** Default "Todo" stage created on project creation
- **Validation:** Task dates must be within project date range
- **Multi-tenancy:** Company-scoped

---

## 🔷 Module 11: Support / Helpdesk (`helpdesk`)

### Features Present

| Feature | Status | Notes |
|---|---|---|
| Tickets | ✅ Present | Issue tracking with title, description, priority |
| Ticket Types | ✅ Present | Suggestion, complaint, service request, meeting request, etc. |
| Ticket Priorities | ✅ Present | Low, medium, high with star rating |
| Ticket Status | ✅ Present | New, in progress, on hold, resolved, canceled |
| Kanban Pipeline | ✅ Present | Visual ticket pipeline |
| Department Managers | ✅ Present | Assign managers to departments for ticket routing |
| Auto Assignment | ✅ Present | Auto-assign tickets to department/job position via assigning type |
| Claim Requests | ✅ Present | Employees can claim tickets |
| FAQ Categories | ✅ Present | Organized FAQ library |
| FAQs | ✅ Present | Question/answer with tags |
| Ticket Comments | ✅ Present | Comments with file attachments |
| Deadline Tracking | ✅ Present | Due date with visual indicators |
| Dashboard | ✅ Present | KPI summaries, status/priority distribution |

### Audit Notes

- **Multi-tenancy:** Company-scoped via employee work info
- **Deadline Alerts:** Visual indicators (overdue = danger, due today = warning, upcoming = success)

---

## 🔷 Module 12: Reporting / Insights (`report`)

### Features Present

| Feature | Status | Notes |
|---|---|---|
| Recruitment Reports | ✅ Present | Recruitment analytics |
| Employee Reports | ✅ Present | Employee analytics |
| Attendance Reports | ✅ Present | Attendance analytics |
| Leave Reports | ✅ Present | Leave analytics |
| Payroll Reports | ✅ Present | Payroll analytics |
| Asset Reports | ✅ Present | Asset analytics |
| Performance Reports | ✅ Present | Performance analytics |

### Audit Notes

- **Dynamic Modules:** Reports only appear for installed apps
- **Permission-gated:** Each report has separate permission checks

---

## 🔷 Module 13: Dashboards & Analytics (Cross-Module)

### Features Present

| Dashboard | Status | Description |
|---|---|---|
| Main Dashboard | ✅ Present | Company-wide KPI overview |
| Employee Dashboard | ✅ Present | Headcount, gender split, joining trends, birthdays |
| Attendance Dashboard | ✅ Present | KPI summaries, trends, department breakdowns |
| Leave Dashboard | ✅ Present | KPI summaries, monthly trends, utilization rates |
| Payroll Dashboard | ✅ Present | Payroll KPIs |
| Recruitment Dashboard | ✅ Present | Recruitment KPIs |
| Onboarding Dashboard | ✅ Present | Pipeline KPIs |
| Offboarding Dashboard | ✅ Present | Pipeline KPIs |
| Performance Dashboard | ✅ Present | OKR progress |
| Asset Dashboard | ✅ Present | Asset KPIs |
| Helpdesk Dashboard | ✅ Present | Ticket KPIs |
| Project Dashboard | ✅ Present | Project/Task KPIs |
| Dynamic Dashboard Charts | ✅ Present | Per-employee chart visibility control |
| ESS Dashboard | ✅ Present | Employee self-service dashboard |

---

## 🔷 Cross-Cutting & Infrastructure Modules

| Module | Features | Audit Notes |
|---|---|---|
| `skylinx_auth` | Custom `SkylinxUser` model | Extends Django auth; user auto-created for employees |
| `skylinx_audit` | Full audit trail, history tags, tracking config | Uses `django-simple-history` + `django-auditlog`; model-level config |
| `notifications` | In-app notification system | Multi-language (en, ar, de, es, fr); live unread count |
| `skylinx_automations` | Email/notification automation rules | Trigger on create/update/delete; condition-based; multi-channel delivery |
| `skylinx_api` | REST API with Swagger/ReDoc docs | DRF + drf-yasg; JWT auth; 14 endpoint modules |
| `skylinx_theme` | Custom UI theme, color management | Brand-blue theme; custom form/login templates |
| `skylinx_views` | Generic CBV framework, column ordering | Custom list/detail CBV with history tracking |
| `skylinx_widgets` | Custom form widgets | Multi-select, select2-style widgets |
| `skylinx_crumbs` | Breadcrumb navigation | Automatic breadcrumb generation |
| `skylinx_dbtemplate` | Database-backed templates | Dynamic template loading from DB |
| `skylinx_documents` | Document management | Request, upload, approve/reject workflow; expiry tracking |
| `dynamic_fields` | Dynamic custom fields on models | CharField, IntegerField, TextField, DateField, FileField |
| `accessibility` | Feature-level visibility controls | Per-user/per-group accessibility rules |
| `base` | Foundational models & settings | Company, Department, JobPosition, Shifts, Work Types, Holidays, Announcements, Email config, Multiple approvals |

---

## 🔷 Integrations & External Services

### Present Integrations

| Integration | Status | Features |
|---|---|---|
| Biometric Devices | ✅ Present | ZKTeco, Anviz, COSEC, Dahua, e-Time Office — IP-based/API-based attendance fetching |
| Face Detection | ✅ Present | Face recognition for check-in; per-employee face data |
| Geofencing | ✅ Present | GPS-based location validation for attendance check-in |
| WhatsApp Business | ✅ Present | Request flows (leave, shift, asset, attendance, reimbursement, bonus); notifications; announcements |
| Outlook / Microsoft Auth | ✅ Present | OAuth2 email sending via Outlook API |
| Google Meet | ✅ Present | Create/delete Google Meet links; interview & PMS meeting integration |
| LinkedIn | ✅ Present | Post recruitment openings; API token management |
| Google Drive Backup | ✅ Present | Database + media backup to GDrive via service account |
| LDAP/AD | ✅ Present | LDAP authentication; dynamic settings from DB |
| PostgreSQL Backup | ✅ Present | Automated pg_dump backups via cron scheduling |
| Email (SMTP) | ✅ Present | Configurable SMTP servers; per-company email settings |
| Google Cloud Storage | ✅ Present | Media file storage backend (GCP) |
| Notifications (Multi-channel) | ✅ Present | In-app + Email + WhatsApp |

---

## 🔷 Background Scheduled Tasks

| Task | Interval | Module |
|---|---|---|
| Rotate shift assignments | Every 4 hours | `base` |
| Rotate work type assignments | Every 4 hours | `base` |
| Switch scheduled shifts | Every 4 hours | `base` |
| Undo expired shift requests | Every 4 hours | `base` |
| Switch scheduled work types | Every 4 hours | `base` |
| Undo expired work type requests | Every 4 hours | `base` |
| Sync roster shifts | Every 4 hours | `base` |
| Recurring holiday advancement | Every 4 hours | `base` |
| Update employee experience | Every 4 hours | `employee` |
| Disciplinary action block/unblock | Every 60 seconds | `employee` |
| Notify expiring assets | Daily | `asset` |
| Mark expired assets | Daily | `asset` |
| Notify expiring documents | Every 4 hours | `asset` |
| Create daily work records | Every 30 min + daily at 00:30 | `attendance` |
| Leave reset | Every 20 seconds | `leave` |
| Contract expiration | Every 4 hours | `payroll` |
| Auto payslip generation | Every 3 hours | `payroll` |
| Auto-close recruitments | Every hour | `recruitment` |
| Candidate conversion check | Every 5 minutes | `recruitment` |
| Cyclic feedback creation | Daily at 8 AM | `pms` |
| Outlook token refresh | Every 50 minutes | `outlook_auth` |
| Google Drive backup | Configurable interval/cron | `skylinx_backup` |
| PostgreSQL backup | Configurable daily times | `pg_backup` |

---

## 🔷 Permission Model

- **280+ custom permissions** across all modules (calculated from models/views)
- **Role-based:** Superuser, manager, reporting manager, employee levels
- **Granular:** View/create/change/delete per model; custom permissions (e.g., `change_validateattendance`, `archive_recruitment`)
- **Multi-company:** `SkylinxCompanyManager` auto-filters all queries to current company
- **Accessibility Layer:** Custom feature toggles per user/group via `accessibility` app
- **Fail2Ban:** Built-in login brute-force protection via signals + middleware

---

## 🔷 Security Audit Notes

| Aspect | Status | Details |
|---|---|---|
| XSS Protection | ✅ Present | `has_xss()` validation in all CharField/TextField via `clean_fields()` |
| CSRF Protection | ✅ Present | Django CSRF middleware |
| SQL Injection | ✅ Present | Django ORM protection |
| Authentication | ✅ Present | Session-based + JWT API auth |
| LDAP/AD Auth | ✅ Present | Configurable via DB settings |
| Fail2Ban | ✅ Present | Configurable max retry & ban time; session-based IP banning |
| File Upload Validation | ✅ Present | Resume: PDF only; Documents: format & size checks |
| Permission Checks | ✅ Present | `@permission_required` on all views |
| Multi-tenancy Isolation | ✅ Present | `SkylinxCompanyManager` on all models |
| Audit Trail | ✅ Present | All key models track create/update/delete history |
| Secure Media | ✅ Present | Protected media file serving |
| Password Policies | ✅ Present | Django auth framework |

---

## 🔷 Potential Gaps & Observations

### Minor Observations

1. **No unit test runner configured** — Tests exist in most apps but CI pipeline is not visible from project files
2. **Some schedulers use very frequent intervals** — Leave reset runs every 20 seconds which may cause DB load
3. **Comment/notification models spread across modules** — Some duplication in comment handling patterns
4. **`skylinx_backup` local backup code is commented out** — Only GDrive backup is active
5. **Payroll model `__init__.py` is empty** — Model classes are likely in a subdirectory not fully explored
6. **No webhook endpoints visible** — External system integration limited to polling schedulers

### Strengths

1. **Exceptionally comprehensive** — Covers the entire HR employee lifecycle end-to-end
2. **Strong multi-tenancy** — Company isolation is implemented at the ORM level
3. **Excellent audit trail** — Every significant data change is tracked
4. **Multiple communication channels** — Email, in-app, WhatsApp, and Outlook notifications
5. **Flexible configuration** — Most features have settings/settings menus
6. **Scheduled automation** — 23 background tasks handle routine HR operations

---

## 🔷 Codebase Architecture Overview

### Tech Stack

| Layer | Technology |
|---|---|
| **Framework** | Django 5.2 |
| **Database** | PostgreSQL 16 |
| **Cache/Queue** | Redis 7 |
| **Web Server** | Gunicorn + Nginx (production) |
| **Containerization** | Docker / Docker Compose |
| **API** | Django REST Framework + SimpleJWT + drf-yasg |
| **Background Jobs** | APScheduler |
| **Templates** | Django Templates + custom theming engine |
| **Email** | SMTP / Outlook Graph API |
| **Notifications** | django-notifications-hq |
| **Audit Trail** | django-simple-history + django-auditlog |

### Directory Structure

```
├── skylinx/                    # Core Django project config
├── base/                       # Foundational models (Company, Department, Shifts, etc.)
├── employee/                   # Employee profiles, work info, bank details, etc.
├── recruitment/                # Hiring pipeline, candidates, interviews
├── onboarding/                 # New hire onboarding
├── offboarding/                # Exit management
├── attendance/                 # Time tracking, OT, work records
├── leave/                      # Leave types, requests, allocations
├── payroll/                    # Contracts, payslips, allowances, deductions
├── pms/                        # Performance management (OKRs, 360 feedback)
├── asset/                      # Asset management
├── project/                    # Projects, tasks, timesheets
├── helpdesk/                   # Support tickets, FAQs
├── report/                     # Cross-module reporting
├── biometric/                  # Biometric device integration
├── facedetection/              # Face detection for attendance
├── geofencing/                 # GPS-based attendance validation
├── whatsapp/                   # WhatsApp Business integration
├── outlook_auth/               # Microsoft Outlook auth
├── skylinx_meet/               # Google Meet integration
├── skylinx_ldap/               # LDAP/AD authentication
├── skylinx_api/                # REST API with Swagger docs
├── skylinx_audit/              # Audit trail system
├── skylinx_auth/               # Custom user model
├── skylinx_automations/        # Mail/notification automation rules
├── skylinx_backup/             # Google Drive backup
├── skylinx_crumbs/             # Breadcrumb navigation
├── skylinx_dbtemplate/         # Database-backed templates
├── skylinx_documents/          # Document management
├── skylinx_theme/              # UI theme engine
├── skylinx_views/              # Generic CBV framework
├── skylinx_widgets/            # Custom form widgets
├── accessibility/              # Feature visibility controls
├── dynamic_fields/             # Dynamic custom fields
├── notifications/              # In-app notification system
├── pg_backup/                  # PostgreSQL dump backup
├── templates/                  # Global HTML templates
├── static/                     # Static assets (CSS, JS, fonts)
└── load_data/                  # Demo/seed data JSON fixtures
```
