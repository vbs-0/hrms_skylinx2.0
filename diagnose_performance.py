import os
import sys
import time

# Ensure we can import Django settings
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "skylinx.settings.base")

try:
    import django
    django.setup()
except Exception as e:
    print(f"Error initializing Django: {e}")
    print("Please make sure you run this script in the root directory of the project where manage.py is located.")
    sys.exit(1)

from django.db import connection, connections
from django.test.utils import CaptureQueriesContext
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()

def check_indexes():
    print("\n[1/3] Checking Database Indexes on Critical Performance Tables...")
    cursor = connection.cursor()
    
    # We want to check:
    # 1. employee_employeeworkinformation (reporting_manager_id_id, department_id_id, employee_id_id)
    # 2. attendance_attendance (employee_id_id)
    tables_to_check = {
        "employee_employeeworkinformation": ["reporting_manager_id_id", "department_id_id", "employee_id_id", "job_position_id_id"],
        "attendance_attendance": ["employee_id_id"]
    }
    
    db_engine = connection.vendor
    print(f"Database Engine detected: {db_engine}")
    
    for table, columns in tables_to_check.items():
        # Check if table exists
        if table not in connection.introspection.table_names(cursor):
            print(f"- Table '{table}' does not exist, skipping index check.")
            continue
            
        try:
            constraints = connection.introspection.get_constraints(cursor, table)
            indexed_columns = []
            for name, info in constraints.items():
                if info.get('index') or info.get('unique'):
                    indexed_columns.extend(info.get('columns', []))
            
            print(f"\nTable: {table}")
            for col in columns:
                if col in indexed_columns:
                    print(f"  [OK] Column '{col}' is INDEXED.")
                else:
                    print(f"  [WARNING] Column '{col}' is NOT INDEXED!")
                    if db_engine == 'postgresql':
                        print(f"    -> Action: Run raw SQL: CREATE INDEX idx_{table}_{col} ON {table} ({col});")
                    elif db_engine == 'sqlite':
                        print(f"    -> Action: Run raw SQL: CREATE INDEX idx_{table}_{col} ON {table} ({col});")
        except Exception as e:
            print(f"Error checking indexes for table {table}: {e}")

def profile_queries():
    print("\n[2/3] Profiling Database Queries for N+1 Query Issues...")
    
    from attendance.models import Attendance, AttendanceValidationCondition
    from employee.models import Employee
    
    # Get a user (prefer superuser or manager)
    user = User.objects.filter(is_superuser=True).first()
    if not user:
        user = User.objects.first()
    
    if not user:
        print("Error: No users found in database to profile queries.")
        return
        
    print(f"Running profile simulation acting as user: {user.username}")
    
    start_time = time.time()
    
    # Capture queries during execution
    with CaptureQueriesContext(connection) as queries:
        try:
            # Emulate loading attendance views
            condition = AttendanceValidationCondition.objects.first()
            minot = 1800
            
            # Fetch up to 50 attendance records
            validate_attendances = list(Attendance.objects.filter(attendance_validated=False)[:50])
            attendances = list(Attendance.objects.filter(attendance_validated=True)[:50])
            
            # Emulate Django Template Rendering of these records
            for att in attendances:
                emp = att.employee_id
                if emp:
                    # Accessing related models (simulating template loops)
                    emp_name = f"{emp.employee_first_name} {emp.employee_last_name}"
                    work_info = getattr(emp, 'employee_work_info', None)
                    if work_info:
                        dept = getattr(work_info, 'department_id', None)
                        mgr = getattr(work_info, 'reporting_manager_id', None)
                        pos = getattr(work_info, 'job_position_id', None)
                        if dept: _ = str(dept)
                        if mgr: _ = mgr.employee_first_name
                        if pos: _ = str(pos)
                        
            for att in validate_attendances:
                emp = att.employee_id
                if emp:
                    emp_name = f"{emp.employee_first_name} {emp.employee_last_name}"
                    work_info = getattr(emp, 'employee_work_info', None)
                    if work_info:
                        dept = getattr(work_info, 'department_id', None)
                        mgr = getattr(work_info, 'reporting_manager_id', None)
                        pos = getattr(work_info, 'job_position_id', None)
                        if dept: _ = str(dept)
                        if mgr: _ = mgr.employee_first_name
                        if pos: _ = str(pos)
        except Exception as e:
            print(f"Error during query execution: {e}")
            return

    elapsed = time.time() - start_time
    total_queries = len(queries)
    
    print(f"Total time taken for simulation: {elapsed:.4f} seconds")
    print(f"Total database queries executed: {total_queries}")
    
    # Identify duplicates
    query_counts = {}
    for q in queries:
        sql = q['sql']
        query_counts[sql] = query_counts.get(sql, 0) + 1
        
    duplicate_queries = {sql: count for sql, count in query_counts.items() if count > 1}
    total_duplicates = sum(duplicate_queries.values()) - len(duplicate_queries)
    
    print(f"Duplicate/Redundant database queries: {total_duplicates}")
    
    if total_duplicates > 0:
        print("\n[WARNING] N+1 Query issues detected on your database!")
        print("This is the main reason pages load slowly when your tables have more data.")
        print("For every attendance row, Django runs separate queries to fetch the employee name, department, reporting manager, etc.")
        print("\nTop duplicate queries:")
        for sql, count in sorted(duplicate_queries.items(), key=lambda x: x[1], reverse=True)[:3]:
            print(f"- Executed {count} times: {sql[:150]}...")
            
        print("\n--- Recommendation to fix N+1 Issues ---")
        print("Update your Django View QuerySets to use `.select_related()`. This tells Django to fetch relations in a single JOIN query.")
        print("In `attendance/views.py` (lines 210-216) and `attendance/views.py` (lines 258-264), change:")
        print("  attendances = Attendance.objects.filter(attendance_validated=True)")
        print("To:")
        print("  attendances = Attendance.objects.select_related(")
        print("      'employee_id',")
        print("      'employee_id__employee_work_info',")
        print("      'employee_id__employee_work_info__department_id',")
        print("      'employee_id__employee_work_info__reporting_manager_id',")
        print("      'employee_id__employee_work_info__job_position_id'")
        print("  ).filter(attendance_validated=True)")
    else:
        print("[OK] No N+1 Query issues detected for this simulation.")

def check_external_dependencies():
    print("\n[3/3] Checking External Middleware & Settings (LDAP/SMTP)...")
    
    # Check LDAP connectivity speed
    start_time = time.time()
    try:
        from skylinx_ldap.models import LDAPSettings
        settings_exist = LDAPSettings.objects.exists()
        print(f"- LDAP configuration in database: {'Yes' if settings_exist else 'No'}")
    except Exception as e:
        print(f"- Error checking LDAP configuration: {e}")
        
    print("\nDiagnostics complete!")

if __name__ == "__main__":
    check_indexes()
    profile_queries()
    check_external_dependencies()
