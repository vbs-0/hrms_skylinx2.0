"""BUZZ — directory + hierarchy-scoped social chat.

Permission model (Darwinbox-style, "option B"):
an employee can freely message
  - anyone in their own department,
  - their reporting-manager chain upward,
  - their direct/indirect reports downward,
  - HR Managers / Company Admins of their company (and vice versa).
Anyone else in the same company requires an accepted BuzzConnection
("request to connect") first. Cross-company chat is never allowed.
"""

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from employee.models import Employee


def _chain_up_ids(employee, max_depth=10):
    """Ids of the employee's reporting-manager chain, walking upward."""
    ids = []
    seen = set()
    current = employee
    for _i in range(max_depth):
        wi = getattr(current, "employee_work_info", None)
        manager = getattr(wi, "reporting_manager_id", None) if wi else None
        if manager is None or manager.id in seen or manager.id == employee.id:
            break
        ids.append(manager.id)
        seen.add(manager.id)
        current = manager
    return ids


def can_message(sender, target):
    """Option-B gate. Both args are Employee instances. Returns (bool, reason);
    reason is "" when allowed, else a short machine tag:
    'cross_company' | 'needs_connection'."""
    if sender.id == target.id:
        return False, "self"
    s_company = sender.get_company()
    t_company = target.get_company()
    if not s_company or s_company != t_company:
        return False, "cross_company"

    from base.rbac import org_rank, HR_MANAGER_RANK

    # HR / Company Admin / owner can reach everyone (and everyone can reach them)
    s_user = sender.employee_user_id
    t_user = target.employee_user_id
    if (s_user and org_rank(s_user) <= HR_MANAGER_RANK) or (
        t_user and org_rank(t_user) <= HR_MANAGER_RANK
    ):
        return True, ""

    s_wi = getattr(sender, "employee_work_info", None)
    t_wi = getattr(target, "employee_work_info", None)
    s_dept = getattr(s_wi, "department_id_id", None) if s_wi else None
    t_dept = getattr(t_wi, "department_id_id", None) if t_wi else None
    if s_dept and s_dept == t_dept:
        return True, ""

    # manager chain: target above sender, or sender above target
    if target.id in _chain_up_ids(sender) or sender.id in _chain_up_ids(target):
        return True, ""

    if BuzzConnection.objects.filter(
        status="accepted", requester=sender, target=target
    ).exists() or BuzzConnection.objects.filter(
        status="accepted", requester=target, target=sender
    ).exists():
        return True, ""
    return False, "needs_connection"


class BuzzConnection(models.Model):
    """Cross-department 'request to connect' (option B)."""

    STATUS_CHOICES = [
        ("pending", _("Pending")),
        ("accepted", _("Accepted")),
        ("declined", _("Declined")),
    ]

    requester = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="buzz_requests_sent"
    )
    target = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="buzz_requests_received"
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    message = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("requester", "target")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.requester} -> {self.target} ({self.status})"


class BuzzConversation(models.Model):
    """1:1 or group conversation. company_id pins the tenant; every
    participant must belong to it."""

    company_id = models.ForeignKey(
        "base.Company", on_delete=models.CASCADE, related_name="buzz_conversations"
    )
    is_group = models.BooleanField(default=False)
    title = models.CharField(max_length=100, blank=True, default="")
    created_by = models.ForeignKey(
        Employee, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def display_title(self, for_employee=None):
        if self.is_group:
            return self.title or "Group"
        others = self.participants.exclude(employee=for_employee) if for_employee else self.participants.all()
        p = others.select_related("employee").first()
        return p.employee.get_full_name() if p else "Conversation"

    def __str__(self):
        return self.title or f"Conversation {self.pk}"


class BuzzParticipant(models.Model):
    conversation = models.ForeignKey(
        BuzzConversation, on_delete=models.CASCADE, related_name="participants"
    )
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="buzz_participations"
    )
    last_read_at = models.DateTimeField(default=timezone.now)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("conversation", "employee")]

    def unread_count(self):
        return self.conversation.messages.filter(
            created_at__gt=self.last_read_at
        ).exclude(sender=self.employee).count()


class BuzzMessage(models.Model):
    conversation = models.ForeignKey(
        BuzzConversation, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        Employee, null=True, on_delete=models.SET_NULL, related_name="buzz_messages"
    )
    body = models.TextField(max_length=4000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sender}: {self.body[:40]}"
