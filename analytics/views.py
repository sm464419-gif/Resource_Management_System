
# Create your views here.
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.utils import timezone
from datetime import datetime, timedelta, time
from collections import Counter
import csv
from .models import DemandForecast, UtilizationReport
from resources.models import Resource
from bookings.models import Booking

def analytics_dashboard(request):
    resources = Resource.objects.all()
    bookings = Booking.objects.all()
    total_resources = resources.count()
    total_bookings = bookings.count()
    total_reports = UtilizationReport.objects.count()
    total_forecasts = DemandForecast.objects.count()
    reports = UtilizationReport.objects.all().order_by('-id')[:10]
    context = {
        'total_resources': total_resources,
        'total_bookings': total_bookings,
        'total_reports': total_reports,
        'total_forecasts': total_forecasts,
        'reports': reports,
    }
    return render(request, 'analytics/analytics_dashboard.html', context)


def get_period(request):
    today = timezone.localdate()
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    else:
        start_date = today - timedelta(days=30)

    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    else:
        end_date = today

    period_start = timezone.make_aware(datetime.combine(start_date, time.min))
    period_end = timezone.make_aware(datetime.combine(end_date, time.max))
    return period_start, period_end


def get_utilization_data(resource, period_start, period_end):
    bookings = Booking.objects.filter(
        resource=resource,
        start_time__lte=period_end,
        end_time__gte=period_start
    )

    total_bookings = bookings.exclude(status__in=['Cancelled', 'Rejected']).count()
    no_show_bookings = bookings.filter(status__iexact='No-show').count()
    booked_hours = 0
    peak_hours = Counter()

    for booking in bookings.exclude(status__in=['Cancelled', 'Rejected', 'No-show']):
        actual_start = max(booking.start_time, period_start)
        actual_end = min(booking.end_time, period_end)
        duration = (actual_end - actual_start).total_seconds() / 3600

        if duration > 0:
            booked_hours += duration

        peak_hours[booking.start_time.hour] += 1

    daily_open_hours = (
        datetime.combine(period_start.date(), resource.close_time)
        - datetime.combine(period_start.date(), resource.open_time)
    ).total_seconds() / 3600

    number_of_days = (period_end.date() - period_start.date()).days + 1
    available_hours = daily_open_hours * number_of_days

    if available_hours > 0:
        utilization_percent = (booked_hours / available_hours) * 100
    else:
        utilization_percent = 0

    peak_hour = (
        peak_hours.most_common(1)[0][0]
        if peak_hours else 0
    )

    return {
        'total_bookings': total_bookings,
        'total_no_status': no_show_bookings,
        'utilization_percent': round(utilization_percent, 2),
        'peak_hour': peak_hour,
    }


def generate_report(request):
    period_start, period_end = get_period(request)
    resources = Resource.objects.all()
    for resource in resources:
        data = get_utilization_data(resource, period_start, period_end)
        UtilizationReport.objects.create(
            resource=resource,
            department=resource.department,
            period_start=period_start,
            period_end=period_end,
            total_bookings=data['total_bookings'],
            total_no_status=data['total_no_status'],
            utilization_percent=data['utilization_percent'],
            peak_hour=data['peak_hour'],
        )

    return render(
        request,
        'analytics/utilization_report.html',
        {
            'reports': UtilizationReport.objects.filter(
                period_start=period_start,
                period_end=period_end
            )
        }
    )


def calculate_utilization(request):
    period_start, period_end = get_period(request)
    resource_id = request.GET.get('resource_id')

    if resource_id:
        resources = Resource.objects.filter(id=resource_id)
    else:
        resources = Resource.objects.all()

    results = []

    for resource in resources:
        data = get_utilization_data(
            resource, period_start, period_end
        )
        results.append({
            'resource': resource,
            **data,
        })

    context = {
        'results': results,
        'period_start': period_start,
        'period_end': period_end,
    }

    return render(
        request,
        'analytics/utilization_report.html',
        context
    )


def utilization_report_view(request):
    reports = UtilizationReport.objects.all().order_by('-id')
    return render(
        request,
        'analytics/utilization_report.html',
        {'reports': reports}
    )


def predict_demand(request):
    resources = Resource.objects.all()
    today = timezone.now()
    previous_period = today - timedelta(days=30)
    for resource in resources:
        previous_bookings = Booking.objects.filter(
            resource=resource,
            start_time__gte=previous_period,
            start_time__lte=today
        ).exclude(
            status__in=['Cancelled', 'Rejected']
        ).count()

        DemandForecast.objects.create(
            resource=resource,
            forecast_period='Next 30 Days',
            predicted_demand=previous_bookings,
            confidence_score=70.0,
            generated_at=today,
        )

    return render(
        request,
        'analytics/demand_forecast.html',
        {
            'forecasts': DemandForecast.objects.all().order_by('-id')
        }
    )


def demand_forecast_view(request):
    forecasts = DemandForecast.objects.all().order_by('-generated_at')
    return render(
        request,
        'analytics/demand_forecast.html',
        {'forecasts': forecasts}
    )


def report_export(request):
    reports = UtilizationReport.objects.all()
    response = HttpResponse(
        content_type='text/csv'
    )

    response['Content-Disposition'] = (
        'attachment; filename="utilization_report.csv"'
    )

    writer = csv.writer(response)
    writer.writerow([
        'Resource',
        'Department',
        'Period Start',
        'Period End',
        'Total Bookings',
        'No Show',
        'Utilization Percent',
        'Peak Hour',
    ])

    for report in reports:
        writer.writerow([
            report.resource.name,
            report.department,
            report.period_start,
            report.period_end,
            report.total_bookings,
            report.total_no_status,
            report.utilization_percent,
            report.peak_hour,
        ])

    return response