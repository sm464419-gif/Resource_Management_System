from django.db import models

# Create your models here.
class DemandForecast(models.Model):
    resource = models.ForeignKey(
        "resources.Resource",on_delete=models.CASCADE)
    forecast_period = models.CharField(max_length=100)
    predicted_demand = models.IntegerField()
    confidence_score = models.FloatField()
    generated_at = models.DateTimeField()

    def __str__(self):
        return str(self.resource)


class UtilizationReport(models.Model):
    resource = models.ForeignKey(
        "resources.Resource",on_delete=models.CASCADE)
    department = models.CharField(max_length=100)
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    total_bookings = models.IntegerField()
    total_no_status = models.IntegerField()
    utilization_percent = models.FloatField()
    peak_hour = models.IntegerField()

    def __str__(self):
        return str(self.resource)


