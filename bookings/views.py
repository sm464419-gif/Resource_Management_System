import calendar
from datetime import date, timedelta
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_POST

from resources.models import Resource
from .models import Booking, ConflictLog, WaitList

DHAKA_TZ = ZoneInfo('Asia/Dhaka')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_staff_or_admin(user):
    return user.is_staff or user.is_superuser or getattr(user, 'role', '') == 'admin'


def staff_required(view):
    return login_required(user_passes_test(is_staff_or_admin)(view))


def parse_local_datetime(value):
    """Turn a datetime-local string into an aware Asia/Dhaka datetime."""
    dt = parse_datetime(value or '')
    if dt and timezone.is_naive(dt):
        dt = timezone.make_aware(dt, DHAKA_TZ)
    return dt


def check_conflict(resource, start_time, end_time, exclude_id=None):
    """Active bookings that overlap the given time range."""
    clashes = Booking.objects.filter(
        resource=resource,
        start_time__lt=end_time,
        end_time__gt=start_time,
    ).exclude(status__in=['Cancelled', 'Rejected'])

    if exclude_id:
        clashes = clashes.exclude(id=exclude_id)
    return clashes


def is_free(resource, start_time, end_time):
    return not check_conflict(resource, start_time, end_time).exists()


def suggest_alternative(resource, start_time, end_time):
    """Next free hourly slot (within 48 hours) and free resources in the same category."""
    duration = end_time - start_time

    later_start = None
    for hours in range(1, 49):
        candidate = start_time + timedelta(hours=hours)
        if is_free(resource, candidate, candidate + duration):
            later_start = candidate
            break

    others = Resource.objects.filter(category=resource.category).exclude(pk=resource.pk)

    return {
        'start': later_start,
        'end': later_start + duration if later_start else None,
        'resources': [r for r in others if is_free(r, start_time, end_time)],
    }


def detect_conflict(booking):
    """Create a ConflictLog for every booking that clashes with `booking`."""
    clashes = check_conflict(
        booking.resource, booking.start_time, booking.end_time,
        exclude_id=booking.id,
    )
    return [
        ConflictLog.objects.get_or_create(booking=booking, conflicting_booking=other)[0]
        for other in clashes
    ]


def update_waitlist(booking):
    """
    After a booking is cancelled/rejected, mark the first waitlist entry whose
    slot is now free as 'notified' (it shows on that user's waitlist page).
    """
    waiting = WaitList.objects.filter(
        resource=booking.resource,
        status='waiting',
        requested_start__lt=booking.end_time,
        requested_end__gt=booking.start_time,
    ).select_related('resource').order_by('id')

    for entry in waiting:
        if not is_free(entry.resource, entry.requested_start, entry.requested_end):
            continue

        entry.status = 'notified'
        entry.notified = True
        entry.save(update_fields=['status', 'notified'])
        return entry  # only the first eligible user

    return None


# ---------------------------------------------------------------------------
# User bookings
# ---------------------------------------------------------------------------

@login_required
def booking_list(request):
    bookings = Booking.objects.filter(user=request.user).select_related('resource')

    status = request.GET.get('status')
    if status in ('Pending', 'Approved', 'Cancelled'):
        bookings = bookings.filter(status=status)

    return render(request, 'bookings/booking_list.html', {
        'bookings': bookings.order_by('-start_time'),
    })


@login_required
def booking_detail(request, id):
    booking = get_object_or_404(Booking, id=id, user=request.user)
    return render(request, 'bookings/booking_detail.html', {'booking': booking})


@login_required
def create_booking(request, resource_id):
    resource = get_object_or_404(Resource, id=resource_id)

    if request.method == 'POST':
        raw_start = request.POST.get('start_time')
        raw_end = request.POST.get('end_time')
        start_time = parse_local_datetime(raw_start)
        end_time = parse_local_datetime(raw_end)
        purpose = request.POST.get('purpose', '').strip()

        error = None
        if not start_time or not end_time:
            error = 'Please enter valid booking dates and times.'
        elif start_time <= timezone.now():
            error = 'Please select a future booking time.'
        elif end_time <= start_time:
            error = 'End time must be after start time.'
        elif not purpose:
            error = 'Please enter the booking purpose.'

        if error:
            messages.error(request, error)

        elif not is_free(resource, start_time, end_time):

            messages.error(
                request,
                'This resource is already booked for that time. '
                'You can join the waitlist below.'
            )
            query = urlencode({'resource': resource.id, 'start': raw_start, 'end': raw_end})
            return redirect(f"{reverse('bookings:waitlist')}?{query}")

        else:
            Booking.objects.create(
                user=request.user,
                resource=resource,
                start_time=start_time,
                end_time=end_time,
                purpose=purpose,
                status='Pending',
            )
            messages.success(request, 'Your booking request was submitted successfully!')
            return redirect('bookings:booking_list')

    return render(request, 'bookings/create_booking.html', {'resource': resource})


@login_required
@require_POST
def cancel_booking(request, id):
    booking = get_object_or_404(Booking, id=id, user=request.user)

    if booking.status == 'Cancelled':
        messages.warning(request, 'This booking is already cancelled.')
        return redirect('bookings:booking_list')

    booking.status = 'Cancelled'
    booking.save(update_fields=['status'])
    update_waitlist(booking)

    messages.success(request, 'Booking cancelled successfully!')
    return redirect('bookings:booking_list')


# ---------------------------------------------------------------------------
# Calendar / history
# ---------------------------------------------------------------------------

@login_required
def booking_calendar(request):
    today = timezone.localdate()

    try:
        year, month = map(int, request.GET.get('month', '').split('-'))
        first = date(year, month, 1)
    except ValueError:
        first = today.replace(day=1)
    year, month = first.year, first.month

    prev_month = (first - timedelta(days=1)).strftime('%Y-%m')
    next_month = (first + timedelta(days=32)).replace(day=1).strftime('%Y-%m')

    grid = calendar.Calendar(firstweekday=6).monthdatescalendar(year, month)

    bookings = Booking.objects.filter(
        user=request.user,
        start_time__date__range=(grid[0][0], grid[-1][-1]),
    ).select_related('resource').order_by('start_time')

    by_day = {}
    for b in bookings:
        by_day.setdefault(timezone.localtime(b.start_time).date(), []).append(b)

    weeks = [
        [
            {
                'date': d,
                'in_month': d.month == month,
                'is_today': d == today,
                'bookings': by_day.get(d, []),
            }
            for d in week
        ]
        for week in grid
    ]

    return render(request, 'bookings/booking_calendar.html', {
        'weeks': weeks,
        'month_label': first.strftime('%B %Y'),
        'prev_month': prev_month,
        'next_month': next_month,
    })


@login_required
def booking_history(request):
    bookings = Booking.objects.filter(user=request.user).filter(
        Q(end_time__lt=timezone.now()) | Q(status__in=['Cancelled', 'Completed'])
    ).select_related('resource').order_by('-start_time')

    return render(request, 'bookings/booking_history.html', {'bookings': bookings})


# ---------------------------------------------------------------------------
# Conflicts (staff)
# ---------------------------------------------------------------------------

def _conflict_queryset():
    return ConflictLog.objects.select_related(
        'booking__resource', 'booking__user', 'conflicting_booking__user',
    )


@staff_required
def conflict_list(request):
    conflicts = _conflict_queryset().order_by('-detected_at')

    status = request.GET.get('status')
    if status == 'Open':
        conflicts = conflicts.filter(resolution='')
    elif status == 'Resolved':
        conflicts = conflicts.exclude(resolution='')

    return render(request, 'bookings/conflict_list.html', {'conflicts': conflicts})


@staff_required
def conflict_detail(request, id):
    conflict = get_object_or_404(_conflict_queryset(), id=id)
    new_booking = conflict.booking
    alternative = suggest_alternative(
        new_booking.resource, new_booking.start_time, new_booking.end_time,
    )
    return render(request, 'bookings/conflict_detail.html', {
        'conflict': conflict,
        'alternative': alternative,
    })


@staff_required
@require_POST
def resolve_conflict(request, id):
    conflict = get_object_or_404(ConflictLog, id=id, resolution='')
    choice = request.POST.get('resolution')

    existing = conflict.conflicting_booking
    new = conflict.booking

    # Which booking loses for each choice
    losers = {
        'keep_a': new,         # keep the existing booking
        'keep_b': existing,    # keep the new booking
        'reschedule': new,
        'waitlist': new,
    }
    loser = losers.get(choice)

    if loser is None:
        messages.error(request, 'Please choose a resolution.')
        return redirect('bookings:conflict_detail', id=conflict.id)

    loser.status = 'Cancelled'
    loser.save()

    if choice == 'waitlist':
        WaitList.objects.get_or_create(
            user=loser.user,
            resource=loser.resource,
            requested_start=loser.start_time,
            requested_end=loser.end_time,
            status='waiting',
        )

    conflict.resolution = choice
    conflict.save()

    # The cancelled slot may now be free for someone on the waitlist
    update_waitlist(loser)

    messages.success(request, 'Conflict resolved.')
    return redirect('bookings:conflict_list')


# ---------------------------------------------------------------------------
# Waitlist
# ---------------------------------------------------------------------------

@login_required
def waitlist_view(request):
    entries = list(
        WaitList.objects.filter(user=request.user)
        .select_related('resource').order_by('-id')
    )

    # Place in line = active entries for an overlapping slot that came first
    for entry in entries:
        if entry.status in ('waiting', 'notified'):
            entry.queue_position = WaitList.objects.filter(
                resource=entry.resource,
                status__in=['waiting', 'notified'],
                requested_start__lt=entry.requested_end,
                requested_end__gt=entry.requested_start,
                id__lt=entry.id,
            ).count() + 1
        else:
            entry.queue_position = None

    return render(request, 'bookings/waitlist.html', {
        'entries': entries,
        'resources': Resource.objects.all(),
    })


@login_required
@require_POST
def add_to_waitlist(request):
    resource = get_object_or_404(Resource, pk=request.POST.get('resource'))
    start = parse_local_datetime(request.POST.get('start_time'))
    end = parse_local_datetime(request.POST.get('end_time'))

    if not start or not end or end <= start:
        messages.error(request, 'Please enter a valid start and end time.')
        return redirect('bookings:waitlist')

    _, created = WaitList.objects.get_or_create(
        user=request.user,
        resource=resource,
        requested_start=start,
        requested_end=end,
        status='waiting',
    )
    if created:
        messages.success(request, 'You have joined the waitlist.')
    else:
        messages.info(request, 'You are already on the waitlist for this slot.')
    return redirect('bookings:waitlist')


@login_required
@require_POST
def leave_waitlist(request, id):
    entry = get_object_or_404(WaitList, id=id, user=request.user)
    entry.status = 'cancelled'
    entry.save()
    messages.success(request, 'You have left the waitlist.')
    return redirect('bookings:waitlist')


# ---------------------------------------------------------------------------
# Approve / reject (staff)
# ---------------------------------------------------------------------------

def _set_status(request, id, status):
    booking = get_object_or_404(Booking, id=id, status='Pending')


    if status == 'Approved':
        overlaps_approved = check_conflict(
            booking.resource, booking.start_time, booking.end_time,
            exclude_id=booking.id,
        ).filter(status='Approved').exists()

        if overlaps_approved:
            messages.error(request, f'Booking #{booking.id} overlaps an approved booking.')
            return redirect('bookings:pending_bookings')

    booking.status = status
    booking.save(update_fields=['status'])

    # A rejected booking frees its slot for the waitlist
    if status == 'Rejected':
        update_waitlist(booking)

    messages.success(request, f'Booking #{booking.id} {status.lower()}.')
    return redirect('bookings:pending_bookings')


@staff_required
def pending_bookings(request):
    bookings = Booking.objects.filter(status='Pending').select_related(
        'resource', 'user'
    ).order_by('created_at')
    return render(request, 'bookings/pending_bookings.html', {'bookings': bookings})


@staff_required
@require_POST
def approve_booking(request, id):
    return _set_status(request, id, 'Approved')


@staff_required
@require_POST
def reject_booking(request, id):
    return _set_status(request, id, 'Rejected')