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

# Add these imports at the top of core/views.py (skip any you already have)
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count
from django.shortcuts import render
from django.utils import timezone

from bookings.models import Booking
from checkins.models import CheckIn
from resources.models import Resource, ResourceCategory


def is_dashboard_admin(user):
    return user.is_authenticated and (
        user.is_staff
        or user.is_superuser
        or getattr(user, "role", "") == "admin"
    )


@login_required
@user_passes_test(is_dashboard_admin)
def admin_dashboard(request):
    User = get_user_model()
    now = timezone.localtime()
    today = now.date()

    bookings = Booking.objects.all()
    total_bookings = bookings.count()

    # ---------- headline numbers ----------
    total_resources = Resource.objects.count()
    used_resources = (
        bookings.exclude(status__in=["Cancelled", "Rejected"])
        .values("resource").distinct().count()
    )

    stats = {
        "resources": total_resources,
        "active_resources": Resource.objects.filter(status__iexact="active").count(),
        "categories": ResourceCategory.objects.count(),
        "bookings": total_bookings,
        "today_bookings": bookings.filter(start_time__date=today).count(),
        "pending": bookings.filter(status__iexact="pending").count(),
        "cancelled": bookings.filter(status__in=["Cancelled", "Rejected"]).count(),
        "users": User.objects.filter(is_active=True).count(),
        "checkins_today": CheckIn.objects.filter(checked_in_at__date=today).count(),
        "no_shows": CheckIn.objects.filter(is_no_show=True).count(),
        "utilization": round(used_resources / total_resources * 100) if total_resources else 0,
    }

    # ---------- bookings by status (bar widths) ----------
    status_rows = list(
        bookings.values("status").annotate(count=Count("id")).order_by("-count")
    )
    top_status = max((r["count"] for r in status_rows), default=1)
    for row in status_rows:
        row["percent"] = round(row["count"] / top_status * 100)

    # ---------- last 7 days (column chart) ----------
    days = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        days.append({
            "label": day.strftime("%a"),
            "count": bookings.filter(start_time__date=day).count(),
        })
    top_day = max((d["count"] for d in days), default=0) or 1
    for d in days:
        d["percent"] = round(d["count"] / top_day * 100)

    # ---------- most booked resources ----------
    top_resources = list(
        Resource.objects.select_related("category")
        .annotate(total=Count("bookings"))
        .filter(total__gt=0)
        .order_by("-total")[:5]
    )
    top_total = top_resources[0].total if top_resources else 1
    for r in top_resources:
        r.percent = round(r.total / top_total * 100)

    # ---------- categories, recent and today ----------
    category_stats = ResourceCategory.objects.annotate(
        resource_count=Count("resource")
    ).order_by("-resource_count", "name")

    recent_bookings = (
        bookings.select_related("user", "resource").order_by("-created_at")[:8]
    )
    today_bookings = (
        bookings.select_related("user", "resource")
        .filter(start_time__date=today)
        .exclude(status__in=["Cancelled", "Rejected"])
        .order_by("start_time")[:10]
    )

    return render(request, "core/dashboard.html", {
        "today": today,
        "stats": stats,
        "status_breakdown": status_rows,
        "last_7_days": days,
        "top_resources": top_resources,
        "category_stats": category_stats,
        "recent_bookings": recent_bookings,
        "today_bookings": today_bookings,
    })

