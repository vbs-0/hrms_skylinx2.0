# Company Profile and HR Admin Onboarding

## Goal

Add a CEO-facing Company Profile area to the main sidebar on staging, modeled on the supplied Kredily screenshots, while preserving the existing Settings > Base > Company administration page. Add a simple company-admin onboarding flow so a CEO/platform owner can create an HR Admin with only name, email, and a temporary password.

## Scope

### Company Profile

- Add a main-sidebar Company Profile entry, visible to authenticated users with company-profile access.
- Add a profile shell with tabs for Overview, Address, Employee Custom Fields, Department, Designation, Announcements, Policies, Admin, Statutory, and My Plan.
- Reuse existing routes/pages for Department, Designation, Announcements, Policies, Admin, and My Plan through profile-tab links; do not duplicate those modules.
- Add missing profile data screens incrementally: overview/contact/social data, multiple addresses, statutory identifiers, directors/auditors/secretary, and bank accounts.
- Keep sensitive fields optional. A company can use the profile without entering PAN, GST, CIN, bank, or director information.

### HR Admin onboarding

- Add an Admin tab action available to an authorized company owner/platform owner.
- Form fields: full name, email, and temporary password.
- Create the user and employee record within the current company, assign the existing HR Admin role/group, and send an onboarding email when email delivery is configured.
- If email delivery is unavailable, show a clear success response with a one-time temporary-password handoff; never log or display the password after the response.
- Prevent cross-company assignment and duplicate email conflicts.
- HR Admin then manages employee profiles and company operations through existing permissions.

## Authorization and tenancy

- Platform owners may view/manage every company.
- Company owners/authorized company administrators may view and edit only their selected/current company.
- Ordinary employees may not access company-profile administration unless explicitly granted the relevant permission.
- Every profile query and mutation must be company-scoped; no global fallback for client users.
- Reuse existing company resolver, permission decorators, company manager patterns, and HR Admin group seeding.

## Reversibility and deployment

- Implement on a feature branch and merge only into `staging`.
- Add migrations only for new profile entities; migrations must be reversible with Django's normal reverse operation.
- Do not modify production files, production services, or production database.
- Preserve the existing Settings > Company routes during rollout so the feature can be disabled by removing the sidebar entry or reverting the feature branch.

## Validation

- Tests must cover sidebar visibility, company isolation, authorized editing, unauthorized access, HR Admin creation, duplicate email handling, role assignment, and password handling.
- Run focused tests, Django checks, migration checks, and staging smoke verification before declaring completion.
