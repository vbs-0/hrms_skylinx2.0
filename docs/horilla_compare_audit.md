# Horilla dev/v2.0 Compare Audit

Reference clone: `C:\Users\chbha\Desktop\skylinx\horilla-v2-reference`

Compared:
- Emplinx branch `1.0.9.beta`, head `d0773b9` at audit start
- Horilla `dev/v2.0`, head `84de90b5e`

## Summary

This is not a small branding fork anymore. The Emplinx repo has 1037 Python files and the Horilla reference has 905 Python files. The file inventory differs by hundreds of files, so direct replacement is unsafe.

Use Horilla as a reference, not as a drop-in base.

## Fixed During This Pass

- `report/views/employee_report.py`
  - Employee report/pivot now starts from a company-scoped employee queryset.
  - Owner/superuser employees are excluded from client report data.

- `report/views/payroll_report.py`
  - Payroll report/pivot now uses `_payslip_queryset_for_request(request)`.
  - Removed raw `Payslip.objects.all()` from report data paths.

- `payroll/views/component_views.py`
  - `send_slip` now scopes selected payslip IDs through `_payslip_queryset_for_request(request)`.
  - Payslip export filter modal now uses the scoped payslip queryset.

- `payroll/views/views.py`
  - Bulk payslip status update now scopes selected IDs through `_payslip_queryset_for_request(request)`.

## Important Intentional Differences From Horilla

- Horilla treats `payroll.view_payslip` as broad report/list access.
  - Emplinx must not do that because employees need `view_payslip` for self-service payslips only.

- Horilla company switcher is normal multi-company HRMS behavior.
  - Emplinx must keep company switching owner-only because clients are tenants, not platform admins.

- Horilla employee dropdowns commonly start from `Employee.objects.all()`.
  - Emplinx must exclude owner/superuser employees and scope by the client company.

- Horilla report endpoints use broad `.objects.all()` patterns.
  - Emplinx reports must scope first, then apply filters.

## Still Needs Slower Sweep

- Employee dropdowns in forms/modals outside payroll reports:
  - reporting manager dropdowns
  - document request employee dropdown
  - shift/work-type assignment dropdowns
  - mail recipient dropdowns

- Reports outside payroll/employee:
  - attendance report
  - leave report
  - recruitment report
  - PMS report
  - asset report

- Company update/view endpoints:
  - clients should edit only their own company
  - clients should never list or select other companies

- HTMX shell disappearance:
  - `HtmxRedirectMiddleware` exists in Emplinx, not Horilla.
  - Remaining issue is likely a view returning a fragment into the wrong target or a redirect path not passing through normal middleware behavior.

## Do Not Copy Blindly

Copying Horilla's payroll/report permission behavior would reintroduce employee payroll/report leaks in Emplinx. Any borrowed code must be wrapped in Emplinx tenant scoping first.
