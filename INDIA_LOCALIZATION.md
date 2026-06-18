# India Localization & Form Simplification — Master Plan

**Project:** Skylinx HRMS
**Target market:** Small / mid-size Indian companies
**Prime directive:** SIMPLIFY the UI, do **NOT** introduce regressions, do **NOT** break DB compatibility.

Single source of truth for what to change, where, and **what it breaks**. Read §0
(safety rules) and §11 (blast radius) before touching anything.

---

## 0. Safety rules (non-negotiable)

### 0.1 Never delete
No removing: model fields, DB columns, migrations, API contracts, serializers,
relationships. You may only **hide**, make **optional**, or move to **Advanced**.

### 0.2 Form safety
Change Django **forms**, not models, wherever possible.
- Allowed: `required=False`, grouping, conditional visibility, widget hiding.
- Forbidden: removing `save()`, `clean()`, or model references.

### 0.3 Validation safety
Hidden field → relax requirement AND gate validation on visibility:
```python
self.fields["some_field"].required = False

def clean(self):
    cleaned = super().clean()
    if cleaned.get("enable_feature"):   # only when shown / enabled
        ...                              # validate here, never always
    return cleaned
```

### 0.4 Template safety
Don't delete HTML. Wrap advanced fields, default off:
```django
{% if show_advanced %}{{ form.advanced_field }}{% endif %}
```

### 0.5 Database safety
Records must still open / edit / export. **No migrations for simplification.**
Migrations allowed ONLY for the new India fields (§6) and onboarding FK (§1.2) —
additive + nullable only, never destructive.

### 0.6 Backward compatibility
Old stored values load silently and save back unchanged even when hidden.

### 0.7 Mandatory regression test per touched module
After each edit verify **Create / Edit / Delete / Search / Import / Export /
Report**, and confirm no: console errors, validation errors, missing template
keys, HTMX swap failures, Select2 failures, digest/localStorage failures.

If a change risks breaking the system → **keep the original** and mark deferred.

---

## 1. Concept clarifications

### 1.1 What is an "Allowance"?
A named extra-pay component on top of basic salary
(`payroll/models/models.py → class Allowance`): title, amount, fixed-or-%,
taxable, targeted at all/specific employees or job positions. Payroll adds it to
gross at payslip time.

**India fit:** perfect as-is. Indian payslip = stack of allowances:
`Basic + HRA + DA + Conveyance + Medical + Special = Gross`. Don't change the
model — **create records**:

| Allowance | Typical rule |
|---|---|
| HRA | 50% basic (metro) / 40% (non-metro) |
| Conveyance | ₹1,600/mo |
| Medical | ₹1,250/mo |
| Special | balancing figure |

Statutory **deductions** (PF/ESI/PT) are not auto — see §7.

### 1.2 Why is Onboarding tied to Recruitment? Manual onboarding?
`Onboarding` has a **mandatory FK to Recruitment** (assumes ATS pipeline). Wrong
for Indian SMEs (referral / consultant / walk-in). Workaround today: dummy
Recruitment record. Real fix: FK `null=True, blank=True` + a "Direct Hire" path.
**Breakage to check before this** — see §11.7.

---

## 2. Terminology map (India labels)

Change **labels / translation strings only** — never field names.

| Current | India label |
|---|---|
| Payslip | **Salary Slip** |
| Leave Request | **Leave Application** |
| Disciplinary Action | **Show Cause / Warning** |
| Resignation | **Separation (F&F)** |
| Job Position | **Designation** |
| Work Type | **Work Mode** |
| Employee ID / Badge ID | **Employee Code** |
| Contract | **Employment Type** |

> ⚠️ **A label is not free text — see §11.1.** Several labels are wired into
> Excel import/export headers, the FAQ seed, and breadcrumbs. Renaming one and
> stopping there silently breaks import round-trips and leaves the FAQ lying.
> Every rename in this table has a checklist in §11.1 that MUST be done together.

---

## 3. Form simplification per module

Apply §0. "Hidden" = Advanced toggle, default off.

| Module | Visible | Hidden (Advanced) |
|---|---|---|
| Allowance | Title · Employees · Taxable · Fixed · Amount | Condition · Shift · Attendance · Limits |
| Deduction | Title · Amount · Type | rest |
| Payslip | Employee · Period · Earnings · Deductions · Net | (logic untouched) |
| Employee | Name · Emp Code · Email · Phone · Dept · Designation · DOJ · PAN · Aadhaar · Bank block | cost center, secondary contacts, rarely-used |

> ⚠️ Hiding an Employee field that appears in `excel_columns` does **not** remove
> it from export, and import still accepts it — good (backward compatible). But
> if you hide a field that import marks **required** (§11.1), imports of files
> that omit it will fail. Check the required list before hiding work-info fields.

---

## 4. Bank details — relabel & hide (NO deletion)

Form-level only:

| Field | Action | India label |
|---|---|---|
| Account Number / Bank Name / Branch | keep | same |
| `any_other_code1` | keep, **relabel** | **IFSC Code** (export header is "Bank Code #1" — §11.2) |
| `any_other_code2` | hide (Advanced) | (was SWIFT) |
| IBAN / Country | hide / default India | — |

IFSC validation (only when shown): `^[A-Z]{4}0[A-Z0-9]{6}$`.

> ⚠️ `any_other_code1` exports as header **"Bank Code #1"** (`forms.py:609`).
> Relabel the UI to "IFSC" but **keep the export/import header in sync** or old
> exported sheets won't re-import. See §11.2.

---

## 5. Employee card & search navigation bug

**Symptom:** clicking a card / search result opens read-only profile
(`employee-view-individual`) instead of editable tabs (`employee-view-update`).
**Cause:** the `<a href>` points at the profile URL name.
**Fix (template only):** change the href to `employee-view-update`, OR add an
explicit **Edit** button.

> ⚠️ `employee-view-update` requires **change_employee** permission;
> `employee-view-individual` is viewable by more roles. If you make the whole
> card link to edit, low-privilege users (who could view before) get a 403 on
> click. **Recommended:** keep card → profile, add an Edit button gated on
> permission. See §11.3.

---

## 6. New India fields (the ONLY additive migration on Employee)

Additive, nullable → safe. Add to Employee model:

| Field | Type | Rules |
|---|---|---|
| `pan_number` | CharField(10) | `^[A-Z]{5}[0-9]{4}[A-Z]$`, unique; for TDS / Form 16 |
| `aadhaar_number` | CharField(12) | 12 digits; **mask to last 4** on views (UIDAI); full value access-restricted |
| `account_type` | CharField choices | Savings / Current |

Placement: **Personal / Documents** tab (identity, not banking).
"Mandatory" enforced at **form** layer (`required=True`), not DB non-null, so old
rows still load/edit. Migration = plain `AddField(null=True)`, reverse = drop.

> ⚠️ Adding these is not done until you also touch **export, import, API
> serializer, and PDF/Form-16 templates** — otherwise PAN/Aadhaar are invisible
> everywhere except the edit form. See §11.4.

---

## 7. Statutory deductions (PF/ESI/PT) — feature, not relabel

| Item | Rule | Status |
|---|---|---|
| PF | 12% emp + 12% employer of basic | manual Deduction today |
| ESI | 0.75% emp + 3.25% employer (gross ≤ ₹21k) | manual today |
| PT | state-wise monthly slab | manual today |

Short term: create Deduction records with correct %. Long term: India statutory
engine at payslip time (large, separate project, own test plan).

---

## 8. Already exists — just surface / populate (no/low code)

| Want | Where |
|---|---|
| Activity / notification log | `skylinx_audit` → `SkylinxAuditLog`; add HR nav link to a list view |
| Holidays | Leave → **Holidays** (auto-excluded from leave calc) |
| Restricted holidays | Leave → **Company Leaves** |
| Leave types (CL/PL/SL) | Leave → **Leave Types** |
| Weekly off / work week | Setup → **Work Types / Shifts** |
| Allowances | Payroll → create §1.1 records |

Real-time bell notifications = separate `Notification` model + signals (not
built). Pre-seeded India holiday list = nice-to-have data seed.

---

## 9. FAQ / Help — must be updated with every rename

FAQs are **data-driven**, not hardcoded: `helpdesk/management/commands/
create_faqs.py` loads question/answer/category from a JSON file into the `FAQ`
model. So:

- The FAQ does **not** auto-follow UI label changes. If you rename "Payslip" →
  "Salary Slip" in the UI, the FAQ still says "Payslip" until you edit the JSON
  seed and re-run `create_faqs`, OR edit FAQs in the helpdesk UI.
- "FAQ doesn't have every guide" → because the seed JSON only covers upstream
  topics. Add India-specific FAQs: PAN/Aadhaar, salary-slip components, leave
  types, manual onboarding, where to set holidays.

**Action:** maintain an India FAQ JSON and re-seed after each terminology batch.
Treat FAQ update as a **required step of every rename**, not a follow-up.

---

## 10. Execution order

| # | Task | Type | Effort | Migration? | FAQ touch? |
|---|---|---|---|---|---|
| 1 | Relabel bank (IFSC) + sync export/import header | form/template/export | small | no | no |
| 2 | Terminology labels (§2) + import header + FAQ | labels/export/FAQ | medium | no | **yes** |
| 3 | Card / search → correct target + perm gate | template | tiny | no | no |
| 4 | Simplify Allowance/Deduction/Payslip/Employee forms | form/template | small | no | maybe |
| 5 | Surface audit log in HR nav | view + nav | small | no | add FAQ |
| 6 | PAN + Aadhaar + Account Type (+ export/import/API/PDF) | model + plumbing | medium | **yes** | add FAQ |
| 7 | Manual onboarding path | model + form | medium | **yes** | add FAQ |
| 8 | India statutory deduction records | data | small | no | add FAQ |
| 9 | Pre-seed India holidays | data | small | no | no |
| 10 | PF/ESI engine, Form 16/TDS, F&F flow | feature | large | later | yes |

Do 1–5 first (lowest risk). Run §0.7 after each. Note: "small" effort assumes the
§11 blast-radius items are done in the same batch — they are not optional.

---

## 11. Blast radius — what breaks, and the full touch-list per change

This is the section that prevents regressions. Each rename/hide touches more than
the form.

### 11.1 Renaming any field LABEL (terminology, §2)
A label string is reused as an **Excel column header** and checked by **import
validation**. The two are not kept in sync by the framework.

- **Export headers** come from `employee/forms.py:571` `excel_columns` (each
  label wrapped in `_()`).
- **Import validation** hardcodes **English** header strings in
  `employee/methods/methods.py:227` `required_keys` = `["Badge ID","First Name",
  "Department","Job Position","Job Role","Work Type","Shift","Employee Type",
  "Reporting Manager","Company","Location","Date Joining","Contract End Date",
  "Basic Salary","Salary Hour", ...]`.

**Consequences of a careless rename:**
- Rename "Job Position" → "Designation" only in the form → export sheet header
  becomes "Designation" but import still demands "Job Position" → **re-importing
  your own export fails.**
- Latent bug already present: export labels translate per-locale, import keys are
  hardcoded English → non-English imports already mismatch. Don't widen it.

**Touch-list for EVERY label rename:**
1. The form label / `verbose_name`.
2. `excel_columns` in `employee/forms.py` (export + template header).
3. `required_keys` / column lookups in `valid_import_file_headers`
   (`employee/methods/methods.py`) and the bulk-create importers that read by
   column name (`bulk_create_*` in `employee/views.py`).
4. The import-template generator (`employee_template` / work-info template) so
   downloaded blank templates carry the new headers.
5. Breadcrumb labels (`skylinx_crumbs`) if they hardcode the old word.
6. **FAQ JSON** (§9) so help text matches.
7. API serializer field labels / docs if any client depends on them (§0.1: don't
   rename the JSON *key*, only the human label).
8. Email templates / payslip PDF / report headers that print the old word.

> Safer pattern: keep the **internal/import key English and stable**, change only
> the **displayed label** via translation catalog (`base/translator.py` / `.po`).
> That way export-for-humans reads "Designation" while the import contract stays
> "Job Position". Decide per field which layer the rename lives in.

### 11.2 Bank relabel (§4)
`any_other_code1` → UI "IFSC", but its export header is **"Bank Code #1"**
(`forms.py:609`) and bank columns are part of export. If you relabel the export
header too, **old exported sheets won't re-import**; if you don't, the UI says
IFSC while the sheet says Bank Code #1. Pick one and apply across form + export +
import + payslip/bank-advice PDF. Bank columns are **not** in `required_keys`, so
import won't hard-fail if absent — but the mapping must match to land data.

### 11.3 Card / search nav (§5)
`employee-view-update` is permission-gated (`change_employee`);
`employee-view-individual` is broader. Repointing the card link 403s
view-only users. Also check: search results template, recent-activity widgets,
any bookmarked/emailed deep links to the old URL. **Recommended:** card →
profile (unchanged), add a permission-gated Edit button.

### 11.4 PAN / Aadhaar / Account Type (§6)
Adding the model field is ~10% of the work. Also touch:
1. Employee form + template (Personal/Documents tab).
2. `excel_columns` (export) + import column mapping + `process_employee_records`
   so bulk import can set them.
3. Import template generator (new optional columns).
4. API serializer (additive field, don't break existing keys).
5. Masking logic for Aadhaar on list/detail/export (show last 4) — and decide
   who can see full value.
6. Form-16 / payslip PDF where PAN is legally required.
7. PAN uniqueness: a unique constraint can break bulk import if duplicates exist
   in legacy data — validate, don't crash.

### 11.5 Hiding fields (§3)
Hidden ≠ removed from export/API (good — backward compatible). Risks:
- Hiding a field that import marks **required** (§11.1) breaks imports omitting
  it. Cross-check `required_keys` before hiding any work-info field.
- Select2 / HTMX widgets that initialize on a now-hidden field can throw JS
  errors if hidden with `display:none` but still initialized — hide by not
  rendering (template `{% if %}`), not by CSS alone, where a widget is involved.
- A `clean()` that still references the hidden field (§0.3) will validate
  invisibly — gate it.

### 11.6 Allowance/Deduction/Payslip simplification (§3)
Payroll math reads model fields, not form layout — hiding form fields is safe for
calculation. But: hidden "Condition/Shift/Attendance/Limits" still apply to
**existing** allowance records (backward compat, intended). New records created
via the simplified form get defaults — confirm the model defaults produce a
plain "always-apply fixed amount", else simplified allowances behave oddly.

### 11.7 Manual onboarding (§1.2)
Before making the Recruitment FK nullable, audit every reader that assumes it's
present: onboarding list/detail templates rendering `onboarding.recruitment.*`,
onboarding filters/reports grouping by recruitment, any
`select_related("recruitment")` that would now yield None. Add null-guards in
those templates/queries in the same change, or they raise on direct-hire records.

### 11.8 General JS / theme
`base.py` `STATIC_URL` and WhiteNoise already fixed. When adding templates,
reuse existing skylinx theme blocks; new JS that touches `localStorage`/digest
must match the existing key scheme or the §0.7 "digest/localStorage" checks fail.

---

## 12. Output / rollback discipline (per change set)
Produce: files changed · exact diffs · rollback steps · §0.7 checklist result.
- Tasks 1–5: revert = `git revert` the commit (no data touched).
- Tasks 6–7: reverse migration drops only the new nullable fields.
- Tasks 8–9: delete the seeded records.
- Task 10: separate project, own test plan.
If a change can't pass §0.7, revert and mark deferred here rather than ship a
regression.

---

### Appendix — one-line risk summary
- Labels are import/export contracts AND FAQ content — never rename in isolation (§11.1).
- Nav repoint can 403 view-only users (§11.3).
- New fields are 10% model, 90% plumbing (§11.4).
- Nullable onboarding FK needs null-guards in every reader (§11.7).
- Hidden ≠ deleted; that's the whole backward-compat strategy (§0.6, §11.5).
