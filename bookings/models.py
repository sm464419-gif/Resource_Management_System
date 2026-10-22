from django.db import models


class Booking(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    resource = models.ForeignKey('resources.Resource', on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    purpose = models.TextField()
    priority_score = models.FloatField(default=0)
    is_recurring = models.BooleanField(default=False)
    recurrence_rule = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=50, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)