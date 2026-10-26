from django.contrib import admin

# Register your models here.
from .models import CheckIn,NoShowPolicy
admin.site.register(CheckIn)
admin.site.register(NoShowPolicy)

