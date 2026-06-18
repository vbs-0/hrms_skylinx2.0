# India Localization — Part 2: US-isms still baked in

**Companion to `INDIA_LOCALIZATION.md`.** That doc covered terminology, forms,
PAN/Aadhaar, onboarding. It **missed the US-specific payroll/tax/locale guts**.
This doc is that sweep — every place the app still assumes USA, with file paths.

Same §0 safety rules from the first doc apply: **relabel/repurpose, don't delete.**
The tax models are user-data-driven (free-text records), so India fits by
relabeling + seeding, not by ripping anything out.

---

## A. The big one: "Federal Tax" is a whole US subsystem

India has **no federal tax.** Income tax here is central, slab-based, deducted as
**TDS** under the Income Tax Act, with an **Old Regime / New Regime** choice. The
app ships the US model: a "Federal Tax" menu, "Filing Status" (the US W-4
concept: Single / Married / Head of Household), and "Tax Brackets".

### What exists (don't delete — relabel + reseed)

| Thing | File | India action |
|---|---|---|
| Sidebar menu **"Federal Tax"** | `payroll/sidebar.py:50` | relabel → **"Income Tax (TDS)"** |
| `federal_tax_accessibility` perm fn | `payroll/sidebar.py:73` | keep (internal name, no UI) |
| `FilingStatus` model — `filing_status` is **free-text CharField**, not hardcoded Single/Married | `payroll/models/models.py:81` | relabel verbose_name → **"Tax Regime"**; seed two records: **Old Regime**, **New Regime** |
| `TaxBracket` (min/max income, rate per filing status) | `payroll/models/tax_models.py:47` | this IS income slabs — relabel "Filing status" → "Tax Regime"; seed FY25-26 slabs |
| Tax calc engine (`calculate_federal_tax`, `federal_tax_for_period`) | `payroll/methods/tax_calc.py` | **keep math** — slab math is identical; only var names say "federal" (internal, leave) |
| Tax views ("federal tax-related operations") | `payroll/views/tax_views.py:4` | relabel docstrings/messages only |
| Templates folder `cbv/federal_tax/`, `skylinx_theme/.../federal_tax/` | template dirs | relabel **displayed** headings; leave folder/file names |
| `.po` catalogs reference Federal Tax / Filing status | `skylinx/locale/*/django.po`, `skylinx_theme/locale/.../django.po` | add India translations there (cleanest layer) |
| FAQ entries about Federal Tax | `load_data/faq.json` | rewrite for TDS / regime |

> **Why this is safe:** `FilingStatus.filing_status` is a free CharField and
> `based_on` is just basic_pay vs gross. There are no hardcoded "Single/Married"
> choices to remove. So "make it Indian" = relabel the menu + create two regime
> records + enter the current slabs as TaxBrackets. Zero schema change.

### India FY 2025-26 slabs to seed (New Regime, default)
Seed as `TaxBracket` rows under a "New Regime" `FilingStatus` (`based_on` = gross,
verify against current Budget before going live — slabs change yearly):

| Min income (₹) | Max income (₹) | Rate |
|---|---|---|
| 0 | 4,00,000 | 0% |
| 4,00,001 | 8,00,000 | 5% |
| 8,00,001 | 12,00,000 | 10% |
| 12,00,001 | 16,00,000 | 15% |
| 16,00,001 | 20,00,000 | 20% |
| 20,00,001 | 24,00,000 | 25% |
| 24,00,001 | ∞ | 30% |

> ⚠️ Slabs are statutory and change every Union Budget (Feb). Treat the seed as a
> starting point with a "review each FY" note, not a constant. Old Regime (with
> 80C/HRA deductions) is a second FilingStatus record if you support both.
> Surcharge + 4% cess are not modeled — flag as a gap if you need exact TDS.

---

## B. Currency — defaults to US dollar

| Thing | File | India action |
|---|---|---|
| `PayrollSettings.currency_symbol` default **`"$"`** | `payroll/models/tax_models.py:31` | set to **`₹`** (Payroll → Settings UI, or change default) |
| `position` default `postfix` | `payroll/models/tax_models.py:33` | India shows symbol **before** amount → set **`prefix`** (₹1,200) |

Currency is read from `PayrollSettings.first().currency_symbol`
(`payroll/views/views.py:593,1593`) — so once set, payslips/PDFs follow. **But**
check for **hardcoded `$`** in templates/PDFs that bypass the setting (payslip
PDF, dashboard cards) and fix those to use the setting.

> Action: set ₹ + prefix in the seed/setup, and grep templates for a literal `$`
> next to an amount (distinct from jQuery `$`) before shipping payslips.

---

## C. Address / postal — US wording

India uses **PIN Code**, not ZIP. The field is named `zip` everywhere (keep the
field name) but the **label** says "Zip":

| Where | File | Action |
|---|---|---|
| Employee `zip` | `employee/models.py:103` (`verbose_name="Zip"`) | label → **"PIN Code"** |
| Export header "Zip Code" | `employee/forms.py:651` | header → "PIN Code" (sync import per Part-1 §11.1) |
| Recruitment `zip` | `recruitment/models.py:702` (`"Zip Code"`) | label → "PIN Code" |
| Onboarding portal `zip` | `onboarding/forms.py:336` (`label="Zip"`) | label → "PIN Code" |
| Company `zip` columns | `base/cbv/company.py:110,118` | label → "PIN Code" |

Also: default **Country = India**, and consider that India PIN is 6 digits
(validation `^\d{6}$` when shown) — current field is `max_length=20` free text,
fine to leave, tighten only if you want.

---

## D. Date format — US mm/dd/yyyy vs India dd/mm/yyyy

There's a date-format setting endpoint (`/settings/get-date-format/`). India uses
**dd/mm/yyyy** (or dd-mm-yyyy). Verify the default and set it to a `DD-MM-YYYY`
format in settings so dates don't display US-style. This is a settings value, not
code — confirm the default isn't `MM/DD/YYYY`.

---

## E. Sub-labels & smaller US-isms to verify

These are quick relabels (translation/verbose_name layer), grouped so you can
sweep them in one pass:

| US term in app | India label |
|---|---|
| Federal Tax | Income Tax (TDS) |
| Filing Status | Tax Regime |
| Tax Bracket | Income Slab |
| Zip / Zip Code | PIN Code |
| State (US connotation) | State / UT (keep, India has states + UTs) |
| Social Security / SSN | (not found — good; if any appear, → PAN/UAN) |
| Salary Hour | keep (hourly is rare in India but harmless) |
| Contract End Date | keep |

> No SSN/Medicare/401k fields were found in code — so the US-isms that remain are
> the tax subsystem (A), currency (B), ZIP (C), and date format (D). That's the
> complete list, not a sample.

---

## F. Provident Fund / ESI / UAN — what's genuinely missing for India tax

The first doc (§7) noted PF/ESI as manual. Tying it to tax: Indian salary has
statutory items the US-style tax engine doesn't know about:

- **PF (EPF)** — 12% employee + 12% employer; needs **UAN** number per employee.
- **ESI** — if gross ≤ ₹21k; needs **ESIC** number.
- **Professional Tax (PT)** — state slab, monthly.
- **TDS** — handled by the relabeled tax engine (A) IF you seed correct slabs.

UAN / ESIC / PT registration numbers are not fields today. If you need
compliance-grade payroll, add them like PAN/Aadhaar (additive nullable, Part-1
§6 pattern). Otherwise they live in manual Deduction records.

---

## G. Execution order (Part 2)

| # | Task | Layer | Risk | Migration? |
|---|---|---|---|---|
| 1 | Currency → ₹ + prefix; fix hardcoded `$` in payslip/PDF | settings + template | low | no |
| 2 | "Federal Tax"→"Income Tax (TDS)", "Filing Status"→"Tax Regime", "Tax Bracket"→"Income Slab" labels | labels/.po | low | no |
| 3 | Seed Old/New Regime FilingStatus + FY25-26 TaxBrackets | data seed | low | no |
| 4 | Zip → PIN Code labels (+ export/import header sync) | labels/export | low | no |
| 5 | Date format default → DD-MM-YYYY | setting | low | no |
| 6 | FAQ rewrite for TDS/regime/PIN/₹ | data | low | no |
| 7 | (optional) UAN/ESIC/PT number fields | model | low | additive |

All of 1–6 are relabel/seed/settings — **no schema change, no deletion**, fully
reversible. Run the Part-1 §0.7 regression matrix on payroll after 1–3 (payslip
generate + PDF + export are the things that can break).

---

### One-line summary
Part 1 fixed *HR* terminology. The money/tax/locale layer was still pure USA:
**Federal Tax → TDS (relabel + reseed, no delete), `$` → ₹, Zip → PIN, mm/dd →
dd/mm.** The tax models are free-text + slab rows, so India fits by relabeling and
seeding — not by surgery.
