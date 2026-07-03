"""FCM push notifications: fires whenever a Notification row is created,
so every existing notify.send() call site (leave, announcements, requests,
etc.) gets push delivery for free without touching each call site."""
import os

from django.db.models.signals import post_save
from django.dispatch import receiver

_firebase_app = None


def _get_firebase_app():
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app
    cred_path = os.environ.get("FIREBASE_CREDENTIALS_PATH")
    if not cred_path or not os.path.exists(cred_path):
        return None
    import firebase_admin
    from firebase_admin import credentials

    _firebase_app = firebase_admin.initialize_app(credentials.Certificate(cred_path))
    return _firebase_app


def send_push(user, title, body, data=None):
    app = _get_firebase_app()
    if app is None:
        return
    tokens = list(user.device_tokens.values_list("token", flat=True))
    if not tokens:
        return
    from firebase_admin import messaging

    message = messaging.MulticastMessage(
        notification=messaging.Notification(title=title, body=body),
        data={k: str(v) for k, v in (data or {}).items()},
        tokens=tokens,
    )
    try:
        response = messaging.send_each_for_multicast(message, app=app)
    except Exception as e:
        print(f"FCM push failed: {e}")
        return
    # Drop tokens Firebase says are no longer valid (uninstalled/expired).
    if response.failure_count:
        from .models import DeviceToken

        for idx, result in enumerate(response.responses):
            if not result.success:
                DeviceToken.objects.filter(token=tokens[idx]).delete()


def _connect():
    from .models import Notification

    @receiver(post_save, sender=Notification)
    def _push_on_notification_created(sender, instance, created, **kwargs):
        if not created or not instance.recipient_id:
            return
        title = "Emplinx"
        body = instance.description or instance.verb or "You have a new notification"
        send_push(instance.recipient, title, body, data={"notification_id": instance.id})
