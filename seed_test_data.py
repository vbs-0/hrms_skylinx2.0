import os
import sys
import django
from datetime import date

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'skylinx.settings')
django.setup()

from django.apps import apps
from django.db import transaction, connection
from seed_india_tax_regimes import seed_tax_regimes

def assign_company(instance, company):
    if hasattr(instance, 'company_id'):
        field = instance._meta.get_field('company_id')
        if field.many_to_many:
            instance.company_id.set([company])
        else:
            instance.company_id = company
            instance.save()

def clear_and_seed():
    print("Starting database cleanup and seeding...")
    
    db_engine = connection.vendor
    if db_engine == 'sqlite':
        with connection.cursor() as cursor:
            cursor.execute('PRAGMA foreign_keys = OFF;')
            print("Disabled foreign key checks for SQLite.")

    # 1. Clear existing transactional / employee-related data via raw SQL
    models_to_clear = [
        ('payroll', 'Payslip'),
        ('payroll', 'Contract'),
        ('payroll', 'LoanAccount'),
        ('payroll', 'Reimbursement'),
        ('attendance', 'AttendanceActivity'),
        ('attendance', 'AttendanceOverTime'),
        ('attendance', 'AttendanceLateComeEarlyOut'),
        ('attendance', 'Attendance'),
        ('attendance', 'WorkRecords'),
        ('leave', 'LeaveRequest'),
        ('leave', 'LeaveAllocationRequest'),
        ('leave', 'AvailableLeave'),
        ('project', 'TimeSheet'),
        ('project', 'Task'),
        ('project', 'Project'),
        ('asset', 'AssetAssignment'),
        ('asset', 'AssetRequest'),
        ('asset', 'Asset'),
        ('offboarding', 'OffboardingEmployee'),
        ('offboarding', 'Offboarding'),
        ('onboarding', 'CandidateTask'),
        ('onboarding', 'OnboardingTask'),
        ('onboarding', 'OnboardingStage'),
        ('onboarding', 'OnboardingCandidate'),
        ('employee', 'EmployeeNote'),
        ('employee', 'DisciplinaryAction'),
        ('employee', 'BonusPoint'),
        ('employee', 'EmployeeBankDetails'),
        ('employee', 'EmployeeWorkInformation'),
        ('employee', 'Employee'),
        ('facedetection', 'EmployeeFaceDetection'),
        ('facedetection', 'FaceDetection'),
        ('biometric', 'BiometricEmployees'),
        ('base', 'Roster'),
        ('base', 'ShiftRequest'),
        ('base', 'WorkTypeRequest'),
        ('base', 'Announcement'),
        ('helpdesk', 'Ticket'),
        ('helpdesk', 'DepartmentManager'),
        ('recruitment', 'Candidate'),
        ('skylinx_documents', 'Document'),
        ('skylinx_documents', 'DocumentRequest'),
        ('base', 'JobRole'),
        ('base', 'JobPosition'),
        ('base', 'Department'),
        ('base', 'WorkType'),
        ('base', 'EmployeeType'),
        ('base', 'EmployeeShift'),
    ]

    for app_label, model_name in models_to_clear:
        try:
            model = apps.get_model(app_label, model_name)
            table_name = model._meta.db_table
            with connection.cursor() as cursor:
                cursor.execute(f"DELETE FROM {table_name};")
            print(f"Cleared table {table_name}")
        except Exception as e:
            print(f"Skipped/Error clearing table for {app_label}.{model_name}: {e}")

    # Delete SkylinxUsers (except superusers/staff or admin)
    try:
        SkylinxUser = apps.get_model('skylinx_auth', 'SkylinxUser')
        users_to_delete = SkylinxUser.objects.filter(is_superuser=False, is_staff=False).exclude(username='admin')
        count = users_to_delete.count()
        # Delete via raw SQL to avoid cascade protected errors
        user_table = SkylinxUser._meta.db_table
        user_ids = list(users_to_delete.values_list('id', flat=True))
        if user_ids:
            with connection.cursor() as cursor:
                # Convert list to string tuple format
                ids_str = ",".join(str(uid) for uid in user_ids)
                cursor.execute(f"DELETE FROM {user_table} WHERE id IN ({ids_str});")
            print(f"Cleared {count} non-admin users via SQL.")
        else:
            print("No non-admin users to clear.")
    except Exception as e:
        print(f"Error clearing users: {e}")

    try:
        with transaction.atomic():
            # Run tax regime seeding to populate FilingStatus
            try:
                seed_tax_regimes()
            except Exception as e:
                print(f"Error seeding tax regimes: {e}")

            # 2. Seed Base Metadata
            print("Creating base metadata...")
            Company = apps.get_model('base', 'Company')
            company, _ = Company.objects.get_or_create(id=1, defaults={"company": "Skylinx"})
            
            Department = apps.get_model('base', 'Department')
            departments = {}
            for dept_name in ["HR", "Engineering", "Sales", "Finance"]:
                dept, _ = Department.objects.get_or_create(department=dept_name)
                assign_company(dept, company)
                departments[dept_name] = dept

            JobPosition = apps.get_model('base', 'JobPosition')
            positions = {}
            position_list = [
                ("HR Manager", "HR"),
                ("HR Executive", "HR"),
                ("Software Engineer", "Engineering"),
                ("Frontend Developer", "Engineering"),
                ("Engineering Manager", "Engineering"),
                ("Tester", "Engineering"),
                ("Sales Executive", "Sales"),
                ("Accountant", "Finance")
            ]
            for pos_name, dept_name in position_list:
                pos, _ = JobPosition.objects.get_or_create(
                    job_position=pos_name,
                    defaults={"department_id": departments[dept_name]}
                )
                positions[pos_name] = pos

            JobRole = apps.get_model('base', 'JobRole')
            roles = {}
            role_list = [
                ("Manager", "HR Manager"),
                ("Recruiter", "HR Executive"),
                ("Backend Developer", "Software Engineer"),
                ("UI Developer", "Frontend Developer"),
                ("Leadership", "Engineering Manager"),
                ("Support", "Tester"),
                ("Field Sales", "Sales Executive"),
                ("Finance Executive", "Accountant")
            ]
            for role_name, pos_name in role_list:
                role, _ = JobRole.objects.get_or_create(
                    job_role=role_name,
                    defaults={"job_position_id": positions[pos_name]}
                )
                roles[role_name] = role

            WorkType = apps.get_model('base', 'WorkType')
            work_types = {}
            for wt_name in ["Office", "Remote", "Hybrid"]:
                wt, _ = WorkType.objects.get_or_create(work_type=wt_name)
                assign_company(wt, company)
                work_types[wt_name] = wt

            EmployeeType = apps.get_model('base', 'EmployeeType')
            employee_types = {}
            for et_name in ["Permanent", "Contract"]:
                et, _ = EmployeeType.objects.get_or_create(employee_type=et_name)
                employee_types[et_name] = et

            EmployeeShift = apps.get_model('base', 'EmployeeShift')
            shifts = {}
            for shift_name in ["General Shift", "Morning Shift"]:
                shift, _ = EmployeeShift.objects.get_or_create(employee_shift=shift_name)
                shifts[shift_name] = shift

            # 3. Seed 8 Employees
            print("Creating 8 employees...")
            Employee = apps.get_model('employee', 'Employee')
            EmployeeWorkInformation = apps.get_model('employee', 'EmployeeWorkInformation')
            EmployeeBankDetails = apps.get_model('employee', 'EmployeeBankDetails')
            SkylinxUser = apps.get_model('skylinx_auth', 'SkylinxUser')

            specs = [
                {
                    "username": "priya.sharma",
                    "first_name": "Priya",
                    "last_name": "Sharma",
                    "email": "priya.sharma@skylinx.com",
                    "phone": "+919876543210",
                    "gender": "female",
                    "dob": date(1988, 5, 12),
                    "qualification": "MBA in HR",
                    "experience": 8,
                    "marital_status": "married",
                    "pan": "ABCPS1234F",
                    "aadhaar": "987654321012",
                    "dept": "HR",
                    "pos": "HR Manager",
                    "role": "Manager",
                    "salary": 1800000,
                    "bank": "HDFC Bank",
                    "ifsc": "HDFC0000001",
                    "acc_num": "50100203040506",
                    "branch": "Mumbai Main Branch",
                    "manager_uname": None
                },
                {
                    "username": "rajesh.patel",
                    "first_name": "Rajesh",
                    "last_name": "Patel",
                    "email": "rajesh.patel@skylinx.com",
                    "phone": "+919876543211",
                    "gender": "male",
                    "dob": date(1993, 10, 24),
                    "qualification": "BBA",
                    "experience": 3,
                    "marital_status": "single",
                    "pan": "ABCPP5678G",
                    "aadhaar": "123456789012",
                    "dept": "HR",
                    "pos": "HR Executive",
                    "role": "Recruiter",
                    "salary": 600000,
                    "bank": "State Bank of India",
                    "ifsc": "SBIN0001608",
                    "acc_num": "30123456789",
                    "branch": "Bhopal Main Branch",
                    "manager_uname": "priya.sharma"
                },
                {
                    "username": "vikram.singh",
                    "first_name": "Vikram",
                    "last_name": "Singh",
                    "email": "vikram.singh@skylinx.com",
                    "phone": "+919876543212",
                    "gender": "male",
                    "dob": date(1985, 3, 15),
                    "qualification": "M.Tech",
                    "experience": 12,
                    "marital_status": "married",
                    "pan": "ABCVS2468H",
                    "aadhaar": "246813579024",
                    "dept": "Engineering",
                    "pos": "Engineering Manager",
                    "role": "Leadership",
                    "salary": 2400000,
                    "bank": "ICICI Bank",
                    "ifsc": "ICIC0000002",
                    "acc_num": "000201020304",
                    "branch": "Pune Main Branch",
                    "manager_uname": None
                },
                {
                    "username": "amit.verma",
                    "first_name": "Amit",
                    "last_name": "Verma",
                    "email": "amit.verma@skylinx.com",
                    "phone": "+919876543213",
                    "gender": "male",
                    "dob": date(1995, 7, 19),
                    "qualification": "B.Tech CSE",
                    "experience": 4,
                    "marital_status": "single",
                    "pan": "ABCAV1357I",
                    "aadhaar": "135792468013",
                    "dept": "Engineering",
                    "pos": "Software Engineer",
                    "role": "Backend Developer",
                    "salary": 1200000,
                    "bank": "Axis Bank",
                    "ifsc": "UTIB0000003",
                    "acc_num": "913010020030040",
                    "branch": "Bengaluru Main Branch",
                    "manager_uname": "vikram.singh"
                },
                {
                    "username": "sneha.reddy",
                    "first_name": "Sneha",
                    "last_name": "Reddy",
                    "email": "sneha.reddy@skylinx.com",
                    "phone": "+919876543214",
                    "gender": "female",
                    "dob": date(1997, 12, 5),
                    "qualification": "B.E. Information Technology",
                    "experience": 2,
                    "marital_status": "single",
                    "pan": "ABCSR9876J",
                    "aadhaar": "987612345098",
                    "dept": "Engineering",
                    "pos": "Frontend Developer",
                    "role": "UI Developer",
                    "salary": 800000,
                    "bank": "HDFC Bank",
                    "ifsc": "HDFC0000001",
                    "acc_num": "50100908070605",
                    "branch": "Hyderabad Main Branch",
                    "manager_uname": "vikram.singh"
                },
                {
                    "username": "anjali.gupta",
                    "first_name": "Anjali",
                    "last_name": "Gupta",
                    "email": "anjali.gupta@skylinx.com",
                    "phone": "+919876543215",
                    "gender": "female",
                    "dob": date(1994, 2, 28),
                    "qualification": "MCA",
                    "experience": 5,
                    "marital_status": "married",
                    "pan": "ABCAG4321K",
                    "aadhaar": "432109876543",
                    "dept": "Engineering",
                    "pos": "Tester",
                    "role": "Support",
                    "salary": 750000,
                    "bank": "State Bank of India",
                    "ifsc": "SBIN0001608",
                    "acc_num": "30987654321",
                    "branch": "Bhopal Main Branch",
                    "manager_uname": "vikram.singh"
                },
                {
                    "username": "rohan.mehta",
                    "first_name": "Rohan",
                    "last_name": "Mehta",
                    "email": "rohan.mehta@skylinx.com",
                    "phone": "+919876543216",
                    "gender": "male",
                    "dob": date(1991, 9, 8),
                    "qualification": "MBA in Sales & Marketing",
                    "experience": 6,
                    "marital_status": "married",
                    "pan": "ABCRM6789L",
                    "aadhaar": "678901234567",
                    "dept": "Sales",
                    "pos": "Sales Executive",
                    "role": "Field Sales",
                    "salary": 900000,
                    "bank": "ICICI Bank",
                    "ifsc": "ICIC0000002",
                    "acc_num": "000205060708",
                    "branch": "Delhi Main Branch",
                    "manager_uname": "priya.sharma"
                },
                {
                    "username": "kavita.joshi",
                    "first_name": "Kavita",
                    "last_name": "Joshi",
                    "email": "kavita.joshi@skylinx.com",
                    "phone": "+919876543217",
                    "gender": "female",
                    "dob": date(1990, 4, 30),
                    "qualification": "M.Com",
                    "experience": 7,
                    "marital_status": "married",
                    "pan": "ABCKJ1122M",
                    "aadhaar": "112233445566",
                    "dept": "Finance",
                    "pos": "Accountant",
                    "role": "Finance Executive",
                    "salary": 1000000,
                    "bank": "Axis Bank",
                    "ifsc": "UTIB0000003",
                    "acc_num": "913010090080070",
                    "branch": "Mumbai Main Branch",
                    "manager_uname": "priya.sharma"
                }
            ]

            employee_map = {}
            badge_counter = 1001

            # Create user accounts and Employee records first
            for spec in specs:
                # Create User
                user, created = SkylinxUser.objects.get_or_create(
                    username=spec["username"],
                    defaults={
                        "email": spec["email"],
                        "is_active": True,
                        "first_name": spec["first_name"],
                        "last_name": spec["last_name"]
                    }
                )
                if created:
                    user.set_password("Skylinx@123")
                    user.save()
                    print(f"Created SkylinxUser: {spec['username']}")

                # Create Employee
                employee = Employee.objects.create(
                    badge_id=str(badge_counter),
                    employee_first_name=spec["first_name"],
                    employee_last_name=spec["last_name"],
                    email=spec["email"],
                    phone=spec["phone"],
                    gender=spec["gender"],
                    dob=spec["dob"],
                    country="India",
                    state="Maharashtra" if "Mumbai" in spec["branch"] or "Pune" in spec["branch"] else "Madhya Pradesh",
                    city="Mumbai" if "Mumbai" in spec["branch"] else ("Pune" if "Pune" in spec["branch"] else "Bhopal"),
                    address="456 corporate avenue",
                    zip="400001" if "Mumbai" in spec["branch"] else "462001",
                    qualification=spec["qualification"],
                    experience=spec["experience"],
                    marital_status=spec["marital_status"],
                    children=1 if spec["marital_status"] == "married" else 0,
                    emergency_contact="+919876500000",
                    emergency_contact_name="Family Member",
                    emergency_contact_relation="Spouse" if spec["marital_status"] == "married" else "Parent",
                    pan_number=spec["pan"],
                    aadhaar_number=spec["aadhaar"],
                    account_type="savings",
                    is_active=True,
                    employee_user_id=user
                )
                employee_map[spec["username"]] = employee
                badge_counter += 1
                print(f"Created Employee: {spec['first_name']} {spec['last_name']}")

            # Set up work info and bank details
            for spec in specs:
                emp = employee_map[spec["username"]]
                
                # Find manager
                manager = None
                if spec["manager_uname"]:
                    manager = employee_map.get(spec["manager_uname"])

                # Get or create Work Info (handles auto-creation signals)
                work_info, _ = EmployeeWorkInformation.objects.get_or_create(employee_id=emp)
                work_info.company_id = company
                work_info.department_id = departments[spec["dept"]]
                work_info.job_position_id = positions[spec["pos"]]
                work_info.job_role_id = roles[spec["role"]]
                work_info.reporting_manager_id = manager
                work_info.work_type_id = work_types["Office"]
                work_info.employee_type_id = employee_types["Permanent"]
                work_info.shift_id = shifts["General Shift"]
                work_info.location = emp.city
                work_info.email = spec["email"]
                work_info.mobile = spec["phone"]
                work_info.date_joining = date(2024, 1, 15)
                work_info.basic_salary = spec["salary"]
                work_info.experience = float(spec["experience"])
                work_info.save()

                # Get or create Bank Details (handles auto-creation signals)
                bank_details, _ = EmployeeBankDetails.objects.get_or_create(employee_id=emp)
                bank_details.bank_name = spec["bank"]
                bank_details.account_number = spec["acc_num"]
                bank_details.branch = spec["branch"]
                bank_details.address = f"{spec['branch']}, India"
                bank_details.country = "India"
                bank_details.state = emp.state
                bank_details.city = emp.city
                bank_details.any_other_code1 = spec["ifsc"]
                bank_details.is_active = True
                bank_details.save()

                # Create a simple active contract to allow payslips and payroll features to work!
                Contract = apps.get_model('payroll', 'Contract')
                Contract.objects.create(
                    employee_id=emp,
                    contract_name=f"Contract - {emp.employee_first_name}",
                    contract_status="active",
                    contract_start_date=date(2024, 1, 15),
                    wage=float(spec["salary"]) / 12.0, # Monthly base wage
                    filing_status=apps.get_model('payroll', 'FilingStatus').objects.filter(filing_status="New Regime").first()
                )

            # 4. Ensure admin has an employee profile (fixes Initialize Database screen)
            print("Ensuring admin has an employee profile...")
            admin_users = SkylinxUser.objects.filter(is_superuser=True)
            for admin_user in admin_users:
                if not hasattr(admin_user, 'employee_get'):
                    admin_emp = Employee.objects.create(
                        employee_user_id=admin_user,
                        employee_first_name=admin_user.first_name or "Admin",
                        employee_last_name=admin_user.last_name or "User",
                        badge_id=f"ADMIN{admin_user.id}",
                        email=admin_user.email or "admin@example.com",
                        is_active=True,
                        country="India"
                    )
                    # Create base work info
                    work_info, _ = EmployeeWorkInformation.objects.get_or_create(employee_id=admin_emp)
                    work_info.company_id = company
                    work_info.save()
                    print(f"Restored employee profile for admin: {admin_user.username}")

    finally:
        if db_engine == 'sqlite':
            with connection.cursor() as cursor:
                cursor.execute('PRAGMA foreign_keys = ON;')
                print("Re-enabled foreign key checks for SQLite.")

    print("Database cleanup and seeding completed successfully!")

if __name__ == '__main__':
    clear_and_seed()
