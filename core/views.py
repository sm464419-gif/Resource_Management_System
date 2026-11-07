from django.shortcuts import render


def base(request):
    return render(request, 'core/base.html')
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Count
from django.shortcuts import render

from bookings.models import Booking
from resources.models import Resource, ResourceCategory


def home(request):
    User = get_user_model()

    # Categories with a live resource count
    categories = ResourceCategory.objects.annotate(
        resource_count=Count("resource")
    ).order_by("name")

    # Most booked resources (only ones that have bookings)
    popular_resources = (
        Resource.objects.select_related("category")
        .annotate(booking_count=Count("bookings"))
        .filter(booking_count__gt=0)
        .order_by("-booking_count")[:6]
    )

    # Utilization = share of resources that have at least one active booking
    total_resources = Resource.objects.count()
    active = Booking.objects.exclude(status__in=["Cancelled", "Rejected"])
    used_resources = active.values("resource").distinct().count()
    utilization = round(used_resources / total_resources * 100) if total_resources else 0

    stats = {
        "categories": ResourceCategory.objects.count(),
        "users": User.objects.filter(is_active=True).count(),
        "bookings": Booking.objects.count(),
        "utilization": utilization,
    }

    return render(request, "core/home.html", {
        "categories": categories,
        "popular_resources": popular_resources,
        "stats": stats,
        "login_url": settings.LOGIN_URL,
    })