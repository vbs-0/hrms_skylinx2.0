# Pending — gaps & implementation debt

Ranked. ✅ built · 🟡 partial · ❌ missing. The *engine* (RBAC, subscriptions,
billing core, mobile app) is mostly there. What's missing is the **glue that
makes a client self-sufficient** and the **safety net that lets us sleep**.

## ✅ Done this session
- **Currency default ₹** — fixed `$` fallback in `payroll/models/models.py` (3 spots) so new tenants without a `PayrollSettings` row show ₹, not $.
- **#8 backups** — `scripts/backup_db.sh` (pg_dump + media tar, 14-day rotation). *Action left: add the cron line on the server.*
- **#12 deploy** — `scripts/deploy.sh` (safety-backup → pull → migrate → collectstatic → restart).
- **#5 Razorpay webhook** — `billing.verify_webhook` + `razorpay_webhook` view + `pay/webhook/` route; activates plan server-side from receipt. *Action left: set `RAZORPAY_WEBHOOK_SECRET` + register the `order.paid` webhook in Razorpay.*
- **#7 trial-ending warning** — in-app banner (≤7 days, red at ≤2) in `index.html` + `notify_trial_ending` command (7/3/1-day emails). *Email half needs #3 SMTP.*
- **#30 multi-admin / account recovery** — `company_admins` view + `admins.html` + `subscription-admins` route + profile-menu link; promote/revoke admin within a company, blocks removing the last admin.
- **#3 SMTP wired + VERIFIED** — added `EMAIL_*` settings (read `SMTP_*` from `.env`) in `skylinx/settings/base.py`; creds in `.env`; **real test email sent OK** (Gmail 587/TLS). Unblocks #7 email, #2 invites, password reset, #20 verification.
- **Verification pass (Round 8)** — confirmed #61 (✅ regularization), #62 (✅ onboarding tasks/managers), #63 (🟢 FnF stage exists), #67 (❌ probation workflow real gap), #69 (🟡 mobile reimbursement read-only), #71 (🟡 deadline exists, escalation missing).

## Critical (survival / money)

| # | Gap | State | Where / what's needed |
|---|---|---|---|
| 8 | **🔴 Nightly DB backup** — no pg_dump, no offsite. One VM, one Postgres. Corruption/VM loss = all clients' data gone. | ❌ | `pg_dump` cron on server. Do first — zero code risk, no keys. |
| 5 | **Razorpay webhook** — we confirm payment on browser redirect, not server-side. Close the tab after paying → plan may not activate. Money bug. | ❌ | New endpoint; verify webhook signature; activate plan even if browser closes. |
| 4 | **Invoices / receipts / billing history** — payment flips to 'active' with no record. Clients need GST bills. | ❌ | After `pay_verify()`; Invoice model or on-the-fly PDF. |

## High (client can't self-onboard)

| # | Gap | State | Where / what's needed |
|---|---|---|---|
| 1 | **Onboarding wizard** — after signup we drop into an empty app. No guide to create departments → HR → employees. | ❌ | New flow after `signup()` in `subscriptions/views.py`; redirect to a setup checklist, not `/`. |
| 2 | **Invite employees by email** — admin creates employee, then manually tells them the login. Embarrassing. | ❌ | New view + token; reuse `create_user`; depends on #3. |
| 3 | **SMTP actually configured** — reset/welcome mail sends nowhere; no mail server plugged in. | 🟡 | `DynamicEmailConfiguration` exists; needs creds + a platform default. |
| 7 | **Trial-ending + suspension emails + in-app banner** — app just stops one morning, no warning. | ❌ | Hook into `expire_subscriptions` command + a banner partial. |

## Medium (polish / expected of a real SaaS)

| # | Gap | State | Where / what's needed |
|---|---|---|---|
| 6 | **Friendly Roles screen** — RBAC works but UI is the raw Django permission picker. | 🟡 | Engine done (`base/rbac.py`); needs simple UI + preset roles (HR/Manager/Employee). |
| 9 | **Self-serve cancel / downgrade** — upgrade works, cancel/downgrade needs emailing us. | 🟡 | `choose_plan()` handles upgrade; add cancel/downgrade paths. |
| 10 | **Company branding** — company name yes, logo/colors on login + app, no. Clients ask day one. | 🟡 | Company model + template hooks. |
| 11 | **Landing + public pricing page** — `plans.html` is logged-in only. | 🟡 | Public pricing page. |
| 12 | **Deploy script + staging** — updates are manual scp/restart; no staging, no rollback. | ❌ | `deploy.sh` (git pull → migrate → collectstatic → restart). Server is already a git repo. |

## Suggested smallest-set order

**#8 backups** (survival) → **#3 + #2 email/invites** (clients onboard staff) →
**#5 webhook** (don't lose payments) → **#1 wizard** (first impression). Rest is polish.

## Round 2 — surfaced once a client actually uses it daily

| # | Gap | State | Where / what's needed |
|---|---|---|---|
| 13 | ~~Bulk employee import~~ — **ALREADY BUILT.** | ✅ | `employee-import/`, `work-info-import/` (employee/urls.py:243). |
| 14 | **Indian payroll** — PF/ESI/PT statutory deductions **built** (`seed_india_deductions`, `payslip_calc`). Remaining: **bank-transfer file export** + TDS slabs. | 🟡 | Salary + PF/ESI/PT done; add bank file (NEFT/CSV) export. |
| 15 | ~~Holiday calendar + shift/roster~~ — **ALREADY BUILT.** | ✅ | `base/cbv/holidays.py`, `employee_shift`, `rotating_shift`, `roster`. |
| 16 | **Audit log** — who changed what/when (esp. salary, roles, leave). Compliance need. | ❌ | Audit trail on sensitive models. |
| 17 | **Mobile push notifications** — app only shows notifications when opened; approvals feel dead. | ❌ | FCM token register + push on approval/events. |
| 17a | **HR/admin event notifications** — admin/HR should get a notification (app + push) when an employee logs in, clocks in/out, applies leave, etc. **Each type toggleable in settings** (what fires, what doesn't, who receives). | ❌ | Notification-preferences model per role/user; emit on key events; respect toggles. Builds on #17. |
| 3a | **More default mail-automation templates** — template infra exists (`mail_template.py`), but ship sensible defaults (welcome, invite, leave approved/rejected, payslip ready, trial-ending, password reset, etc.). | 🟡 | Seed a set of default `MailTemplate` rows; wire to events. |
| 18 | **Data export + "delete my company"** — clients should take/erase their data. | ❌ | Per-tenant export (zip/CSV) + cascade delete. Ties to #25. |
| 19 | **Security hardening** — no 2FA, no login rate-limit, no session controls. | ❌ | 2FA for admins; throttle login; session settings. |
| 20 | **Signup abuse protection** — no rate-limit / email verify / captcha; spam companies possible. | ❌ | Rate-limit + email verification (overlaps #3). |
| 21 | **Reports & exports** (headcount, attrition, leave trends → PDF/Excel) — HR lives in reports. | 🟡 | Dashboard has live KPIs only; add report pages + exports. |
| 22 | **Timezone / locale / currency per company** — single-assumption today. | 🟡 | Per-company tz, date format, payroll currency. |
| 23 | **Uptime monitoring + error tracking + status page** — we find out it's down from clients. | ❌ | Health check + alerting (e.g. Sentry/uptime ping) + public status. |
| 24 | **In-app help / support / docs / tickets — tiered by role.** Company admin controls who sees what: **admin + HR get our (vendor) support contact**; **employees get FAQ + raise tickets that HR resolves** (internal helpdesk), not our contact. | ❌ | Help widget with role-based content; vendor-contact for admin/HR; employee→HR ticket flow (helpdesk app may already cover part). |
| 25 | **Terms of Service + Privacy Policy** — table stakes for paid SaaS holding PII. | ❌ | Static pages + signup consent checkbox. |
| 26 | **Concurrency / last-write-wins** — two HRs editing same record silently clobber. | 🟡 | Optimistic locking on sensitive edits. Minor. |
| 27 | **Scale / performance** — single server, no caching, no load test, no read replica. | 🟡 | Fine now; caching + monitoring + capacity plan before ~2k+ employees. |

## Round 3 — senior-engineer catches (not client-facing)

| # | Gap | State | Where / what's needed |
|---|---|---|---|
| 28 | **Multi-tenant data-leak test suite** — we isolate by company in code, but nothing *proves* company A can never read company B's data via any view/API. One leak = reputation over. | ❌ | Dedicated test pass: for each endpoint/API, assert cross-company access 403s/empty. |
| 29 | **`referance hrms` / `referance code` folders in tree** — dead weight (already excluded on push). | 🟡 | Add to `.gitignore`; remove from working tree. |

## Round 4 — deeper operational / lifecycle gaps

| # | Gap | State | Where / what's needed |
|---|---|---|---|
| 30 | **Account recovery / transfer ownership / multiple owners** — if the lone admin leaves or loses access, the tenant is bricked; only we can fix it manually. → **DECIDED: fix it.** | ❌ | **Options (recommend A+C):** **A** allow ≥2 owner-admins + "promote to admin" button (trivial, covers most cases). **B** "transfer ownership" action in client settings. **C** self-recovery via verified email (needs #3; reset flow already exists). **Vendor fallback:** impersonate (built) → we reset — document it. |
| 31 | **No task queue** — payroll/bulk-import/mail-blast run in raw threads; big runs time out, restart mid-run = lost, no retry. | ❌ | Lightweight queue (django-q/RQ) or chunked jobs; retry + progress. |
| 32 | **Uploaded files: no per-plan quota, no offsite backup** — docs/ID proofs sit on the one VM disk; #8 backs up DB not files; disk fills silently. → **DECIDED: per-client GB quota, dynamically changeable, linked to subscription/plan.** | ❌ | Add `storage_limit_gb` to Plan (+ per-company override); enforce on upload; show usage bar. Plus file backup (S3 or rsync). |
| 33 | **E-signature / acknowledgement tracking** — offers & policy sign-off are upload-a-scan only. | ❌ | Sign/acknowledge flow + audit (ties to #16). |
| 34 | **Mobile offline mode** — no network, no attendance punch (bad-wifi sites). | ❌ | Queue-and-sync punches locally. |
| 35 | **Biometric device sync** — `biometric` app exists (hook present); per-tenant device sync (ZKTeco-style) reliability unverified. | 🟡 | Verify + harden device→attendance sync. |
| 36 | **Mobile release pipeline + forced-update gate** — old app vs new API breaks silently. | ❌ | Min-version check → "please update" screen; store release process. |
| 37 | **Historical data migration** — import covers employees, not 3 yrs of attendance/leave/payroll history when switching from another HRMS. | ❌ | Import flows for historical records. |
| 38 | **Billing is Razorpay/INR only** → **DECIDED: India-only is fine for now; currency symbol swappable later.** GST invoice from us still wanted (see #4). | 🟢 | Deferred. Just keep symbol configurable. |
| 39 | **Dunning** — failed renewal = sudden lockout; no retry + "payment failed" emails + grace period. | ❌ | Retry schedule, grace window, notify (ties to #5/#7). |
| 40 | **Coupons / referral / promo codes** — sales can't honor a discount without manual edits. | ❌ | Discount codes on checkout. |
| 41 | **Internal seed/demo script** → **DECIDED: NOT self-serve.** We demo to clients hands-on personally. Want one **internal-only** command that populates a full realistic company — employees, departments, **assigning heads/managers**, attendance, leave, payroll — for live demos. | 🟡 | Extend `load_demo_data` to build a complete org with reporting hierarchy. Internal command only; never exposed to clients. |
| 42 | **Email deliverability (SPF/DKIM/DMARC + sending domain)** — beyond SMTP (#3), mail lands in spam; invites missed. | ❌ | Configure sending domain + auth records. |
| 43 | **Notification digest / frequency control** — all-or-nothing per event; noisy. | ❌ | Per-user digest + frequency (builds on #17a). |
| 44 | **Data-retention / auto-purge policy** — ex-employee PII kept forever = compliance liability. | ❌ | Configurable retention + auto-anonymize/purge (ties to #18/#25). |

> Note: **helpdesk**, **recruitment (with public job postings)** apps exist — so #24's employee→HR ticket half and a careers page are partly there; verify before building.

## Round 5 — compliance & legal (India-focused)

| # | Gap | State | Where / what's needed |
|---|---|---|---|
| 45 | **Consent + cookie/privacy banner (DPDP Act)** — collecting employee PII with no recorded consent. | ❌ | Consent capture at signup/onboard + banner. Ties #25. |
| 46 | **Right-to-erasure request flow** — employee/company can demand data deletion. | ❌ | Request → review → purge (ties #18/#44). |
| 47 | **Region-configurable leave/labor policies** — accrual, carry-forward, encashment, comp-off rules vary by state/company. | 🟡 | Verify leave-policy config depth; make rules per-company. |
| 48 | **Statutory payroll outputs** — Form 16, PF ECR/challan, ESI returns export. | ❌ | Generators for the standard filings (extends #14). |

## Round 6 — integrations & ecosystem

| # | Gap | State | Where / what's needed |
|---|---|---|---|
| 49 | **Calendar sync** (Google/Outlook) — leave, holidays, interview slots. | ❌ | iCal feed (cheap) or OAuth sync. |
| 50 | **Slack / Teams notifications** — approvals/announcements where teams already are. | ❌ | Incoming-webhook out. |
| 51 | **SSO / Google login** for employees — fewer passwords, easier adoption. | ❌ | OAuth login option. |
| 52 | **Accounting export** (Tally/Zoho Books) for payroll journals. | ❌ | Export format for the common IN accounting tools. |
| 53 | **Public REST API + API keys** — clients integrate their own tools (we have `skylinx_api` internally; not exposed/keyed for clients). | 🟡 | Per-tenant API keys + scoped, rate-limited public API. |
| 54 | **Outbound webhooks** — client subscribes to events (new hire, payslip ready). | ❌ | Event → client URL delivery (ponytail: reuse #5 webhook plumbing). |

## Round 7 — internal / vendor ops tooling

| # | Gap | State | Where / what's needed |
|---|---|---|---|
| 55 | **Vendor metrics dashboard** — MRR, churn, active tenants, trials converting. We're flying blind on the business. | ❌ | Aggregate over Subscription/Company in the owner console. |
| 56 | **Per-tenant feature flags / staged rollout** — ship risky changes to one tenant first (no staging = #12). | ❌ | Simple flag table keyed by company. |
| 57 | **Vendor-side audit log** — who on OUR team impersonated/edited which tenant. Trust + accountability. | ❌ | Log impersonation + admin actions (extends #16). |
| 58 | **No-code plan/feature editor** — edit plans/features without touching code (partly via Django admin today). | 🟡 | Owner-console plan editor. |
| 59 | **Broadcast to all tenants** — announce maintenance/new features in-app + email. | ❌ | Platform announcement → all companies. |
| 60 | **Internal health/status dashboard** — services up, queue depth, disk, last backup. | ❌ | Ties #8/#23/#31; one ops page. |

## Round 8 — workflow & lifecycle (month 2–3 of real use)

Several of these touch apps that already exist (attendance, onboarding,
offboarding, helpdesk, recruitment, payroll-reimbursement) — marked 🟡 verify
because the module is there but the specific flow may be thin/missing.

| # | Gap | State | Where / what's needed |
|---|---|---|---|
| 61 | ~~Attendance regularization~~ — **VERIFIED BUILT.** Request/correction flow exists. | ✅ | `attendance/views/requests.py`. |
| 62 | ~~Onboarding checklist auto-assign~~ — **VERIFIED BUILT.** Stages have "Stage Managers" (M2M) + `OnboardingTask`. | ✅ | `onboarding/models.py` (OnboardingStage, OnboardingTask). |
| 63 | **Offboarding F&F** — **mostly built**: literal `fnf` "FnF Settlement" stage type + task-based exit stages exist. Only deep payroll-integrated settlement *calculation* may be thin. | 🟢 | `offboarding/models.py`. Verify settlement math if needed. |
| 64 | **Manager "my team" dashboard** — managers see only their team's leave/attendance/reviews, not all of HR's screens. | ❌ | Scoped manager home. |
| 65 | **Branch / department-scoped admin** — RBAC isolates by company, not by branch within a company (Mumbai-HR sees Delhi staff). | ❌ | Sub-company scoping in RBAC. |
| 66 | **Document-expiry tracking + reminders** — visa/contract/cert expiry alerts. | ❌ | Expiry dates on docs + reminder job. |
| 67 | **Probation/confirmation workflow** — **VERIFIED gap**: only a probation *filter* exists (`employee/filters.py`), no confirm/extend workflow + reminder. | ❌ | Build confirmation workflow + reminder (minor). |
| 68 | **Celebrations feed/nudges** — birthdays, work anniversaries to the team. | 🟡 | Minor; auto-notify probably missing. |
| 69 | **Mobile expense claim w/ receipt photo** — **VERIFIED partial**: mobile has a read-only Reimbursement list (`/payroll/reimbusement/`), no claim-creation + photo capture. | 🟡 | Add mobile create flow + receipt photo (web reimbursement exists). |
| 70 | **Headcount/position budgeting** — sanctioned vs filled, cost per department. | ❌ | Budget view over recruitment + payroll. |
| 71 | **Helpdesk SLA + escalation** — **VERIFIED partial**: tickets have `priority` + `deadline` + "Overdue by N days" color-coded display. Missing: auto-escalation/notify on breach. | 🟡 | Add SLA-breach escalation/notification on top of existing deadline. |
| 72 | **Field-level sensitive-data visibility** — restrict who sees salary/PAN/bank beyond module perms. | ❌ | Field-level masking by role. |
| 73 | **Mobile app localization** — web has i18n; app has no language switch (Hindi etc.). | ❌ | Localize Flutter app + in-app switch. |

# ───────────────────────── FUTURE IMPLEMENTATION ─────────────────────────
_Parked for later. Not part of the current build pass._

## UX / usability debt (HR daily-use friction — separate from feature gaps)

> **Future:** before fixing, do a live navigation pass as an HR user on the
> running server to turn U1–U12 into a precise per-screen punch-list.

The product is built for HR, but assembled as 15 apps each with its own sidebar +
permission-gated settings. That structure breeds scattered actions, hidden
features, and inconsistent layouts. These are interaction blunders, not missing
features — they make HR's day slower even when the feature exists.

| # | Friction | Fix |
|---|---|---|
| U1 | **Nav label ≠ destination** — "Employee" lands on a dashboard, not the people list. | Menu noun → that noun's primary list view. Keep dashboards under a separate "Home". |
| U2 | **No approvals inbox** — approving leave is ~5 clicks × many/day, one at a time. | One queue screen, inline Approve/Reject, **bulk approve**. HR's #1 job = 1 click. |
| U3 | **Add-employee is a 40-field wall** — required fields unclear, no draft. | Stepped wizard (basic → work → docs), mark required, save-as-draft. (Overlaps #1.) |
| U4 | **Settings split & inconsistent** — config scattered across 15 per-app menus + a global gear, all perm-gated. | Consolidate; surface daily config near where it's used. |
| U5 | **Inverted action hierarchy** — daily action hidden in ⋮→row→tab; rare action is the big button. | Frequency drives prominence; destructive tucked away. |
| U6 | **Permission-hidden with no hint** — feature simply vanishes; HR assumes it's missing, emails support. | Show "no access — ask your admin" instead of nothing. |
| U7 | **State doesn't persist** — filters/search/scroll reset on navigate (htmx reloads). | Preserve filter/search/scroll across navigation. |
| U8 | **No global search** — can't jump to a person by name from anywhere. | Global people search in the top bar. |
| U9 | **Weak action feedback** — after approve/save, nothing visibly changes; was it saved? | Clear toast + row-state change + undo where cheap. |
| U10 | **Dashboard = vanity charts, not a to-do** — HR opens to charts, not "who needs me". | Home = action list (approvals, joiners, expiring docs); charts secondary. |
| U11 | **Inconsistent layout across modules** — Add/filter/toolbar in different places per app. | One list-view template language: same toolbar, Add corner, filter bar everywhere. |
| U12 | **Confirm/undo applied unevenly** — nags on harmless actions, silent on destructive ones. | Guard destructive+irreversible (delete employee, finalize payroll); drop the rest. |

> These overlap each other and #1 (wizard). Biggest single win for HR: **U2 approvals inbox + U10 action-list home** — turns "hunt for what needs me" into "it's the first thing I see".

---
_Last updated: 2026-06-21. Append new gaps below as the brainstorm continues._
