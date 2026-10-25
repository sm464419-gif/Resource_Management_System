from django.contrib import admin

from .models import SharedPool, SharingRequest

# Register your models here.
admin.site.register(SharedPool)
admin.site.register(SharingRequest)
