import sqlite3

c = sqlite3.connect("db.sqlite3")
cur = c.cursor()

cur.execute("SELECT count(*) FROM employee_employee WHERE is_active=1")
print("active employees:", cur.fetchone()[0])

# reporting manager lives on employee_employeeworkinformation
cur.execute("PRAGMA table_info(employee_employeeworkinformation)")
cols = [r[1] for r in cur.fetchall()]
print("workinfo cols with 'manag':", [x for x in cols if "manag" in x.lower()])
print("workinfo cols with 'report':", [x for x in cols if "report" in x.lower()])

mgr_col = next((x for x in cols if "report" in x.lower() and "manager" in x.lower()), None)
print("using manager column:", mgr_col)
cur.execute(
    f"""
    SELECT e.id,
           e.employee_first_name || ' ' || coalesce(e.employee_last_name,''),
           wi.{mgr_col}
    FROM employee_employee e
    LEFT JOIN employee_employeeworkinformation wi ON wi.employee_id_id = e.id
    WHERE e.is_active=1
    ORDER BY e.id
    """
)
rows = cur.fetchall()
with_mgr = [r for r in rows if r[2]]
print("total rows:", len(rows))
print("with reporting manager:", len(with_mgr))
print("without (roots):", len(rows) - len(with_mgr))
print("--- first 30 ---")
for r in rows[:30]:
    print(r[0], r[1], "-> mgr_id:", r[2])
