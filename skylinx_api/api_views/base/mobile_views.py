from datetime import date
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from base.models import Announcement
from base.rbac import is_platform_owner


class MobileAnnouncementsAPIView(APIView):
    """Return active announcements visible to the authenticated employee."""
    permission_classes = [IsAuthenticated]

    @staticmethod
    def _can(request, action):
        return is_platform_owner(request.user) or request.user.has_perm(
            f"base.{action}_announcement"
        )

    @staticmethod
    def _company(request):
        try:
            return request.user.employee_get.get_company()
        except Exception:
            return None

    def get(self, request, pk=None):
        try:
            employee = request.user.employee_get
            company = employee.get_company()
        except Exception:
            employee = None
            company = None

        today = date.today()

        # Base queryset: not expired
        qs = Announcement.objects.filter(
            expire_date__gte=today
        ) | Announcement.objects.filter(expire_date__isnull=True)

        # Filter to announcements visible to this employee's company or all
        if company:
            qs = qs.filter(
                company_id=company
            ) | qs.filter(company_id__isnull=True)

        # Deduplicate and order by newest first
        try:
            qs = qs.distinct().order_by("-created_at")[:20]
        except Exception:
            qs = qs.distinct()[:20]

        announcements = []
        for a in qs:
            announcements.append({
                "id": str(a.id),
                "title": a.title,
                "description": a.description or "",
                "expireDate": a.expire_date.isoformat() if a.expire_date else None,
                "createdAt": a.created_at.isoformat() if hasattr(a, "created_at") and a.created_at else None,
            })

        return Response({
            "success": True,
            "message": "Announcements loaded",
            "data": announcements
        }, status=200)

    def post(self, request, pk=None):
        if not self._can(request, "add"):
            return Response({"success": False, "message": "Not allowed."}, status=403)
        title = str(request.data.get("title") or "").strip()
        description = str(request.data.get("description") or "").strip()
        if not title:
            return Response({"success": False, "message": "Title is required."}, status=400)
        announcement = Announcement.objects.create(
            title=title,
            description=description,
            expire_date=request.data.get("expireDate") or None,
        )
        company = self._company(request)
        if company:
            announcement.company_id.add(company)
        return Response({"success": True, "message": "Announcement created."}, status=201)

    def put(self, request, pk=None):
        if not pk or not self._can(request, "change"):
            return Response({"success": False, "message": "Not allowed."}, status=403)
        announcement = self._editable(request, pk)
        if not announcement:
            return Response({"success": False, "message": "Announcement not found."}, status=404)
        title = str(request.data.get("title") or "").strip()
        if not title:
            return Response({"success": False, "message": "Title is required."}, status=400)
        announcement.title = title
        announcement.description = str(request.data.get("description") or "").strip()
        if "expireDate" in request.data:
            announcement.expire_date = request.data.get("expireDate") or None
        announcement.save()
        return Response({"success": True, "message": "Announcement updated."})

    def delete(self, request, pk=None):
        if not pk or not self._can(request, "delete"):
            return Response({"success": False, "message": "Not allowed."}, status=403)
        announcement = self._editable(request, pk)
        if not announcement:
            return Response({"success": False, "message": "Announcement not found."}, status=404)
        announcement.delete()
        return Response({"success": True, "message": "Announcement deleted."})

    def _editable(self, request, pk):
        qs = Announcement.objects.entire().filter(pk=pk)
        company = self._company(request)
        if company and not is_platform_owner(request.user):
            qs = qs.filter(company_id=company)
        return qs.first()
