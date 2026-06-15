# **Skylinx HRMS**

**Skylinx HRMS** is a Free and Open Source HRMS (Human Resource Management System) platform designed to streamline HR processes and enhance organizational efficiency. It brings recruitment, onboarding, employee management, attendance, leave, payroll, performance, helpdesk, assets, and offboarding together in one modern, modular application.

## **Modules**

- **Recruitment** – manage vacancies, candidates, interviews, and hiring pipelines.
- **Onboarding** – structured onboarding flows for new hires.
- **Employee** – central employee directory and profile management.
- **Attendance** – clock in/out, shifts, biometric and geofencing support.
- **Leave** – leave types, requests, approvals, and balances.
- **Payroll** – contracts, allowances, deductions, and payslips.
- **Performance (PMS)** – objectives, key results, and feedback.
- **Helpdesk** – internal ticketing and support.
- **Assets** – asset allocation, requests, and tracking.
- **Offboarding** – resignation and exit management.
- **Project** – project and task management with timesheets.

## **Requirements**

Ensure you have the following installed:

- **Python** 3.10+
- **Django**
- A **database** (PostgreSQL recommended)

## **Installation**

```bash
# 1. Clone your repository
git clone <your-repo-url> skylinx_hrms
cd skylinx_hrms

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: .\venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.dist .env
# edit .env with your database and secret settings

# 5. Apply migrations
python3 manage.py migrate

# 6. Create an admin user
python3 manage.py createskylinxuser \
  --first_name admin --last_name admin --username admin \
  --password admin --email admin@example.com --phone 1234567890

# 7. Run the development server
python3 manage.py runserver
```

> Note: the `createskylinxuser` command initializes an admin user along with default company, department, and job position records.

## **Accessing the application**

Once running, open **http://localhost:8000** in your browser.

To run on a different port:

```bash
python3 manage.py runserver 8080
```

## **Docker**

```bash
docker compose up --build
```

See `docker.md` for details.

## **License**

This project is distributed under the LGPL License. See the `LICENSE` file for details.

---

Happy building with **Skylinx HRMS**! 🚀
