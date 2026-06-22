# Documentation of Customized Changes in Skylinx HRMS (Modified by Sandeep)

This document lists all active modifications made to personalize the homepage layout, hide the Shift Roster menu item, and delegate branding/announcement administration to company admins.

---

### 1. Primary Hero Button Rename
- **File:** skylinx_theme/templates/home_page.html
- **Change:** Renamed the dashboard's hero section main CTA button to **"Overview and Analytics"**.
- **Impact:** Aligns dashboard visual entry point with primary reporting modules.

---

### 2. Shift Roster Menu Removal (UI only)
- **File:** employee/sidebar.py
- **Change:** Hardcoded `shift_roster_accessibility` function to return `False`.
- **Impact:** Safely removes the **Shift Roster** option from the sidebar navigation menu globally across all user types without affecting backend scheduling models or core business logic.

---

### 3. Scoped Branding Management (Logo & Social Links)
- **Files Modified:**
  - **Template:** skylinx_theme/templates/home_logo_card.html
  - **Controller/Views:** base/views.py
- **Change:**
  - Enforced RBAC check (`request.user.is_superuser or request.user.has_perm("base.change_company")`) instead of a strict `is_superuser` restriction.
  - Exposes the hover-to-upload card and editable name/links form to authorized company admins and superusers, while hiding them from normal employees.
  - Added a direct edit/pencil button next to the LinkedIn, Facebook, and Instagram social media icons for company admins.
  - Re-routed the local social media link storage file (`base/company_social_links.json`) to write and load links using the logged-in user's company ID key:
    ```json
    {
      "1": {
        "linkedin": "https://linkedin.com/company/company1",
        "facebook": "...",
        "instagram": "..."
      }
    }
    ```
- **Impact:** Individual company admins can upload their company logo, rename their company, and save their social profile links via the edit button, which are loaded dynamically for their employees. Root admin maintains global access.

---

### 4. Scoped Company Announcement Board
- **Files Modified:**
  - **Template:** skylinx_theme/templates/home_announcement.html
  - **Controller/Views:** base/views.py
- **Change:**
  - Allowed superusers and company admins with `base.change_announcement` permissions to click and edit the horizontal scrolling announcement banner.
  - Updates are scoped to the current tenant's active announcement instance.
- **Impact:** Regular employees view their company-specific announcements in read-only mode, while company admins have full update privileges.
