#views.py


from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from .models import CheckIn, NoShowPolicy


# Only admin/staff can manage policies and no-shows
def is_admin(user):
    return user.is_staff or user.is_superuser


# 1. Check in using booking ID
@login_required
def scan_checkin(request):
    if request.method == "POST":
        booking_id = request.POST.get("booking_id")

        checkin = get_object_or_404(
            CheckIn,
            booking_id=booking_id,
            booking__user=request.user,
        )

        if checkin.checked_in_at:
            messages.info(request, "Already checked in.")
        elif checkin.is_no_show:
            messages.error(request, "This booking is marked as a no-show.")
        elif timezone.now() < checkin.start_time:
            messages.error(request, "Your booking has not started yet.")
        else:
            policy = NoShowPolicy.objects.filter(
                resource_category=checkin.booking.resource.category
            ).first()

            grace = policy.grace_period if policy else 10

            if timezone.now() > checkin.start_time + timedelta(minutes=grace):
                messages.error(request, "Check-in time has expired.")
            elif timezone.now() >= checkin.end_time:
                messages.error(request, "Your booking has ended.")
            else:
                checkin.checked_in_at = timezone.now()
                checkin.method = request.POST.get("method", "manual")
                checkin.status = "checked_in"
                checkin.save()

                messages.success(request, "Check-in successful!")

        return redirect("checkins:checkin")

    return render(request, "checkins/checkin.html")


# 2. Check-in and no-show history
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


# 3. Mark missed bookings as no-show
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

            grace = policy.grace_period if policy else 10

            if now >= record.start_time + timedelta(minutes=grace):
                record.is_no_show = True
                record.status = "no_show"
                record.save()
                count += 1

        messages.success(request, f"{count} booking(s) marked as no-show.")

    return redirect("checkins:checkin_history")


# 4. Release an expired resource booking
@login_required
def release_resource(request, checkin_id):
    record = get_object_or_404(
        CheckIn,
        pk=checkin_id,
        booking__user=request.user,
    )

    if request.method == "POST":
        if timezone.now() < record.end_time:
            messages.error(request, "The booking has not ended yet.")
        else:
            record.was_used = True
            record.status = "completed"
            record.save()
            messages.success(request, "Resource released successfully.")

    return redirect("checkins:checkin_history")


# 5. Apply no-show and automatic-release policies
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

            grace = policy.grace_period if policy else 10

            if now >= record.start_time + timedelta(minutes=grace):
                record.is_no_show = True
                record.status = "no_show"
                record.save()
                marked += 1

        if NoShowPolicy.objects.filter(auto_release=True).exists():
            expired = CheckIn.objects.filter(
                end_time__lte=now,
                was_used=False,
            )

            for record in expired:
                record.was_used = True
                record.status = "completed"
                record.save()
                released += 1

        messages.success(
            request,
            f"Policy applied. No-shows: {marked}, released: {released}.",
        )

    return redirect("checkins:no_show_policy")


# 6. Admin no-show policy page
@login_required
@user_passes_test(is_admin)
def no_show_policy_view(request):
    policies = NoShowPolicy.objects.all()

    if request.method == "POST":
        policy_id = request.POST.get("policy_id")
        policy = get_object_or_404(NoShowPolicy, pk=policy_id)

        try:
            grace = int(request.POST.get("grace_period", 10))
            penalty = float(request.POST.get("penalty_score", 0))
        except (ValueError, TypeError):
            messages.error(request, "Enter valid numbers.")
            return redirect("checkins:no_show_policy")

        if grace < 0 or penalty < 0:
            messages.error(request, "Values cannot be negative.")
        else:
            policy.grace_period = grace
            policy.penalty_score = penalty
            policy.auto_release = (
                request.POST.get("auto_release") == "on"
            )
            policy.save()
            messages.success(request, "Policy updated successfully.")

        return redirect("checkins:no_show_policy")

    return render(
        request,
        "checkins/no_show_policy.html",
        {"policies": policies},
    )