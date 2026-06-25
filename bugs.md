# Bugs To Track

- [ ] Client company list/edit scope: clients must only see and edit their own company.
- [ ] Subscription page ownership: client-facing plan controls should be owner/company scoped, not just permission scoped.
- [ ] Missing `employee_get` crash sites: remaining raw `request.user.employee_get` usages in leave, payroll, offboarding, and project views/templates.
- [ ] Dynamic create dropdowns: show `Create New ...` only when the current user can actually add that related object.
- [ ] Reporting manager dropdown: must never show the owner/superuser for client users.
- [ ] Subordinate pickers: must stay company-scoped and never include owner/superuser records.
- [ ] User group assign modal: must not list the owner or cross-company users for client tenants.
- [ ] Dynamic create job role branch: verify the Job Title / Job Role create flow refreshes the dropdown after modal submit.
- [ ] Duplicate selected-company logic: middleware and context processors still both manage company session state.
- [ ] Stale selected-company session: keep replacing hard `Company.objects.get(id=selected_company)` with safe fallbacks.
