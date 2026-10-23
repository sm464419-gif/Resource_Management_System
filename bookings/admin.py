from django.contrib import admin
from .models import Booking,ConflictLog,WaitList

admin.site.register(Booking)
admin.site.register(ConflictLog)
admin.site.register(WaitList)