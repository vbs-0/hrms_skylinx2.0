from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from notifications.models import DeviceToken

from ...api_serializers.notifications.serializers import NotificationSerializer

# Create your views here.


class DeviceTokenView(APIView):
    """Register/unregister this device's FCM token for push notifications."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.data.get("token")
        if not token:
            return Response({"error": "token is required"}, status=400)
        platform = request.data.get("platform", "android")
        DeviceToken.objects.filter(token=token).exclude(user=request.user).delete()
        DeviceToken.objects.update_or_create(
            token=token, defaults={"user": request.user, "platform": platform}
        )
        return Response({"status": "registered"}, status=200)

    def delete(self, request):
        token = request.data.get("token")
        DeviceToken.objects.filter(user=request.user, token=token).delete()
        return Response({"status": "unregistered"}, status=200)


class NotificationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, type):
        if type == "all":
            queryset = request.user.notifications.all()
        elif type == "unread":
            queryset = request.user.notifications.unread()

        pagination = PageNumberPagination()
        page = pagination.paginate_queryset(queryset, request)
        serializer = NotificationSerializer(page, many=True)
        return pagination.get_paginated_response(serializer.data)


class NotificationReadDelView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        obj = request.user.notifications.filter(id=id).first()
        obj.mark_as_read()
        serializer = NotificationSerializer(obj)
        return Response(serializer.data, status=200)

    def delete(self, request, id):
        obj = request.user.notifications.filter(id=id).first()
        obj.deleted = True
        obj.save()
        return Response({"status": "deleted"}, status=200)


class NotificationBulkReadDelView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        obj = request.user.notifications.all()
        obj.mark_all_as_read()
        return Response({"status": "marked as read"}, status=200)

    def delete(self, request):
        obj = request.user.notifications.all()
        obj.mark_all_as_deleted()
        return Response({"status": "deleted"}, status=200)


class NotificationBulkDelUnreadMessageView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        obj = request.user.notifications.unread()
        obj.mark_all_as_deleted()
        return Response({"status": "deleted"}, status=200)
