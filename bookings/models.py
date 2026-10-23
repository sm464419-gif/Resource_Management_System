from django.db import models
from django.conf import settings


class Booking(models.Model):
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    resource = models.ForeignKey('resources.Resource', on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    purpose = models.TextField()
    priority_score = models.FloatField(default=0)
    is_recurring = models.BooleanField(default=False)
    recurrence_rule = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=50, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)



class ConflictLog(models.Model):
    booking = models.ForeignKey(
        "Booking", on_delete=models.CASCADE,
        related_name="conflicts"
    )
    conflicting_booking = models.ForeignKey(
        "Booking", on_delete=models.CASCADE,
        related_name="conflicting_logs"
    )
    detected_at = models.DateTimeField(auto_now_add=True)
    resolution = models.CharField(max_length=100, blank=True)
    suggested_resource = models.ForeignKey(
        "resources.Resource", on_delete=models.SET_NULL,
        null=True, blank=True
    )
    suggested_time = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return str(self.booking)


class WaitList(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE
    )
    resource = models.ForeignKey(
        "resources.Resource", on_delete=models.CASCADE
    )
    requested_start = models.DateTimeField()
    requested_end = models.DateTimeField()
    notified = models.BooleanField(default=False)
    status = models.CharField(max_length=20, default="waiting")

    def __str__(self):
        return str(self.user)
