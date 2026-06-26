#!/bin/bash
# Deploy script for permission fixes
set -e

echo "=== Staging files ==="
git add employee/sidebar.py attendance/sidebar.py leave/sidebar.py payroll/sidebar.py employee/views.py attendance/views/views.py attendance/views/requests.py

echo "=== Committing ==="
git commit -m "fix: restrict sidebar and views to self-service only for regular employees

- employee/sidebar.py: Hide Employees link - changed from view_employee to change_employee
- attendance/sidebar.py: Hide Attendance Requests from regular employees
- leave/sidebar.py: Hide Leave Types and Assign Leave Type from regular employees
- payroll/sidebar.py: Add accessibility for Payslips and Expenses
- employee/views.py: Add filtersubordinates to employee_view (employee.change_employee gate)
- attendance/views/views.py: Change filtersubordinates perms to employee.change_employee (4 calls)
- attendance/views/requests.py: Change filtersubordinates perms to employee.change_employee (2 calls)"

echo "=== Pushing ==="
git push origin 1.0.9.beta

echo "=== Deploying to server ==="
ssh skylinx "cd /home/ubuntu/hrms/hrms_skylinx2.0 && sudo git pull origin 1.0.9.beta && sudo systemctl restart hrms-client && echo 'Server: deployed and restarted'"

echo "=== Done ==="
