# Skylinx HRMS

[![License: LGPL v2.1](https://img.shields.io/badge/License-LGPL%20v2.1-blue.svg)](https://www.gnu.org/licenses/lgpl-2.1)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Django](https://img.shields.io/badge/django-5.0+-green.svg)](https://www.djangoproject.com/)

> **A comprehensive, free, and open-source Human Resource Management System (HRMS) designed to streamline HR operations and enhance organizational efficiency.**

## Features

### Core HR Modules
- Employee Management – centralized workforce data with LDAP integration
- Recruitment – end-to-end hiring from job posting to onboarding
- Onboarding & Offboarding – structured employee-lifecycle workflows
- Attendance & Time Tracking – biometric integration and automated check-in/out
- Leave Management – policy enforcement, approvals, and balance tracking
- Payroll – automated salary processing, tax calculations, and compliance
- Performance Management – goal setting, reviews, and continuous feedback
- Asset Management – track and manage company resources
- Helpdesk – centralized support and ticketing
- Project & Task Management – projects, tasks, and timesheets

## Quick Start

### Using Docker (Recommended)

```bash
git clone <your-repo-url> skylinx_hrms
cd skylinx_hrms
docker-compose up -d
# open http://localhost:8000
```

### Manual Installation

```bash
git clone <your-repo-url> skylinx_hrms
cd skylinx_hrms

# Virtual environment
python3 -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate

# Dependencies
pip install -r requirements.txt

# Environment
cp .env.dist .env                   # then edit .env with your settings

# Database & assets
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic --noinput

# Run
python manage.py runserver          # http://localhost:8000
```

## Security

- Role-based access control
- Encrypted sensitive data storage
- Comprehensive audit trails
- XSS and injection protection
- Secure session management

Always use HTTPS in production, keep dependencies updated, and enable 2FA.

## License

This project is licensed under the LGPL-2.1 License – see the LICENSE file for details.

---

**Skylinx HRMS**
