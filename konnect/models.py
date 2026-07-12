"""KONNECT — company social feed (Kredily-Konnect style).

Company-wide posts: announcements, birthday/anniversary auto-posts, general
shout-outs. Unlike Buzz (private 1:1 chat, now retired from the UI), every
post is visible to the whole company and only to that company.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from base.models import Company
from employee.models import Employee

CATEGORY_CHOICES = [
    ("general", _("General")),
    ("announcement", _("Announcements")),
    ("birthday", _("Birthday")),
    ("anniversary", _("Work Anniversary")),
    ("new_joiner", _("New Joiner")),
]


class KonnectPost(models.Model):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="konnect_posts"
    )
    # author=None → system post (birthday cron etc.), shown as the company
    author = models.ForeignKey(
        Employee, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="konnect_posts",
    )
    body = models.TextField(max_length=4000)
    image = models.ImageField(upload_to="konnect/", null=True, blank=True)
    category = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES, default="general"
    )
    pinned = models.BooleanField(default=False)
    mentions = models.ManyToManyField(
        Employee, blank=True, related_name="konnect_mentions"
    )
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-pinned", "-created_at"]

    def __str__(self):
        return f"[{self.category}] {self.body[:40]}"


class KonnectMedia(models.Model):
    post = models.ForeignKey(KonnectPost, on_delete=models.CASCADE, related_name="media")
    file = models.FileField(upload_to="konnect/media/")
    kind = models.CharField(max_length=5, choices=(("image", "Image"), ("video", "Video")))
    created_at = models.DateTimeField(auto_now_add=True)


class KonnectLike(models.Model):
    post = models.ForeignKey(
        KonnectPost, on_delete=models.CASCADE, related_name="likes"
    )
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("post", "employee")


class KonnectComment(models.Model):
    post = models.ForeignKey(
        KonnectPost, on_delete=models.CASCADE, related_name="comments"
    )
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="+")
    body = models.TextField(max_length=2000)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
