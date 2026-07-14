from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from geopy.geocoders import Nominatim


class GeoFencing(models.Model):
    latitude = models.FloatField()
    longitude = models.FloatField()
    radius_in_meters = models.IntegerField()
    company_id = models.OneToOneField(
        "base.Company",
        related_name="geo_fencing",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    start = models.BooleanField(default=False)
    # ponytail: when False (default) an out-of-zone check-in is recorded + flagged +
    # admins notified (no lockout). When True the mobile API rejects it outright.
    enforce = models.BooleanField(
        default=False,
        help_text="Block mobile check-in/out when outside the geofence (instead of just flagging it).",
    )
    exempted_employees = models.ManyToManyField(
        "employee.Employee",
        blank=True,
        related_name="geofence_exemptions",
        verbose_name="Exempted Employees",
        help_text="These employees skip geofence checks entirely, regardless of location.",
    )

    def clean(self):
        if self.company_id is None:
            qs = GeoFencing.objects.filter(company_id__isnull=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError("Only one GeoFencing can have a null company_id.")

        geolocator = Nominatim(
            user_agent="geo_checker_unique"
        )  # Unique user-agent is important
        try:
            location = geolocator.reverse(
                (self.latitude, self.longitude), exactly_one=True
            )
            if not location:
                raise ValidationError("Invalid location coordinates.")
        except Exception as e:
            raise ValidationError(f"Geolocation error: {e}")

        return super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()  # Run clean before save
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["company_id"],
                name="unique_company_id_when_not_null_geofencing",
                condition=~Q(company_id=None),
            )
        ]
