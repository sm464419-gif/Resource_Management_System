from django.contrib import admin

from .models import DemandForecast, UtilizationReport

# Register your models here.
admin.site.register(DemandForecast)
admin.site.register(UtilizationReport)
