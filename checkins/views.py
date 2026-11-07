import base64
from datetime import timedelta
from io import BytesIO
from urllib.parse import urlparse, parse_qs

import qrcode
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone

from bookings.models import Booking
from resources.models import Resource

from .models import CheckIn, NoShowPolicy

CHECKIN_URL = "checkins:checkins"   # app_name:route-name
EARLY_MINUTES = 15                  # check-in opens this long before the start
DEFAULT_GRACE = 10                  # minutes, used when no NoShowPolicy exists

# True  = only a valid QR scan checks people in
# False = the QR scan works AND the plain button works (for testing)
REQUIRE_QR = True

# Only the secret token identifies a resource (no ID guessing).
QR_LOOKUP_FIELDS = ["qr_code"]


def is_admin(user):
    return user.is_staff or user.is_superuser


# ---------- QR helpers ----------

def extract_code(raw):
    """Turn scanned text (plain token or URL) into the token itself."""
    raw = (raw or "").strip()
    if not raw:
        return ""
    if raw.lower().startswith(("http://", "https://")):
        parsed = urlparse(raw)
        query = parse_qs(parsed.query)
        for key in ("qr", "code", "token"):
            if query.get(key):
                return query[key][0].strip()
        parts = [p for p in parsed.path.split("/") if p]
        return parts[-1] if parts else ""
    return raw


def find_resource(raw):
    """Return the Resource that the scanned QR text belongs to, or None."""
    code = extract_code(raw)
    if not code:
        return None

    field_names = {f.name for f in Resource._meta.get_fields()}
    for field in QR_LOOKUP_FIELDS:
        if field in field_names:
            resource = Resource.objects.filter(**{f"{field}__iexact": code}).first()
            if resource:
                return resource
    return None


def make_qr_for(request, resource):
    """Return (qr_url, base64_png) for a resource's check-in QR."""
    qr_url = request.build_absolute_uri(
        reverse("checkins:qr_checkin", args=[resource.qr_code])
    )
    buffer = BytesIO()
    qrcode.make(qr_url).save(buffer, format="PNG")
    return qr_url, base64.b64encode(buffer.getvalue()).decode("utf-8")


# ---------- booking / window helpers ----------

def get_booking(request, raw_id):
    """Return the logged-in user's booking, or None."""
    if not str(raw_id or "").isdigit():
        return None
    return (
        Booking.objects.select_related("resource")
        .filter(pk=raw_id, user=request.user)
        .first()
    )


def get_grace(booking):
    policy = NoShowPolicy.objects.filter(
        resource_category=booking.resource.category
    ).first()
    return policy.grace_period if policy else DEFAULT_GRACE


def get_window(start, end, grace, now=None):
    """Return (state, opens_at). State: early / open / grace / closed."""
    now = now or timezone.now()
    opens = start - timedelta(minutes=EARLY_MINUTES)
    if now < opens:
        return "early", opens
    if now <= start:
        return "open", opens
    if now <= start + timedelta(minutes=grace) and now < end:
        return "grace", opens
    return "closed", opens


def do_checkin(booking, method):
    """Check the booking in. Returns (message_level, text)."""
    checkin = CheckIn.objects.filter(booking=booking).first()
    if checkin is None:
        checkin = CheckIn.objects.create(
            booking=booking,
            start_time=booking.start_time,
            end_time=booking.end_time,
            method=method,
            status="pending",
        )

    now = timezone.now()
    state, opens = get_window(
        checkin.start_time, checkin.end_time, get_grace(booking), now
    )

    if checkin.checked_in_at:
        return "info", "Already checked in."
    if checkin.is_no_show:
        return "error", "This booking is marked as a no-show."
    if state == "early":
        return "error", f"Check-in opens at {timezone.localtime(opens):%d %b, %H:%M}."
    if state == "closed":
        return "error", "The check-in window has closed."

    checkin.checked_in_at = now
    checkin.method = method
    checkin.status = "late" if state == "grace" else "checked_in"
    checkin.save()
    return "success", "Check-in successful!"


# 1. Check-in page (GET shows the page, POST checks in)
@login_required
def scan_checkin(request):
    if request.method == "POST":
        booking = get_booking(request, request.POST.get("booking_id"))
        if booking is None:
            messages.error(request, "Booking not found.")
            return redirect(CHECKIN_URL)

        back = f"{reverse(CHECKIN_URL)}?booking={booking.pk}"

        if booking.status.lower() != "approved":
            messages.error(
                request, f"Booking status is '{booking.status}', not approved."
            )
            return redirect(back)

        scanned = request.POST.get("code", "").strip()

        if scanned:
            # The QR must belong to THIS booking's resource
            resource = find_resource(scanned)
            if resource is None or resource.pk != booking.resource_id:
                messages.error(
                    request, "That QR code does not match this booking's resource."
                )
                return redirect(back)
            method = "qr"
        elif REQUIRE_QR:
            messages.error(request, "Scan the QR code at the location to check in.")
            return redirect(back)
        else:
            if not request.POST.get("confirm"):
                messages.error(request, "Please confirm that you are at the location.")
                return redirect(back)
            method = "manual"

        level, text = do_checkin(booking, method)
        getattr(messages, level)(request, text)
        return redirect(back)

    # ---- GET ----
    booking = get_booking(request, request.GET.get("booking"))
    checkin = None
    window_state = None
    window_opens = None
    grace = DEFAULT_GRACE
    qr_url = None
    qr_image = None

    if booking:
        checkin = CheckIn.objects.filter(booking=booking).first()
        start = checkin.start_time if checkin else booking.start_time
        end = checkin.end_time if checkin else booking.end_time
        grace = get_grace(booking)
        window_state, window_opens = get_window(start, end, grace)

        if booking.status.lower() != "approved":
            window_state = "unavailable"
        elif checkin and checkin.is_no_show:
            window_state = "closed"

        # Test helper: show the QR to admins, or to everyone while DEBUG = True
        if is_admin(request.user) or settings.DEBUG:
            qr_url, qr_image = make_qr_for(request, booking.resource)

    return render(
        request,
        "checkins/checkin.html",
        {
            "booking": booking,
            "checkin": checkin,
            "window_state": window_state,
            "window_opens": window_opens,
            "grace": grace,
            "require_qr": REQUIRE_QR,
            "qr_url": qr_url,
            "qr_image": qr_image,
        },
    )


# 2. Landing page when a phone camera scans the resource QR
@login_required
def qr_checkin(request, code):
    resource = find_resource(code)
    if resource is None:
        messages.error(request, "Invalid QR code.")
        return redirect("bookings:booking_list")

    now = timezone.now()
    booking = (
        Booking.objects.filter(
            user=request.user,
            resource=resource,
            status__iexact="approved",
            start_time__lte=now + timedelta(minutes=EARLY_MINUTES),
            end_time__gt=now,
        )
        .order_by("start_time")
        .first()
    )
    if booking is None:
        messages.error(
            request,
            f"You have no active approved booking for {resource.name} right now.",
        )
        return redirect("bookings:booking_list")

    level, text = do_checkin(booking, "qr")
    getattr(messages, level)(request, text)
    return redirect(f"{reverse(CHECKIN_URL)}?booking={booking.pk}")


# 3. Check-in and no-show history
@login_required
def checkin_history(request):
    if is_admin(request.user):
        records = CheckIn.objects.all()
    else:
        records = CheckIn.objects.filter(booking__user=request.user)

    return render(
        request,
        "checkins/checkin_history.html",
        {"records": records.order_by("-start_time")},
    )


# 4. Mark missed bookings as no-show
@login_required
@user_passes_test(is_admin)
def mark_no_show(request):
    if request.method == "POST":
        now = timezone.now()
        count = 0

        records = CheckIn.objects.filter(
            checked_in_at__isnull=True,
            is_no_show=False,
            start_time__lte=now,
            end_time__gt=now,
        )

        for record in records:
            policy = NoShowPolicy.objects.filter(
                resource_category=record.booking.resource.category
            ).first()
            grace = policy.grace_period if policy else DEFAULT_GRACE

            if now >= record.start_time + timedelta(minutes=grace):
                record.is_no_show = True
                record.status = "no_show"
                record.save()
                count += 1

        messages.success(request, f"{count} booking(s) marked as no-show.")

    return redirect("checkins:checkin_history")


# 5. Release an expired resource booking
@login_required
def release_resource(request, checkin_id):
    record = get_object_or_404(CheckIn, pk=checkin_id, booking__user=request.user)

    if request.method == "POST":
        if timezone.now() < record.end_time:
            messages.error(request, "The booking has not ended yet.")
        else:
            record.was_used = True
            record.status = "completed"
            record.save()
            messages.success(request, "Resource released successfully.")

    return redirect("checkins:checkin_history")


# 6. Apply no-show and automatic-release policies
@login_required
@user_passes_test(is_admin)
def apply_policy(request):
    if request.method == "POST":
        now = timezone.now()
        marked = 0
        released = 0

        records = CheckIn.objects.filter(
            checked_in_at__isnull=True,
            is_no_show=False,
            start_time__lte=now,
            end_time__gt=now,
        )

        for record in records:
            policy = NoShowPolicy.objects.filter(
                resource_category=record.booking.resource.category
            ).first()
            grace = policy.grace_period if policy else DEFAULT_GRACE

            if now >= record.start_time + timedelta(minutes=grace):
                record.is_no_show = True
                record.status = "no_show"
                record.save()
                marked += 1

        if NoShowPolicy.objects.filter(auto_release=True).exists():
            expired = CheckIn.objects.filter(end_time__lte=now, was_used=False)
            for record in expired:
                record.was_used = True
                record.status = "completed"
                record.save()
                released += 1

        messages.success(
            request, f"Policy applied. No-shows: {marked}, released: {released}."
        )

    return redirect("checkins:no_show_policy")


# 7. Admin no-show policy page
@login_required
@user_passes_test(is_admin)
def no_show_policy_view(request):
    policies = NoShowPolicy.objects.all()

    if request.method == "POST":
        policy_id = request.POST.get("policy_id")
        policy = get_object_or_404(NoShowPolicy, pk=policy_id)

        try:
            grace = int(request.POST.get("grace_period", DEFAULT_GRACE))
            penalty = float(request.POST.get("penalty_score", 0))
        except (ValueError, TypeError):
            messages.error(request, "Enter valid numbers.")
            return redirect("checkins:no_show_policy")

        if grace < 0 or penalty < 0:
            messages.error(request, "Values cannot be negative.")
        else:
            policy.grace_period = grace
            policy.penalty_score = penalty
            policy.auto_release = request.POST.get("auto_release") == "on"
            policy.save()
            messages.success(request, "Policy updated successfully.")

        return redirect("checkins:no_show_policy")

    return render(request, "checkins/no_show_policy.html", {"policies": policies})