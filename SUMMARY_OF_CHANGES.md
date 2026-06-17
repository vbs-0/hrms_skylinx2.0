# Summary of Changes — Skylinx HRMS Fixes and Enhancements

Below is a detailed report of the changes and fixes implemented in the Skylinx HRMS codebase today.

---

## 1. PMS (Performance Management System) & Access Control Fixes
To restrict regular Employees (EMP role) from performing administrative/management tasks on Objectives:
* **Pms Sidebar Link Restriction** (`pms/sidebar.py`):
  - Hided the "Objective Templates" link from regular employees. Access is restricted to HR/Admin (`pms.add_objective` permission) and managers (`is_reportingmanager`).
* **Objective List View Button Restriction** (`pms/cbv/objectives.py`):
  - Hidden the "Create Employee Objective" button for regular employees.
* **Form View Restrictions** (`pms/cbv/objectives.py`):
  - Blocked access to the creation forms `/pms/create-employee-objective/` entirely for employees by raising a `PermissionDenied` exception in the view `dispatch` handler.
  - Restricted managers from editing objectives that do not belong to their subordinate team members.
* **Employee Option Filtering** (`pms/forms.py`):
  - **Employee Dropdown**: Regular employees can only see themselves. Managers can see their subordinate employees and themselves. HR/Admins see all active employees.
  - **Add Assignees Form**: Restricts the selection to subordinates for managers, and returns an empty list for regular employees.

## 2. Attendance Request Form Bugs & Improvements
Addressing issues in the New Attendance Request form at `/attendance/request-attendance-view/`:
* **Batch Attendance Auto-fill View & Routing** (`attendance/views/requests.py`, `attendance/urls.py`):
  - Registered `/attendance/get-batch-details/` view that queries the first attendance record associated with the selected batch and returns details (clock in/out time & date, shift, worked hours, minimum hours) as JSON.
* **Form Configuration & Styling** (`attendance/forms.py`):
  - Set `attendance_worked_hour` field to read-only.
  - Set `request_description` field to required.
  - Styled `batch_attendance_id` with select2 classes (`oh-select oh-select-2 w-100`) and hooked up its change listener.
  - Locked `employee_id` to the logged-in user if they are a regular employee and disabled the choice field.
* **Backend Validation Checks** (`attendance/forms.py`):
  - Added validations in `clean()` to verify that check-out date/time cannot occur before check-in.
  - Prevented future dates from being selected for attendance, check-in, or check-out dates.
  - Checked that worked hours cannot be `"00:00"`.
* **Frontend Real-time Operations & JS Validation** (`attendance/templates/requests/attendance/request_new_form.html`):
  - **Clear Button**: Added a reset button next to Save that resets inputs, updates Select2 dropdown values to their default states, and removes errors/warnings.
  - **Auto-calculate Worked Hours**: Calculations are updated in real-time as users modify date/time inputs.
  - **Warnings**: Generates a red warning label if calculated worked hours is less than the shift's minimum hours.
  - **Dynamic Save Button State**: The Save button is disabled with reduced opacity until all mandatory fields are filled and there are no validation errors.

## 3. General Access Control & Theme Fixes
* **Employees Sidebar Restriction** (`skylinx_theme/templates/skylinx_theme/components/sidebar.html`, `employee/sidebar.py`):
  - Hided the "Employees" link in the main navigation sidebar for regular employees. Link visibility is restricted to users with `employee.view_employee` permission or managers.
* **Create Policy Button Restriction** (`employee/cbv/policy_cbv.py`):
  - Restricted the visibility of the "Create" button on Policies to users with `employee.add_policy` permission.
* **Hour Account Action Restrictions** (`attendance/cbv/hour_account.py`):
  - Hidden the edit/delete options and actions from the list view if the user lacks `attendance.add_attendanceovertime` permission.
* **FAQs Control Actions Hidden** (`skylinx_theme/templates/helpdesk/faq/faq_category_nav.html`):
  - Hidden the "Load FAQs" actions dropdown for regular employees who lack `helpdesk.add_faq` permission.

## 4. UI & Framework Stability Fixes
* **Infinite Recurse Redirect Loop in Profile** (`employee/templates/employee/profile/profile.html`):
  - Solved an infinite redirect loop when accessing the profile page where the active tab would click itself infinitely by introducing a lock variable `isClicking`.
* **Redirect Loop Protection** (`skylinx/http/response.py`):
  - Added safeguard logic to `SkylinxRedirect` to prevent HTTP redirect loops back to the same requested URL, instead redirecting to a safe fallback URL.
* **Dynamic Language Code Initialization** (`employee/views.py`, `employee/urls.py`, `templates/index.html`):
  - Added `/employee/get-language-code/` endpoint to determine the user's active translation language.
  - Initialized `window.CURRENT_LANGUAGE` dynamically inside `index.html` on load, fixing translation issues in local date formats within `actions.js`.
