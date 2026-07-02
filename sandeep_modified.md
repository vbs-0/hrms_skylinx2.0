# Documentation of Customized Changes in Skylinx HRMS (Modified by Sandeep)

This document lists the active modifications made to personalize the HRMS application.

---

### 1. Decoupling and Migration of Employee Compensation Data (CTC & Basic %)
- **Files Modified:**
  - **Employee CBV/Views:**
    - [employee_profile.py](file:///e:/HRMS13/hrms_skylinx2.0-13.0.0.beta/hrms_skylinx2.0-13.0.0.beta/employee/cbv/employee_profile.py)
    - [views.py (Employee)](file:///e:/HRMS13/hrms_skylinx2.0-13.0.0.beta/hrms_skylinx2.0-13.0.0.beta/employee/views.py)
  - **Employee Templates:**
    - [form_view.html](file:///e:/HRMS13/hrms_skylinx2.0-13.0.0.beta/hrms_skylinx2.0-13.0.0.beta/skylinx_theme/templates/employee/update_form/form_view.html)
    - [form_view_fragment.html](file:///e:/HRMS13/hrms_skylinx2.0-13.0.0.beta/hrms_skylinx2.0-13.0.0.beta/skylinx_theme/templates/employee/update_form/form_view_fragment.html)
  - **Payroll Controller/Forms/Models:**
    - [forms.py](file:///e:/HRMS13/hrms_skylinx2.0-13.0.0.beta/hrms_skylinx2.0-13.0.0.beta/payroll/forms/forms.py)
    - [views.py (Payroll)](file:///e:/HRMS13/hrms_skylinx2.0-13.0.0.beta/hrms_skylinx2.0-13.0.0.beta/payroll/views/views.py)
    - [contracts.py](file:///e:/HRMS13/hrms_skylinx2.0-13.0.0.beta/hrms_skylinx2.0-13.0.0.beta/payroll/cbv/contracts.py)
    - [models.py](file:///e:/HRMS13/hrms_skylinx2.0-13.0.0.beta/hrms_skylinx2.0-13.0.0.beta/payroll/models/models.py)
  - **Payroll Templates:**
    - [form.html](file:///e:/HRMS13/hrms_skylinx2.0-13.0.0.beta/hrms_skylinx2.0-13.0.0.beta/payroll/templates/payroll/common/form.html)
    - [form_fragment.html](file:///e:/HRMS13/hrms_skylinx2.0-13.0.0.beta/hrms_skylinx2.0-13.0.0.beta/payroll/templates/payroll/common/form_fragment.html)
    - [contract_single_view.html](file:///e:/HRMS13/hrms_skylinx2.0-13.0.0.beta/hrms_skylinx2.0-13.0.0.beta/payroll/templates/payroll/contract/contract_single_view.html)

- **Change Details:**
  - **UI Access Restricting**: Removed the "Compensation" tab from the general Employee Profile view and profile-updating logic, restricting financial editing access.
  - **Form Gating**: Migrated the editing of sensitive parameters (`ctc` and `basic_pct`) into the permission-gated `ContractForm` (Pay Register).
  - **Auto-Population & Live Wage Calculation**: Added fields to the AJAX contract helper view and templates so that selecting an employee pre-fills their individual CTC and Basic % on the fly. Included a live Javascript calculation to automatically set the monthly basic salary:
    $$\text{Monthly Wage} = \text{round}\left(\frac{\text{CTC}}{12} \times \frac{\text{Basic \%}}{100}\right)$$
  - **Database Persistence**: Form saving is sequenced to save the contract instance first, then update the employee's `EmployeeWorkInformation` model (where `ctc` and `salary_components` JSON are stored), avoiding signal collisions.
  - **Detailed views**: Exposed CTC and Basic % in `ContractsDetailView` attributes list and the detailed single contract view modal.

- **Impact:** Gates sensitive financial data (CTC and Basic %) within the Payroll module under the `payroll.view_contract` and `payroll.change_contract` permissions. Maintains dynamic, customized salary structure calculations per employee.
