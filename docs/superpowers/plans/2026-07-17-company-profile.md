# Company Profile and HR Admin Onboarding Implementation Plan

> **For agentic workers:** Execute task-by-task with a test before production code.

**Goal:** Add a company-profile main-sidebar experience and secure HR-admin onboarding on staging while preserving existing settings pages.

**Architecture:** Add a small `company_profile` Django app for profile metadata, addresses, statutory data, contacts, and bank accounts. The profile shell links existing HRMS modules instead of duplicating them. Onboarding reuses the existing employee/user/group models and company resolver.

**Tech Stack:** Django, PostgreSQL, existing HTMX templates, existing sidebar registry, Django TestCase.

## Global Constraints

- Staging only; production files, services, and database remain untouched.
- All profile queries/mutations are scoped to the current company unless the user is a platform owner.
- Sensitive profile fields remain optional.
- Existing Settings > Company routes remain available.
- Do not add third-party dependencies.

### Task 1: Create feature branch and app skeleton

**Files:** Create `company_profile/` app files; modify settings/app URLs only as needed.

- [ ] Create branch `codex/company-profile-staging` from the current branch.
- [ ] Add app config, models, URLs, views, forms, templates, and tests using existing Django patterns.
- [ ] Run `manage.py check` to verify app loading.

### Task 2: Add profile data models and forms

**Files:** `company_profile/models.py`, `company_profile/forms.py`, migrations, `company_profile/test_models.py`.

- [ ] Add optional one-to-one profile metadata linked to `Company`.
- [ ] Add company-scoped address, statutory, contact/social, director, and bank-account records.
- [ ] Add forms that reject cross-company object IDs and preserve optional blank fields.
- [ ] Write failing model/form tests, run them, implement the minimum, then rerun.

### Task 3: Add profile shell and main sidebar entry

**Files:** `company_profile/sidebar.py`, `company_profile/views.py`, `company_profile/urls.py`, templates, root URL/settings registration.

- [ ] Add a Company Profile main-sidebar module visible to authenticated users with company access.
- [ ] Add tabs for Overview, Address, Employee Custom Fields, Department, Designation, Announcements, Policies, Admin, Statutory, and My Plan.
- [ ] Link existing module URLs instead of cloning their pages.
- [ ] Test sidebar visibility for a company user, ordinary employee, and platform owner.

### Task 4: Add HR-admin onboarding

**Files:** `company_profile/views.py`, `company_profile/forms.py`, templates, tests.

- [ ] Add a form for name, email, and temporary password.
- [ ] Create the user and employee within the current company, assign the existing HR Admin group, and send email through configured Django email backend.
- [ ] Reject duplicate emails and cross-company assignment.
- [ ] Never log or render the temporary password after successful submission.
- [ ] Test authorized creation, group assignment, duplicate email, unauthorized access, and company isolation.

### Task 5: Verify and deploy staging

- [ ] Run focused tests, `manage.py check`, `makemigrations --check --dry-run`, and `git diff --check`.
- [ ] Commit only feature files and push the feature branch.
- [ ] Open/merge a PR into protected `staging`.
- [ ] Verify the staging workflow deploys and production is skipped.
- [ ] Verify staging service, commit SHA, and login HTTP 200.
