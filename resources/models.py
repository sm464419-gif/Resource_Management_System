import uuid
from django.db import models


def generate_device_code():
    return uuid.uuid4().hex[:8].upper()



class ResourceCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()

    def __str__(self):
        return self.name


class Resource(models.Model):
    name = models.CharField(max_length=200)
    category = models.ForeignKey(ResourceCategory, on_delete=models.CASCADE)
    department = models.CharField(max_length=100)
    capacity = models.PositiveIntegerField()
    location = models.CharField(max_length=200)
    qr_code = models.CharField(
        max_length=255,
        unique=True,
        default=uuid.uuid4,
        editable=False
    )
    device_code = models.CharField(
        max_length=100,
        unique=True,
        default=generate_device_code,
        editable=False
    )
    open_time = models.TimeField()
    close_time = models.TimeField()
    status = models.CharField(max_length=50)
    description = models.TextField()

    def __str__(self):
        return self.name
