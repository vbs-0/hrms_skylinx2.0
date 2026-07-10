"""BUZZ API + web page. One set of DRF endpoints serves both the web chat
page (session auth) and the Flutter app (JWT) — no duplicated logic."""

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render
from django.utils import timezone
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from buzz.models import (
    BuzzConnection,
    BuzzConversation,
    BuzzMessage,
    BuzzParticipant,
    can_message,
)
from employee.models import Employee
from skylinx_api.auth import CompanyScopedJWTAuthentication


def _me(request):
    try:
        return request.user.employee_get
    except Exception:
        return None


def _notify(recipient_employee, actor_user, verb, description):
    """In-app notification (rides the existing FCM push signal)."""
    try:
        from django.contrib.contenttypes.models import ContentType
        from notifications.models import Notification

        recipient = recipient_employee.employee_user_id
        if not recipient:
            return
        Notification.objects.create(
            recipient=recipient,
            actor_content_type=ContentType.objects.get_for_model(actor_user),
            actor_object_id=str(actor_user.id),
            verb=verb,
            description=description,
            level="info",
        )
    except Exception:
        pass


class BuzzAPIView(APIView):
    authentication_classes = (CompanyScopedJWTAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)


def _emp_payload(e, me=None):
    wi = getattr(e, "employee_work_info", None)
    allowed, reason = (True, "") if me is None else can_message(me, e)
    return {
        "id": e.id,
        "name": e.get_full_name(),
        "avatar": e.get_avatar(),
        "department": str(getattr(wi, "department_id", "") or ""),
        "job_position": str(getattr(wi, "job_position_id", "") or ""),
        "can_message": allowed,
        "reason": reason,
    }


class DirectoryAPIView(BuzzAPIView):
    """Company directory with per-person 'can I message them' flag."""

    def get(self, request):
        me = _me(request)
        if me is None:
            return Response({"error": "Not an employee."}, status=400)
        company = me.get_company()
        q = request.GET.get("q", "").strip()
        qs = Employee.objects.filter(
            is_active=True, employee_work_info__company_id=company
        ).select_related(
            "employee_work_info__department_id",
            "employee_work_info__job_position_id",
        )
        if q:
            qs = qs.filter(
                Q(employee_first_name__icontains=q)
                | Q(employee_last_name__icontains=q)
                | Q(employee_work_info__department_id__department__icontains=q)
                | Q(employee_work_info__job_position_id__job_position__icontains=q)
            )
        pending_out = set(
            BuzzConnection.objects.filter(requester=me, status="pending").values_list(
                "target_id", flat=True
            )
        )
        data = []
        for e in qs[:300]:
            p = _emp_payload(e, me)
            if e.id in pending_out:
                p["reason"] = "request_pending"
            data.append(p)
        return Response({"results": data})


class ConversationsAPIView(BuzzAPIView):
    """GET: my conversations with unread counts. POST: open (or reuse) a 1:1."""

    def get(self, request):
        me = _me(request)
        if me is None:
            return Response({"error": "Not an employee."}, status=400)
        parts = (
            BuzzParticipant.objects.filter(employee=me)
            .select_related("conversation")
            .order_by("-conversation__updated_at")
        )
        data = []
        for p in parts:
            conv = p.conversation
            last = conv.messages.order_by("-created_at").first()
            data.append(
                {
                    "id": conv.id,
                    "title": conv.display_title(for_employee=me),
                    "is_group": conv.is_group,
                    "last_message": last.body[:80] if last else "",
                    "last_at": last.created_at.isoformat() if last else None,
                    "unread": p.unread_count(),
                }
            )
        return Response({"results": data})

    def post(self, request):
        me = _me(request)
        if me is None:
            return Response({"error": "Not an employee."}, status=400)
        target = Employee.objects.filter(
            id=request.data.get("employee_id"), is_active=True
        ).first()
        if target is None:
            return Response({"error": "Employee not found."}, status=404)
        allowed, reason = can_message(me, target)
        if not allowed:
            return Response({"error": "Not allowed.", "reason": reason}, status=403)

        existing = (
            BuzzConversation.objects.filter(
                is_group=False, participants__employee=me
            )
            .filter(participants__employee=target)
            .first()
        )
        if existing:
            return Response({"id": existing.id, "created": False})
        conv = BuzzConversation.objects.create(
            company_id=me.get_company(), is_group=False, created_by=me
        )
        BuzzParticipant.objects.create(conversation=conv, employee=me)
        BuzzParticipant.objects.create(conversation=conv, employee=target)
        return Response({"id": conv.id, "created": True}, status=201)


class MessagesAPIView(BuzzAPIView):
    """GET ?after=<id>: messages in a conversation (marks read).
    POST: send a message."""

    def _participant(self, request, conversation_id):
        me = _me(request)
        if me is None:
            return None, None
        part = BuzzParticipant.objects.filter(
            conversation_id=conversation_id, employee=me
        ).select_related("conversation").first()
        return me, part

    def get(self, request, conversation_id):
        me, part = self._participant(request, conversation_id)
        if part is None:
            return Response({"error": "Not your conversation."}, status=404)
        qs = part.conversation.messages.select_related("sender")
        after = request.GET.get("after")
        if after and str(after).isdigit():
            qs = qs.filter(id__gt=int(after))
        else:
            qs = qs.order_by("-created_at")[:50][::-1]
        data = [
            {
                "id": m.id,
                "sender_id": m.sender_id,
                "sender": m.sender.get_full_name() if m.sender else "—",
                "mine": m.sender_id == me.id,
                "body": m.body,
                "at": m.created_at.isoformat(),
            }
            for m in qs
        ]
        part.last_read_at = timezone.now()
        part.save(update_fields=["last_read_at"])
        return Response({"results": data, "title": part.conversation.display_title(for_employee=me)})

    def post(self, request, conversation_id):
        me, part = self._participant(request, conversation_id)
        if part is None:
            return Response({"error": "Not your conversation."}, status=404)
        body = str(request.data.get("body", "")).strip()[:4000]
        if not body:
            return Response({"error": "Empty message."}, status=400)
        msg = BuzzMessage.objects.create(
            conversation=part.conversation, sender=me, body=body
        )
        part.conversation.save(update_fields=["updated_at"])  # bump ordering
        part.last_read_at = timezone.now()
        part.save(update_fields=["last_read_at"])
        for other in part.conversation.participants.exclude(employee=me).select_related("employee"):
            _notify(
                other.employee,
                request.user,
                "Buzz",
                f"{me.get_full_name()}: {body[:80]}",
            )
        return Response({"id": msg.id, "at": msg.created_at.isoformat()}, status=201)


class ConnectionsAPIView(BuzzAPIView):
    """GET: pending requests for me. POST: create a request, or respond to one
    ({'connection_id': X, 'action': 'accept'|'decline'})."""

    def get(self, request):
        me = _me(request)
        if me is None:
            return Response({"error": "Not an employee."}, status=400)
        incoming = BuzzConnection.objects.filter(
            target=me, status="pending"
        ).select_related("requester")
        return Response(
            {
                "results": [
                    {
                        "id": c.id,
                        "from_id": c.requester_id,
                        "from": c.requester.get_full_name(),
                        "message": c.message,
                        "at": c.created_at.isoformat(),
                    }
                    for c in incoming
                ]
            }
        )

    def post(self, request):
        me = _me(request)
        if me is None:
            return Response({"error": "Not an employee."}, status=400)

        connection_id = request.data.get("connection_id")
        if connection_id:
            conn = BuzzConnection.objects.filter(
                id=connection_id, target=me, status="pending"
            ).first()
            if conn is None:
                return Response({"error": "Request not found."}, status=404)
            action = request.data.get("action")
            if action not in ("accept", "decline"):
                return Response({"error": "Invalid action."}, status=400)
            conn.status = "accepted" if action == "accept" else "declined"
            conn.responded_at = timezone.now()
            conn.save()
            if conn.status == "accepted":
                _notify(
                    conn.requester,
                    request.user,
                    "Buzz",
                    f"{me.get_full_name()} accepted your connection request.",
                )
            return Response({"status": conn.status})

        target = Employee.objects.filter(
            id=request.data.get("employee_id"), is_active=True
        ).first()
        if target is None:
            return Response({"error": "Employee not found."}, status=404)
        if target.get_company() != me.get_company():
            return Response({"error": "Not allowed."}, status=403)
        allowed, _reason = can_message(me, target)
        if allowed:
            return Response({"error": "You can already message this person."}, status=400)
        conn, created = BuzzConnection.objects.get_or_create(
            requester=me,
            target=target,
            defaults={"message": str(request.data.get("message", ""))[:200]},
        )
        if not created and conn.status == "declined":
            conn.status = "pending"
            conn.responded_at = None
            conn.save()
            created = True
        if created:
            _notify(
                target,
                request.user,
                "Buzz",
                f"{me.get_full_name()} wants to connect on Buzz.",
            )
        return Response({"id": conn.id, "status": conn.status}, status=201 if created else 200)


@login_required
def buzz_page(request):
    """Web UI: directory + chat in one page."""
    return render(request, "buzz/buzz.html")
