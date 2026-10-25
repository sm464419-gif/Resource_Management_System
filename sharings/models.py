from django.db import models
from django.conf import settings

# Create your models here.
class SharedPool(models.Model):
    resource = models.ForeignKey(
        "resources.Resource",on_delete=models.CASCADE)
    released_by = models.CharField(max_length=100)
    available_from = models.DateTimeField()
    available_until = models.DateTimeField()
    status = models.CharField(max_length=50, default="Available")

    def __str__(self):
        return str(self.resource)

class SharingRequest(models.Model):
    shared_pool = models.ForeignKey(
        "SharedPool",on_delete=models.CASCADE)
    requesting_department = models.CharField(max_length=100)
    requested_by = models.IntegerField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=50, default="Pending")
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,on_delete=models.CASCADE,
        null=True,blank=True,related_name="approved_sharing_requests")
    decided_at = models.DateTimeField()

    def __str__(self):
        return str(self.shared_pool)


