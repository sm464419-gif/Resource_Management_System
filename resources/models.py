
from django.db import models


class ResourceCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()


class Resource(models.Model):
    name = models.CharField(max_length=200)
    category = models.ForeignKey(ResourceCategory, on_delete=models.CASCADE)
    department = models.CharField(max_length=100)
    capacity = models.PositiveIntegerField()
    location = models.CharField(max_length=200)
    qr_code = models.CharField(max_length=255)
    device_code = models.CharField(max_length=100)
    open_time = models.TimeField()
    close_time = models.TimeField()
    status = models.CharField(max_length=50)
    description = models.TextField()
