"""Functional tests for BUZZ option-B permissions and chat flow."""

from django.contrib.auth import get_user_model
from django.test import TestCase

from base.models import Company, Department, JobPosition
from buzz.models import BuzzConnection, can_message
from employee.models import Employee, EmployeeWorkInformation

User = get_user_model()


def make_emp(first, company, dept, manager=None):
    emp = Employee(
        employee_first_name=first,
        employee_last_name="T",
        email=f"{first.lower()}@test.local",
        phone="9876543210",
    )
    emp.save()
    wi = getattr(emp, "employee_work_info", None) or EmployeeWorkInformation(employee_id=emp)
    wi.employee_id = emp
    wi.company_id = company
    wi.department_id = dept
    wi.reporting_manager_id = manager
    wi.save()
    emp.refresh_from_db()
    return emp


class CanMessageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(company="TestCo", address="x", country="x", city="x", zip="1")
        cls.other_company = Company.objects.create(company="OtherCo", address="x", country="x", city="x", zip="2")
        cls.eng = Department.objects.create(department="Engineering")
        cls.sales = Department.objects.create(department="Sales")

        cls.manager = make_emp("Manager", cls.company, cls.eng)
        cls.dev1 = make_emp("DevOne", cls.company, cls.eng, manager=cls.manager)
        cls.dev2 = make_emp("DevTwo", cls.company, cls.eng, manager=cls.manager)
        cls.sales1 = make_emp("SalesOne", cls.company, cls.sales)
        cls.outsider = make_emp("Outsider", cls.other_company, cls.eng)

    def test_same_department_allowed(self):
        ok, reason = can_message(self.dev1, self.dev2)
        self.assertTrue(ok)

    def test_manager_chain_allowed_both_ways(self):
        self.assertTrue(can_message(self.dev1, self.manager)[0])
        self.assertTrue(can_message(self.manager, self.dev1)[0])

    def test_cross_department_needs_connection(self):
        ok, reason = can_message(self.dev1, self.sales1)
        self.assertFalse(ok)
        self.assertEqual(reason, "needs_connection")

    def test_accepted_connection_allows(self):
        BuzzConnection.objects.create(requester=self.dev1, target=self.sales1, status="accepted")
        self.assertTrue(can_message(self.dev1, self.sales1)[0])
        self.assertTrue(can_message(self.sales1, self.dev1)[0])

    def test_cross_company_never(self):
        ok, reason = can_message(self.dev1, self.outsider)
        self.assertFalse(ok)
        self.assertEqual(reason, "cross_company")

    def test_self_blocked(self):
        self.assertFalse(can_message(self.dev1, self.dev1)[0])


class ChatAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(company="TestCo", address="x", country="x", city="x", zip="1")
        cls.eng = Department.objects.create(department="Engineering")
        cls.sales = Department.objects.create(department="Sales")
        cls.a = make_emp("Alice", cls.company, cls.eng)
        cls.b = make_emp("Bob", cls.company, cls.eng)
        cls.c = make_emp("Carol", cls.company, cls.sales)
        for emp, uname in ((cls.a, "alice"), (cls.b, "bob"), (cls.c, "carol")):
            user = User.objects.create_user(username=uname, password="x12345678")
            emp.employee_user_id = user
            emp.save()

    def _login(self, name):
        self.client.force_login(User.objects.get(username=name))

    def test_full_chat_flow(self):
        self._login("alice")
        r = self.client.post(
            "/api/v1/buzz/conversations/", {"employee_id": self.b.id},
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 201)
        conv_id = r.json()["id"]

        r = self.client.post(
            f"/api/v1/buzz/conversations/{conv_id}/messages/", {"body": "hello bob"},
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 201)

        # duplicate open returns same conversation
        r = self.client.post(
            "/api/v1/buzz/conversations/", {"employee_id": self.b.id},
            content_type="application/json",
        )
        self.assertEqual(r.json()["id"], conv_id)

        # bob sees it with 1 unread and can read
        self._login("bob")
        r = self.client.get("/api/v1/buzz/conversations/")
        convs = r.json()["results"]
        self.assertEqual(len(convs), 1)
        self.assertEqual(convs[0]["unread"], 1)
        r = self.client.get(f"/api/v1/buzz/conversations/{conv_id}/messages/")
        self.assertEqual(r.json()["results"][0]["body"], "hello bob")

        # carol (cross-dept) can't open a chat with alice
        self._login("carol")
        r = self.client.post(
            "/api/v1/buzz/conversations/", {"employee_id": self.a.id},
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.json()["reason"], "needs_connection")

        # carol can't read alice+bob's messages
        r = self.client.get(f"/api/v1/buzz/conversations/{conv_id}/messages/")
        self.assertEqual(r.status_code, 404)

        # request → accept → chat opens
        r = self.client.post(
            "/api/v1/buzz/connections/", {"employee_id": self.a.id, "message": "hi"},
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 201)
        conn_id = r.json()["id"]

        self._login("alice")
        r = self.client.get("/api/v1/buzz/connections/")
        self.assertEqual(len(r.json()["results"]), 1)
        r = self.client.post(
            "/api/v1/buzz/connections/", {"connection_id": conn_id, "action": "accept"},
            content_type="application/json",
        )
        self.assertEqual(r.json()["status"], "accepted")

        self._login("carol")
        r = self.client.post(
            "/api/v1/buzz/conversations/", {"employee_id": self.a.id},
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 201)

    def test_directory_lists_company_only(self):
        self._login("alice")
        r = self.client.get("/api/v1/buzz/directory/")
        names = {p["name"] for p in r.json()["results"]}
        self.assertIn("Bob T", names)
        self.assertIn("Carol T", names)
        bob = next(p for p in r.json()["results"] if p["name"] == "Bob T")
        carol = next(p for p in r.json()["results"] if p["name"] == "Carol T")
        self.assertTrue(bob["can_message"])
        self.assertFalse(carol["can_message"])
        self.assertEqual(carol["reason"], "needs_connection")
