# Skylinx HRMS — Licensing, Feature Locking & Business Model

> Planning / research document. Captures the agreed model for selling the
> self-hosted HRMS with per-company licensing, seat limits, and remotely
> controlled premium features. Not yet implemented — this is the design spec.

---

## 1. Business model

- **Product is sold, not hosted.** Customers (small companies) receive the
  backend + frontend code and **host it on their own server + database**.
- **One license per company.** No per-employee accounts to manage on our side —
  only the company-level seat count matters.
- **Two independent commercial dimensions**, both controlled remotely by us:
  1. **Seats** — max number of *active* employees the company may have.
  2. **Features** — which premium modules are switched on (tiers / upsell).
- **Recurring value = the premium features + seat upgrades.** A company can buy
  more seats or add a feature at any time; we change it from our dashboard and
  it takes effect on their install at the next sync — **nothing is re-shipped**.

### Seat counting rule
- Count = `Employee.objects.filter(is_active=True).count()`.
- **Disabled / terminated employees (`is_active=False`) do NOT count** — so
  companies save money by deactivating leavers. This is intentional and a
  selling point.

---

## 2. The hard truth (why this is "deterrence", not "DRM")

The customer has **all the source code** and **hosts their own database**.
Therefore:

- Any purely local check (`if not licensed: block`) can be edited out by a
  determined admin in minutes — Python is readable source.
- Our license server has **zero access to their database**. We only ever know
  **what their app chooses to report**.

So the goal is **not** a perfect technical lock (impossible with shipped
source). The goal is to make bypassing **more expensive / riskier than paying**,
using a combination of:

1. **Cryptographic signing** (kills fake-server / forged-license attacks).
2. **Server-side features** (the actual lock — compute happens on *our* hardware).
3. **Legal contract / EULA** (the backstop for B2B customers).
4. **Optional code obfuscation** (raises the effort of editing the check out).

---

## 3. The license object (signed)

The license is a blob **signed with our private key**. It carries both
commercial dimensions plus anti-replay/expiry metadata:

```json
{
  "company_id": "acme-001",
  "seats": 50,
  "features": ["geofencing", "payroll", "whatsapp", "facedetection"],
  "expiry": "2026-12-31",
  "issued_at": "2026-06-17",
  "nonce": "<per-request random value>"
}
```

- **seats** — dimension 1. Default set when we issue the key; raised remotely
  when the customer pays for more.
- **features** — dimension 2. Toggled remotely; enables tiers (Basic/Pro) and
  single-feature upsell.
- Both are **server-controlled and signed** → the customer cannot edit either,
  and a dummy server cannot forge either.

---

## 4. Why the "fake server / dummy API" attack fails

Attack: *"I'll just repoint the app at my own server that returns
`{valid: true, seats: 999999}` for everything."*

**Defeated by asymmetric signing:**

- We generate a keypair: **private key** (stays on our server, never shipped) +
  **public key** (baked into the HRMS code).
- Every meaningful response (license, auth, seat/feature values) is **signed
  with our private key**.
- The app **verifies the signature with the public key** before trusting any
  field.

```
Attacker repoints app -> http://dummy-server/
Dummy returns:  { valid: true, seats: 999999 }
App checks:     signed by Skylinx private key?  -> NO
App rejects:    "Invalid license."  -> locks
```

The dummy server has no private key, so it can't produce a response the app
accepts. **The URL becomes irrelevant** — even a MITM can't sign.

### Replay / license-sharing attack
*"I'll record one real valid response and replay it forever / on other installs."*

Defeated by **challenge-response nonce**:

```
App  -> server:  random nonce N (+ company_id)
server -> app:   sign({ valid, seats, features, expiry, nonce: N })
App:             verify signature AND returned nonce == N AND company_id matches
```

Old/replayed responses carry the wrong nonce -> rejected. Binding `company_id`
(+ optional machine fingerprint) into the signed payload stops sharing one
company's blob across installs.

### The one thing signing can NOT stop
They have the source, so they can **edit the client to skip the signature check
entirely**. No cryptography stops someone editing code that runs on their own
machine. This is the unsolvable core — mitigated (not eliminated) by:
- **Server-side features** (see §5) — immune even to this, because the compute
  isn't in the shipped code.
- **Cython-compiling** the `licensing` module so the check isn't editable source.
- **EULA** — legal deterrence for real companies.

---

## 5. Server-side features = the real lock (immune to all client edits)

For premium features, the **actual work runs on our server**, with logic that
is **not in the shipped code**. A patched client or dummy server still can't
produce the output — only our server can.

Example (auto-payroll): to generate payslips the app must send the employee list
to our `/payroll/render` endpoint. We render the PDF. If they kill the license,
no payslips — there is nothing local to "unlock", and a dummy server can't
render them because it doesn't have the payroll engine.

This also gives us a **trustworthy seat count** (see §6): we count the real
distinct employees in the payroll run ourselves.

---

## 6. Three truth layers for the real seat count

Our server cannot read their DB, so the real count comes from feature usage that
*has to pass through us*:

1. **Login-token issuance (primary, real-time).**
   On employee login the app calls `POST /auth/issue { company_id, employee_id,
   is_active }`. We keep a **rolling 30-day set of distinct active employee IDs**
   per company — its size is the real seat count, measured by us.
   - Enforcement: a *new* employee logging in when the set is already at `seats`
     -> **denied**. Existing employees always allowed.
   - Disabled employees never request tokens and age out of the 30-day window ->
     they stop counting automatically.

2. **Heartbeat (daily — liveness + control channel).**
   `POST /heartbeat { company_id, reported_active_count, version }` returns the
   fresh signed `{ valid, seats, features, expiry, state }`. This is how
   **remote seat increases / feature toggles / revocation reach the client**.

3. **Payroll run (monthly audit cross-check).**
   We record distinct employees paid. Now three numbers exist — *reported*
   (heartbeat), *real* (login set), *paid* (payroll). Any mismatch beyond
   tolerance -> **tamper flag on our dashboard**.

---

## 7. License lifecycle states

| State | Seats | Features | Dashboard | Rest of app |
|---|---|---|---|---|
| **Active** | enforced at `seats` | per `features[]` | visible | normal |
| **Grace** (our server unreachable, <= N days, e.g. 7) | last cached | last cached | visible | works + "reconnecting" banner |
| **Expired / revoked** | — | **ALL OFF** | **dashboard only** | **everything else locked** |

### Expiry behavior (firm requirement)
- On expiry/revocation, **only the dashboard is visible**. Every other module
  (employee, attendance, leave, payroll, recruitment, geofencing — all of them)
  shows a *"License expired — renew to restore access"* lock screen.
- **No data is deleted.** The moment they renew, the next heartbeat flips the
  state back to Active and everything unlocks.
- **Grace** (our downtime, not their non-payment) keeps a paying customer
  working so our outage never bricks their HR system. Grace != Expired.

> Open question to confirm: on expiry, should the still-visible dashboard show
> real read-only data, or only a status + renew screen with no employee data?
> Recommendation: read-only real dashboard (less alarming, shows what returns).

---

## 8. Enforcement points (where checks live, client side)

1. **Global middleware** (`licensing` app) on every request:
   - `expired/revoked` -> allow only dashboard + renew + logout URLs; everything
     else -> lock screen.
   - `active` -> continue.
2. **Feature gate** `feature_enabled("geofencing")` wraps each premium module's
   views; off -> "not included in your plan" screen.
3. **Seat gate** `can_add_employee()` on employee-create -> blocks at `seats`
   (active-only count).
4. **Login-token** call -> real-time seat truth + over-cap block for new hires.
5. **Heartbeat** (daily, via existing APScheduler pattern) -> pulls latest signed
   `{ seats, features, expiry, state }`.

---

## 9. Features in the codebase (real, not hypothetical)

### Core HR — keep always-on (do NOT lock)
| Feature | App |
|---|---|
| Employee records / directory | `employee` |
| Attendance check-in/out | `attendance` |
| Leave management | `leave` |
| Performance management (PMS) | `pms` |
| Onboarding | `onboarding` |
| Offboarding / resignation | `offboarding` |
| Asset management | `asset` |
| Helpdesk / tickets | `helpdesk` |
| Project & timesheet | `project` |

> These stay on while Active. On **expiry** they lock too (dashboard-only rule).
> "Don't lock" above means don't put them behind a *premium feature* flag during
> normal Active operation — they are included in every tier.

### Premium / lockable (real modules, ranked by lock quality)
| Feature | App | Lock quality | First wave? |
|---|---|---|---|
| Auto payroll + payslip PDF | `payroll` | high | YES |
| Geofencing attendance | `geofencing` | high | YES |
| Face-detection attendance | `facedetection` | high | YES |
| WhatsApp notifications | `whatsapp` | high | YES |
| Biometric device attendance | `biometric` | high | later |
| Email / Outlook integration | `outlook_auth` | high | later |
| Video meetings | `skylinx_meet` | high | later |
| LDAP / Active Directory sync | `skylinx_ldap` | high | later |
| REST API / mobile app | `skylinx_api` | high | later |
| Recruitment / ATS | `recruitment` | medium | later |
| Reports & exports | `report` | medium | later |
| Document management | `skylinx_documents` | medium | later |
| Workflow automations | `skylinx_automations` | medium | later |
| Custom dynamic fields | `dynamic_fields` | low | later |
| DB backups | `skylinx_backup`, `pg_backup` | low | later |

### Infrastructure (not features — ignore for licensing)
`base`, `skylinx_views`, `skylinx_widgets`, `skylinx_crumbs`, `skylinx_theme`,
`skylinx_auth`, `skylinx_audit`, `accessibility`, `notifications`, `load_data`,
`skylinx_dbtemplate`, `skylinx_documents` (infra parts).

---

## 10. How "customer pays more" works

1. Customer pays for +20 seats (or adds a feature).
2. We bump `seats` / add to `features[]` in our dashboard. Nothing ships.
3. Next heartbeat/auth -> server returns new **signed** values -> client updates
   instantly. The same path revokes or expires them.

---

## 11. Architecture diagram

```
  THEIR SERVER (they host)                  OUR LICENSE SERVER (small VPS)
 +------------------------+               +------------------------------+
 |  HRMS (Django)         |               |  license-server              |
 |                        |               |                              |
 |  licensing app         |-- login ----->|  /auth/issue   (token+seat)  |
 |   * verify signature   |   token req   |     -> distinct active set    |
 |   * state machine      |               |        = seat TRUTH           |
 |   * can_add_employee() |-- daily ----->|  /heartbeat    (liveness +   |
 |   * feature_enabled()  |   heartbeat   |     control channel)         |
 |   * cached authz/grace |-- payroll --->|  /payroll/render (+ audit)   |
 |                        |-- geofence -->|  /geofence/verify            |
 |  locked features ------|-- whatsapp -->|  /whatsapp/send              |
 |                        |-- face ------>|  /face/verify                |
 +------------------------+               |  admin dashboard (us)        |
   public key baked in                    +------------------------------+
                                            private key (NEVER shipped)
```

---

## 12. Build phases

1. **Crypto + license format** — generate keypair, define signed blob schema
   (seats + features + expiry + nonce), embed public key in HRMS.
2. **Client `licensing` app** (this repo) — signature/nonce verification, state
   machine (active/grace/expired), global middleware (expiry -> dashboard-only),
   `feature_enabled()`, `can_add_employee()`, login-token + cache/grace, daily
   heartbeat. Wire first gates in. Can run against a stub server.
3. **License server** (separate small project) — `/auth/issue`, `/heartbeat`,
   signing, feature endpoints, admin dashboard (set/raise seats, toggle features,
   revoke, view truth-layer counts + tamper flags).
4. **Move first features server-side** — payroll render, geofence verify,
   whatsapp send, face verify.
5. **Optional** — Cython-compile `licensing`; finalize EULA.

---

## 13. Open questions / decisions pending

- [ ] Expiry dashboard: real read-only data vs. status-only screen?
      (Recommendation: read-only real dashboard.)
- [ ] Login-token on every login acceptable with 7-day offline cache? (Rec: yes.)
- [ ] Grace period length N (days) — default 7.
- [ ] Login-set rolling window — default 30 days.
- [ ] Where to start building: Phase 1 -> 2 (crypto + client app first).
- [ ] EULA drafting (one license/company, seat cap, audit clause, no-circumvention).
