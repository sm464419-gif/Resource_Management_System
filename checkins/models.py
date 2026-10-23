#models.py

from django.db import models


class CheckIn(models.Model):
    booking = models.ForeignKey("bookings.Booking", on_delete=models.CASCADE)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    method = models.CharField(max_length=50)
    is_no_show = models.BooleanField(default=False)
    was_used = models.BooleanField(default=False)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=50)

    def scan_checkin(self):
        pass

    def mark_no_show(self):
        pass

    def release_resource(self):
        pass


class NoShowPolicy(models.Model):
    resource_category = models.ForeignKey(
        "resources.ResourceCategory", on_delete=models.CASCADE
    )
    grace_period = models.IntegerField()
    auto_release = models.BooleanField(default=False)
    penalty_score = models.FloatField(default=0)

    def apply_policy(self):
        pass