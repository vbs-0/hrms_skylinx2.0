# Skylinx HRMS — Go-Live & Operations Guide

Everything you need to run the platform, onboard your own company, onboard
clients, and walk an HR admin through daily work. Written for the live server
at **https://skylinxhrms.qzz.io**.

---

## 0. Your accounts at a glance

| Role | Who | URL | Login |
|------|-----|-----|-------|
| **Platform Owner** (you) | Skylinx operator — sees ALL companies | https://skylinxhrms.qzz.io/login/ | `skylinx` / *(password sent separately — change on first login)* |
| **Client Admin** | One per client company — locked to their own company | same login page | created per company (you set it during onboarding) |
| **HR / Manager / Employee** | Created by the Client Admin inside each company | same login page | created in-app |

> **Change the owner password after first login** (top-right avatar → profile/security).
> The password above is a starting credential, not a secret to keep forever.

**Golden rule of the demo:** log in as the **Client Admin** to show a client
their company. Only use the `skylinx` owner account for platform admin
(onboarding companies, managing plans). The owner sees *every* company by
design — that's not a bug, it's the operator view.

---

## 1. The mental model (how isolation works)

- **One database, many companies.** Each client = one `Company` row (a tenant).
- **Non-superusers are hard-locked to their own company.** A client admin or
  employee can only ever see/manage their own company's data. They cannot
  switch companies or see others. (Enforced in `base/middleware.py`.)
- **The owner (superuser `skylinx`) sees everything** and has the company
  switcher ("All companies"). This is the platform/operator view.
- **Shared starter config** (default leave types, payroll components) is visible
  to all tenants as a starting point; each company edits its own copy going
  forward.

---

## 2. First-time platform setup (do once, in order)

### 2.1 Log in as owner
Go to https://skylinxhrms.qzz.io/login/ → `skylinx` / `Skyl1nx@Owner#2026`.

### 2.2 Configure a mail server (REQUIRED for welcome emails to actually send)
No SMTP is configured yet, so onboarding emails are created but **not delivered**
until you set this up.
- Go to **Settings → Mail Server Configuration** (or `/settings/mail-server-conf/`).
- Add your SMTP host/port/username/password and a default "from" address
  (e.g. a Gmail App Password, or your transactional provider — SendGrid/SES).
- Send a test. Once this works, welcome emails + all automations deliver.

> Until SMTP is set, everything else still works — users just won't receive
> mail. You can hand credentials to clients directly instead.

### 2.3 Review subscription plans (already seeded)
Go to the **Owner Console → `/subscriptions/`**. Four plans exist:

| Plan | Seats | Paid modules unlocked |
|------|-------|------------------------|
| **Free** | 5 | none (core only: employee, attendance, leave, dashboard) |
| **Starter** | 25 | Payroll, Recruitment |
| **Pro** | 100 | Payroll, Recruitment, Performance (PMS), Asset, Helpdesk |
| **Enterprise** | unlimited | all 7: Payroll, Recruitment, PMS, Project, Asset, Helpdesk, Biometric |

Core modules (Employee, Attendance basics, Leave, Dashboard, Settings) are
**always available** on every plan. Anything not in the plan is hidden from the
sidebar and blocked by URL. You can edit plan prices/seats/features in the
console.

---

## 3. Onboard a company (your Skylinx company first, then each client)

This single flow creates the company, its admin login, its default roles, and
its subscription — and emails a welcome link.

1. As owner, go to **`/subscriptions/onboard/`** (Owner Console → "Onboard").
2. Fill the form:
   - **Company name** — e.g. `Skylinx` (do yours first), then `ClientCorp` later.
   - **Admin username** — the client admin's login (e.g. `skylinx_admin`).
   - **Admin email** — real email (welcome link goes here once SMTP is set).
   - **Password** — initial password for that admin (they can change it).
   - **Plan** — pick from the table above (Enterprise for your own demo company;
     for clients, match what they paid for). The trial length comes from the plan.
3. Submit. Behind the scenes this:
   - creates the `Company`,
   - creates the admin **as a non-superuser, non-staff user locked to that company**,
   - puts them in the **Company Admin** group (full management of their company),
   - auto-creates the company's **HR Manager / Manager / Employee** roles,
   - creates a **trial Subscription** on the chosen plan,
   - sends the **welcome email** (once SMTP is configured).

**Repeat step 3 for each client.** Hand each client their admin username +
password. They log in at the same URL and only see their own company.

### 3.1 Add your company logo (fixes the sidebar logo)
For each company: **Settings → Company** → edit → upload an icon/logo. If a
company has no logo, the sidebar now shows the Skylinx brand mark instead of a
broken image (so it's never broken), but uploading the real logo is best.

---

## 4. What each role can do (permissions in detail)

Every company automatically gets these **four** roles. Names are stored
per-tenant (`c<id>::Label`) so companies never share or see each other's groups.

### Company Admin  *(the login you create at onboarding)*
- Full **add / change / delete / view** across: Employee, Attendance, Leave,
  Payroll, Recruitment, Performance (PMS), Asset, Project, Helpdesk, Biometric, Base (settings).
- Can **manage user groups & permissions** for their company (create roles,
  assign permissions, add/remove members).
- **Cannot** see other companies. **Not** a Django superuser, **not** staff
  (so no `/admin/` backdoor — that's deliberate, it would leak other tenants).
- This is the person who runs the company day-to-day and creates HR/Manager/Employee users.

### HR Manager
- Broad HR access (view/add/change/delete) across the daily-use apps: Employee,
  Attendance, Leave, Payroll, Recruitment, PMS, Asset, Project, Helpdesk, Biometric.
- Use this for your HR staff who run leave, payroll, attendance, hiring.

### Manager  *(team lead)*
- **View** employees.
- **Approve / edit / add** Attendance.
- **Approve / edit / add** Leave requests; view leave allocation requests.
- Approve Work Type and Shift requests.
- No payroll, no settings. For team leads who approve their team's day-to-day.

### Employee  *(individual contributor)*
- View & edit **own profile**.
- **Apply for leave** + view own leave.
- View own attendance.
- Raise Work Type / Shift change requests.
- Nothing else — cannot see other employees' data.

> To customise: Company Admin goes to **Settings → User Groups**, picks a role,
> and ticks/unticks permissions. Each company edits its own copy.

---

## 5. HR walkthrough — set up a company for real use

Do this **in order** inside a company (as Company Admin or HR Manager). Later
steps depend on earlier ones existing.

### 5.1 Foundations (Settings → Base)
Create these first — everything else references them:
1. **Departments** (e.g. Engineering, Sales, HR).
2. **Job Positions** (e.g. Software Engineer) — each belongs to a Department.
3. **Job Roles** (optional, finer than position).
4. **Company details + logo** (Settings → Company).

### 5.2 Work structure
1. **Shifts** (Settings → Employee → Employee Shift) — e.g. Morning 9–6,
   with grace time. *(Note: Holiday Calendar is its own module now, in the
   bottom sidebar — not under Leave.)*
2. **Work Types** (e.g. WFO, WFH, Hybrid).
3. **Employee Types** (Permanent, Contract, Intern).

### 5.3 Add employees
**Employee module → Employees → Create** (or **+**). Required fields:
- Personal: first/last name, email (unique), phone.
- **Work Info** (this is what assigns them to the company): Department, Job
  Position, Shift, Work Type, Employee Type, Reporting Manager, **Company**,
  Date of Joining, **Probation Period (Days)**, **CTC** + salary breakdown
  (Basic/HRA/Other %, must total 100%).
- Optionally a login: tick to create a user account so they can log in; assign
  them to the **Employee** (or **Manager**) role.

> **Bulk add:** Employee module → Import (download the template, fill, upload).
> Seats are limited by the plan — if a client hits their seat cap, upgrade the
> plan in the Owner Console.

### 5.4 Leave setup (Leave module)
1. **Leave Types** — name, paid/unpaid, number of days, carry-forward rules,
   whether it counts holidays as working days.
2. **Assign Leave Type** — assign a leave type to employees/departments so they
   have a balance to apply against.
3. **Company Leaves** — define weekend days (which weekdays are non-working).
4. **Restrict Leaves** — block leave on specific dates if needed.
5. Employees then **Apply Leave**; Managers/HR **approve** under Leave Approval.
   - Note: employees on **probation** are blocked from casual leave (by design).

### 5.5 Holiday Calendar (its own module, bottom sidebar)
- Add holidays (name, start/end date, **mandatory vs optional**).
- Mandatory holidays are excluded from leave working-day counts; optional ones
  count as working days. Colours on the calendar distinguish them.

### 5.6 Attendance (Attendance module)
1. **Attendance settings** — define how attendance is captured.
2. Employees clock in/out (the timer in the top bar), or import attendance.
3. Managers/HR validate attendance under the Attendance views.
4. (Biometric/Face attendance only if the plan includes the Biometric feature.)

### 5.7 Payroll (Payroll module — requires a plan with Payroll)
Set up in order:
1. **Allowances** (e.g. HRA, travel) and **Deductions** (e.g. PF, tax).
2. **Filing Status / tax setup** (India tax regimes are seedable).
3. **Contracts** — each employee needs a contract (wage, pay frequency) for
   payroll to calculate. CTC + the Basic/HRA/Other % from their work info feed
   the breakdown.
4. **Generate Payslips** for a pay period → review → approve → (email/download).

### 5.8 Expenses / Reimbursements
- Employees raise reimbursement claims (single unified claims section, with
  categories like travel, food, etc.).
- HR/Manager reviews and approves; approved claims can flow into payroll.

### 5.9 Email automations (optional)
- **Settings → Mail Automations** lets you auto-send templated emails on events
  (e.g. "on create" of a leave request).
- **Important:** an automation only fires when its **Condition** evaluates true.
  Leave the default condition (e.g. `Is active == on`) in place — removing the
  condition table entirely disables the automation. (This is why we did *not*
  remove that table.)

---

## 6. Adding more users later

- **New employee (no login):** Employee → Create, fill work info.
- **New employee WITH login:** same, but tick "create user account" and assign a
  role (Employee / Manager / HR Manager).
- **New HR/manager:** create the employee, then **Settings → User Groups** → add
  them to HR Manager or Manager.
- **New client company:** owner runs the onboarding flow again (Section 3).

---

## 7. Post-demo hardening (do soon, NOT mid-demo)

These improve security but can break a live site if done carelessly — do them
in a quiet window, not minutes before a demo.

1. **Turn off debug.** In `/home/ubuntu/hrms/hrms_skylinx2.0/.env` set
   `DEBUG=False`. Before restarting, confirm:
   - `ALLOWED_HOSTS` includes `skylinxhrms.qzz.io` (already added), and
   - nginx serves `/static/` (with DEBUG off Django won't serve static itself).
   Then `sudo systemctl restart hrms-client`. If CSS disappears, nginx isn't
   serving static — revert `DEBUG=True` and fix nginx static first.
2. **HTTPS.** Add a TLS cert (Let's Encrypt) and an nginx `server_name` for the
   domain (currently only the IP). Then everything is `https://`.
3. **Per-tenant config isolation** (optional): currently default leave types /
   payroll components are shared across tenants as starters. If a client must
   have *fully* separate config, that's a follow-up data migration.
4. **Cross-company notification scoping** (optional follow-up): event emails
   currently can notify across companies in some flows; tighten when you have time.

---

## 8. Quick reference — server

```bash
# SSH
ssh skylinx        # ubuntu@129.159.226.101

# App: /home/ubuntu/hrms/hrms_skylinx2.0  (branch tag: 1.0.2.beta.prod)
# DB:  Postgres 16 in docker container "skylinx-pg", db "skylinx"

# restart
sudo systemctl restart hrms-client hrms-scheduler

# logs
sudo journalctl -u hrms-client -n 100 --no-pager

# run a management command
cd /home/ubuntu/hrms/hrms_skylinx2.0
sudo venv/bin/python manage.py <command>
```

Deployed code: tag **`1.0.2.beta.prod`** (branch `v1.0.2.beta`).
