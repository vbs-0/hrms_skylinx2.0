from datetime import date
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from base.models import Announcement


class MobileAnnouncementsAPIView(APIView):
    """Return active announcements visible to the authenticated employee."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
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
