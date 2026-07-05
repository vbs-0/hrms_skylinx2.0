# HRMS 2.0 Settings Administration Guide

This guide is designed for non-technical HR administrators to understand and navigate the **Settings** area of the Django HRMS. It describes every settings section in the sidebar menu order, detailing what it does, when to use it, the permission gates, and any specific "gotchas" (such as company/tenant restrictions or hidden behaviors).

---

## Navigation & Layout Overview
The settings page is structured with a left-hand navigation sidebar categorizing the configuration areas, and a right-hand main content block (`#settingsContainer`) where specific forms and tables are dynamically loaded.

* **Top-Level Company Selector:** Some settings lists or forms are filtered based on the active company selected in your session.

---

## 1. General Settings Group

### General Settings
* **What it does:** The main dashboard for basic system configurations. It aggregates multiple sub-forms including:
  * **Badge ID Prefix:** Defines the default prefix code used when generating employee ID cards (badge IDs).
  * **Announcement Expire:** Configures how many days internal company announcements remain active before expiring.
  * **Account Block/Unblock:** Toggle to enable or disable automatic account lockout features.
  * **Profile Edit feature:** Toggles whether regular employees are allowed to edit their personal details on their profiles.
  * **History Tracking Fields:** Configures audit logs for changes on selected database fields.
  * **Dynamic Pagination:** Sets your personal default row limit per page when viewing lists.
  * **Payroll Currency & Encashment Settings:** Configures default salary currency and leave payout policies (only visible if the Payroll module is active).
* **When to use:** During system setup or when modifying basic tenant preferences (such as updating employee badge patterns or enabling self-service profile edits).
* **Permission Gate:** Logged-in system users (`@login_required`). Access is open to users permitted to view general settings.
* **Gotchas:** 
  * **Company-Specific Prefix:** The Badge ID prefix is linked to the company selected in your session. If "All" is active in the company filter, the prefix form lists all companies. If a specific company is selected, only that company's prefix can be configured.
  * **Personal Pagination:** The Dynamic Pagination setting is stored on your individual user account and does not affect other admins.
  * **Payroll Dependency:** Currency and Encashment settings will not load unless the Payroll app is installed in the system.

### Employee Permission
* **What it does:** Grants fine-grained, individual Django system permissions directly to specific employees, bypassing their global role/user group.
* **When to use:** When a specific employee needs temporary or custom permissions (e.g., an employee who isn't an HR Manager but needs to manage recruitment files).
* **Permission Gate:** Requires `auth.view_permission` (Sidebar check and `@manager_can_enter` view decorator).
* **Gotchas:** 
  * **Excluded Models:** Certain critical models defined in `settings.NO_PERMISSION_MODALS` are omitted from the assignable list for security.
  * **URL Parameters:** Accessing this view with an employee ID in the URL updates permissions for that employee. Accessing it normally displays the employee permissions list.

### Accessibility Restriction
* **What it does:** Allows administrators to restrict or whitelist access to specific features for groups of employees matching target filter criteria.
* **When to use:** Enforcing strict compliance boundaries (e.g., preventing remote workers or junior staff from accessing sensitive modules).
* **Permission Gate:** The sidebar checks `perms.auth.view_permission`, but the backend view strictly requires `perms.auth.change_permission`.
* **Gotchas:** 
  * **Mismatched Permissions:** View-only administrators can see this link in the sidebar, but clicking it will result in a "403 Forbidden" error since saving requires change permissions.
  * **Clearing Filters:** Saving an empty filter form removes all accessibility restriction rules.

### Roles & Permissions
* **What it does:** A card-based visual interface summarizing defined system groups (roles) like "HR Manager", "Supervisor", and "Employee", displaying their total users and active permissions.
* **When to use:** Creating new user groups or reviewing high-level permissions mapped to existing roles.
* **Permission Gate:** Requires `auth.view_group` (view decorator and sidebar check).
* **Gotchas:** 
  * **Company Scope:** Roles are strictly company-scoped. If no company is selected in your active session, no roles will load. You will only see roles belonging to the company currently active in your session.

### User Group
* **What it does:** A paginated, tabular list of user groups (roles).
* **When to use:** Managing standard roles, linking them to specific companies, or configuring standard permissions.
* **Permission Gate:** Requires `auth.view_group` (view decorator and sidebar check).
* **Gotchas:** 
  * **Company Scope:** The list of user groups is filtered by the company selected in the active session. If no company is active, the list appears empty.

### Date & Time Format
* **What it does:** Selects date and time display preferences across the system.
* **When to use:** Adapting the interface to local date formats (e.g. DD-MM-YYYY vs YYYY-MM-DD).
* **Permission Gate:** Requires `base.view_company` (view decorator and sidebar check).
* **Gotchas:** 
  * Acts as a portal to select formatting, but actual format configuration is stored under individual company settings.

### History Tags
* **What it does:** Views and manages tags used for classifying auditing logs.
* **When to use:** Creating standard labels to flag specific system changes.
* **Permission Gate:** The view checks `skylinx_audit.view_audittag`. The sidebar checks `perms.base.view_tags`, `perms.employee.view_employeetag`, or `perms.skylinx_audit.view_audittag`.
* **Gotchas:** 
  * **Mismatched Permissions:** Users with only base tag view permissions will see the link but will get a 403 error on click if they do not have the specific `skylinx_audit.view_audittag` permission.

### Audit Tracking
* **What it does:** Defines which system models (database tables like Leave Request, Attendance, Employee) have change-history tracking enabled.
* **When to use:** Enabling or disabling tracking on data tables to monitor edits or creations.
* **Permission Gate:** Requires `skylinx_audit.view_auditmodelconfig` (view decorator and sidebar check).
* **Gotchas:** 
  * Turning this off stops saving history edits. Deleting a configuration deletes historical logs for that model.

### Activity Log
* **What it does:** Consolidates historical edits, creations, and deletions from all tracked tables into a single chronological log feed.
* **When to use:** Investigating who modified a record, what changes were made, and when they occurred.
* **Permission Gate:** Requires `skylinx_audit.view_auditmodelconfig` (view decorator and sidebar check).
* **Gotchas:** 
  * **Performance Limit:** Cap of 200 history logs loaded per model to ensure fast loading times.
  * **No Company Scoping:** Logs are displayed globally for all companies registered in the system.

### Mail Server
* **What it does:** Configures the outbound SMTP email server used to send password resets, notifications, and payslips.
* **When to use:** Setting up or modifying your corporate email relay.
* **Permission Gate:** Requires `base.view_dynamicemailconfiguration` (view decorator and sidebar check).
* **Gotchas:** 
  * **Outlook Conflict:** This setting is hidden from the sidebar if the Microsoft Outlook Mail plugin is installed.

### Outlook Mail
* **What it does:** Configures Azure Active Directory API integrations to send company emails via Microsoft Outlook.
* **When to use:** Integrating Microsoft Office 365 services for system mail instead of traditional SMTP.
* **Permission Gate:** The view requires `outlook_auth.view_azureapi`. The sidebar checks `perms.base.view_dynamicemailconfiguration`.
* **Gotchas:** 
  * **Outlook app check:** Only active if `"outlook_auth"` is installed.
  * **Mismatched Permissions:** Accessing the page will return a 403 error if you have SMTP viewing permissions but lack Azure API viewing permissions.

### Gdrive Backup
* **What it does:** Configures Google Drive authentication to store automated SQL database backups.
* **When to use:** Setting up secure, offsite database backup schemes.
* **Permission Gate:** The view checks `backup.add_localbackup`. The sidebar checks `perms.skylinx_backup.view_googledrivebackup`.
* **Gotchas:** 
  * **Database Restriction:** Strictly requires PostgreSQL. If using SQLite, it displays a 404 error page.
  * **Automatic Deactivation:** Editing and saving these credentials automatically pauses the backup runner. You must manually start it again.

### LDAP Configuration
* **What it does:** Configures Active Directory / LDAP servers for syncing employee accounts and logging in.
* **When to use:** Syncing employee lists from your corporate network.
* **Permission Gate:** Requires `skylinx_ldap.add_ldapsettings` or `skylinx_ldap.update_ldapsettings`.
* **Gotchas:** 
  * Only active when `"skylinx_ldap"` is installed. Manages a single global LDAP configuration profile.

---

## 2. Base Settings Group

### Department
* **What it does:** Manages departments (e.g. Finance, Sales, Human Resources).
* **When to use:** Structuring departments for reporting lines.
* **Permission Gate:** Requires `base.view_department` (view decorator and sidebar check).
* **Gotchas:** 
  * Departments are listed globally; no company-level filtering is applied to the table display.

### Job Positions
* **What it does:** Manages hiring job titles (e.g. Junior Accountant, Senior Manager).
* **When to use:** Defining vacancy titles or job criteria.
* **Permission Gate:** Requires `base.view_jobposition` (view decorator and sidebar check).
* **Gotchas:** 
  * Displays all positions globally with inline creation forms.

### Job Role
* **What it does:** Defines specific roles nested under job positions.
* **When to use:** Specifying granular jobs or levels within a position.
* **Permission Gate:** Requires `base.view_jobrole` (view decorator and sidebar check).
* **Gotchas:** 
  * Global list.

### Company
* **What it does:** Displays registered companies and organizations.
* **When to use:** Managing corporate details, locations, and logos.
* **Permission Gate:** Requires `base.view_company` (view decorator and sidebar check).
* **Gotchas:** 
  * **Role Restriction:** Platform Owners see all companies. Standard Company Admins are strictly locked to viewing only their assigned company profile.

---

## 3. Recruitment Settings Group
*(Only visible if the Recruitment module is active)*

### Candidate Self Tracking
* **What it does:** Toggles tracking features for applicants to check their status.
* **When to use:** Managing external applicant status portals.
* **Permission Gate:** Requires `recruitment.view_recruitment` (view decorator and sidebar check).
* **Gotchas:** 
  * Loads the general recruitment settings templates.

### Candidate Reject Reason
* **What it does:** Manages standard rejection reason tags (e.g., "Mismatched Salary Expectations").
* **When to use:** Setting up dropdown criteria for rejection tracking.
* **Permission Gate:** Requires `recruitment.view_rejectreason` (view decorator and sidebar check).
* **Gotchas:** 
  * Listed globally.

### Skills
* **What it does:** Configures candidate skills used during resume evaluation.
* **When to use:** Adding keywords (e.g., "Python", "Accounting") for resume scanning.
* **Permission Gate:** View only requires login. Sidebar checks `recruitment.add_recruitment`.
* **Gotchas:** 
  * **Mismatched Permissions:** Non-recruiters can access the skills list if they bypass the sidebar checks because the view only requires a standard login.

### Linkedin Integration
* **What it does:** Connects Linkedin profiles to publish openings.
* **When to use:** Authenticating recruiters' Linkedin accounts.
* **Permission Gate:** View checks `recruitment.view_linkedinaccount`. Sidebar checks `perms.recruitment.add_linkedinaccount`.
* **Gotchas:** 
  * Mismatched sidebar permission check versus view validation.

---

## 4. Employee Settings Group

### Work Type
* **What it does:** Defines employee work modes (e.g., Remote, On-Site, Hybrid).
* **When to use:** Creating new contracts or tracking attendance modes.
* **Permission Gate:** Requires `base.view_worktype` (view decorator and sidebar check).
* **Gotchas:** 
  * **Company Scoped:** Filtered based on your session's active company.

### Rotating Work Type
* **What it does:** Manages work arrangements that cycle over dates.
* **When to use:** Standardizing schedules like "3 days in-office, 2 days remote" rotation.
* **Permission Gate:** Requires `base.view_rotatingworktype` (view decorator and sidebar check).
* **Gotchas:** 
  * Listed globally.

### Employee Shift
* **What it does:** Manages working hour shifts (e.g. Night Shift, Day Shift).
* **When to use:** Establishing standard start and end times for work.
* **Permission Gate:** Requires `base.view_employeeshift` (view decorator and sidebar check).
* **Gotchas:** 
  * Excludes default grace times from shift layouts.

### Rotating Shift
* **What it does:** Sets shifts that automatically cycle (e.g. alternating morning/evening shifts).
* **When to use:** Managing shifts for 24/7 customer support or manufacturing units.
* **Permission Gate:** Requires `base.view_rotatingshift` (view decorator and sidebar check).
* **Gotchas:** 
  * Listed globally.

### Employee Shift Schedule
* **What it does:** Configures calendars mapping employees to shift rosters.
* **When to use:** Overseeing weekly/monthly shift schedules.
* **Permission Gate:** Requires `base.view_employeeshiftschedule` (view decorator and sidebar check).
* **Gotchas:** 
  * Listed globally.

### Employee Type
* **What it does:** Defines standard contract arrangements (e.g. Intern, Permanent, Contractor).
* **When to use:** Standardizing benefits based on employee categories.
* **Permission Gate:** Requires `base.view_employeetype` (view decorator and sidebar check).
* **Gotchas:** 
  * Global list.

### Disciplinary Action Type
* **What it does:** Sets up levels of disciplinary warnings (e.g., Written Warning, Final Warning).
* **When to use:** Documenting employee incidents.
* **Permission Gate:** Requires `employee.view_actiontype` (view decorator and sidebar check).
* **Gotchas:** 
  * Global list.

### Employee Tags
* **What it does:** Manages tags used to label staff (e.g., "First Aid Certified").
* **When to use:** Tagging employees for search filters.
* **Permission Gate:** Requires `employee.view_employeetag` (view decorator and sidebar check).
* **Gotchas:** 
  * Global list.

---

## 5. Attendance Settings Group
*(Only visible if the Attendance module is active)*

### Track Late Come & Early Out
* **What it does:** Enables calculations mapping late clock-ins and early clock-outs.
* **When to use:** Penalizing or tracking employee tardiness.
* **Permission Gate:** View checks `base.view_tracklatecomeearlyout`. Sidebar checks `perms.attendance.view_attendancevalidationcondition`.
* **Gotchas:** 
  * **Mismatched Permissions:** Bypassing users might hit 403.
  * **Company Scoped:** Scopes based on your selected company. If "All" is selected, it configures a global fallback (company = None).

### Attendance Break Point
* **What it does:** Sets minimum hour thresholds to count half-day or full-day attendance.
* **When to use:** Defining cutoff rules (e.g. working less than 4 hours is marked as a Half Day).
* **Permission Gate:** Requires `attendance.view_attendancevalidationcondition` (view decorator and sidebar check).
* **Gotchas:** 
  * Applies globally.

### Check In/Check Out
* **What it does:** Toggles standard web clock-in/out features.
* **When to use:** Setting up self-service check-in tools.
* **Permission Gate:** Only requires login. Sidebar checks `perms.attendance.view_attendancevalidationcondition`.
* **Gotchas:** 
  * **Mismatched Permissions:** Non-admins might load this setting page dynamically if they bypass sidebar links.

### Grace Time
* **What it does:** Sets how many minutes employees are excused for checking in late.
* **When to use:** Allowing a 10-minute buffer after shift starts without marking the employee late.
* **Permission Gate:** Requires `attendance.view_attendancevalidationcondition` (view decorator and sidebar check).
* **Gotchas:** 
  * Lists only custom grace times. The default grace time is excluded.

### Biometric Attendance
* **What it does:** Connects to physical biometric card/fingerprint devices.
* **When to use:** Configuring credentials for automated device syncs.
* **Permission Gate:** Requires `base.view_biometricattendance` (view decorator and sidebar check).
* **Gotchas:** 
  * **Company Scoping:** Configured specifically for the active company in your session.

### IP Restriction
* **What it does:** Restricts web clock-in/out actions to authorized company network IPs.
* **When to use:** Preventing workers from clocking in outside the office premises.
* **Permission Gate:** Requires `attendance.add_attendance` (view decorator and sidebar check).
* **Gotchas:** 
  * Configures a single global IP profile.

### Geo & Face Config
* **What it does:** Configures geofencing coordinates and facial verification photo requirements.
* **When to use:** Requiring employees to match coordinates or take a selfie to verify identity during mobile clock-in.
* **Permission Gate:** Only requires login. Sidebar checks `perms.geofencing.add_geofencing` or `perms.facedetection.add_facedetection`.
* **Gotchas:** 
  * View does not enforce strict permissions, but individual save/update actions do.

---

## 6. Leave Settings Group
*(Only visible if the Leave module is active)*

### Restrictions
* **What it does:** Restricts regular employees from submitting retrospective leave requests.
* **When to use:** Preventing staff from requesting leaves for dates in the past.
* **Permission Gate:** View requires `leave.view_leavegeneralsetting`. Sidebar checks `perms.leave.add_restrictleave`.
* **Gotchas:** 
  * **Mismatched Permissions:** A mismatch exists between the sidebar check and the view decorator.
  * Modifies a single global toggle instance.

### Compensatory Leave
* **What it does:** Sets rules for claiming paid compensatory leave.
* **When to use:** Setting up leave credits in exchange for working holiday shifts.
* **Permission Gate:** View requires `leave.view_leavegeneralsetting`. Sidebar checks `perms.attendance.view_attendancevalidationcondition`.
* **Gotchas:** 
  * **Mismatched Permissions:** Mismatch between sidebar check and view validation.
  * **Company Scoping:** Filters/creates compensatory leave rules specific to the active company.

---

## 7. Payroll Settings Group
*(Only visible if the Payroll module is active)*

### Payslip Auto Generation
* **What it does:** Schedules automatic payslip calculation tasks.
* **When to use:** Automatically calculating and generating payroll at the end of the month.
* **Permission Gate:** Requires `payroll.view_payslipautogenerate` (view decorator and sidebar check).
* **Gotchas:** 
  * Global scheduling lists.

---

## 8. Performance (Bonus Point Setting)
*(Note: Hidden from sidebar UI via `{% if False %}`, but active in backend views)*

### Bonus Point Setting
* **What it does:** Sets points for performance milestones.
* **When to use:** Rewarding employee actions.
* **Permission Gate:** View requires `pms.view_bonuspointsetting`. Sidebar checks `perms.pms.add_bonuspointsetting`.
* **Gotchas:** 
  * **UI Visibility:** Currently disabled and hidden in the sidebar layout.

---

## 9. Help Desk Settings Group
*(Only visible if the Help Desk module is active)*

### Department Managers
* **What it does:** Assigns department managers to handle internal tickets.
* **When to use:** Assigning helpdesk managers to specific departments.
* **Permission Gate:** Requires `helpdesk.view_departmentmanager` (view decorator and sidebar check).
* **Gotchas:** 
  * Global list.

### Ticket Type
* **What it does:** Sets ticket categories (e.g. IT, Admin, HR).
* **When to use:** Sorting employee ticket issues.
* **Permission Gate:** Requires `helpdesk.view_tickettype` (view decorator and sidebar check).
* **Gotchas:** 
  * Global list.

### Helpdesk Tags
* **What it does:** Manages tags used to label tickets.
* **When to use:** Grouping tickets for organization.
* **Permission Gate:** Requires `helpdesk.view_tag` (view decorator and sidebar check).
* **Gotchas:** 
  * Global list.

---

## 10. Whatsapp Configuration Settings Group
*(Only visible if the Whatsapp module is active)*

### Whatsapp Credentials
* **What it does:** Links Whatsapp credentials for system alerts.
* **When to use:** Configuring APIs to send automated alerts via Whatsapp.
* **Permission Gate:** View requires standard login. Sidebar checks `perms.whatsapp.view_whatsappcredentials` and `perms.whatsapp.add_whatsappcredentials`.
* **Gotchas:** 
  * Renders a blank template; credentials form actions enforce add/delete permissions.
