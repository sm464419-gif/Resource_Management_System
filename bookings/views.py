import calendar
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import send_mail
from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_POST

from resources.models import Resource
from .models import Booking, ConflictLog, WaitList

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import Booking

def staff_required(view):
    return login_required(user_passes_test(lambda u: u.is_staff)(view))


@login_required
def booking_list(request):
    bookings = Booking.objects.filter(user=request.user)
    return render(request, 'bookings/booking_list.html', {
        'bookings': bookings
    })


@login_required
def booking_detail(request, id):
    booking = get_object_or_404(
        Booking, id=id, user=request.user
    )
    return render(request, 'bookings/booking_detail.html', {
        'booking': booking
    })


@login_required
def create_booking(request):
    if request.method == 'POST':
        Booking.objects.create(
            user=request.user,
            resource_id=request.POST.get('resource'),
            start_time=request.POST.get('start_time'),
            end_time=request.POST.get('end_time'),
            purpose=request.POST.get('purpose')
        )
        return redirect('bookings:booking_list')

    return render(request, 'bookings/create_booking.html')


@login_required
@require_POST
def cancel_booking(request, id):
    booking = get_object_or_404(
        Booking, id=id, user=request.user
    )
    booking.status = 'Cancelled'
    booking.save()
    return redirect('bookings:booking_list')


def check_conflict(resource, start_time, end_time, exclude_id=None):

    clashes = Booking.objects.filter(
        resource=resource,
        start_time__lt=end_time,  # starts before the new one ends
        end_time__gt=start_time,  # ends after the new one starts
    ).exclude(status__in=['Cancelled', 'Rejected'])

    if exclude_id:
        clashes = clashes.exclude(id=exclude_id)
    return clashes


def suggest_alternative(resource, start_time, end_time):

    duration = end_time - start_time


    later_start = start_time
    for _ in range(48):
        later_start += timedelta(hours=1)
        if not check_conflict(resource, later_start, later_start + duration).exists():
            break
    else:
        later_start = None


    others = Resource.objects.filter(category=resource.category).exclude(pk=resource.pk)
    free_resources = [
        r for r in others
        if not check_conflict(r, start_time, end_time).exists()
    ]

    return {
        'start': later_start,
        'end': later_start + duration if later_start else None,
        'resources': free_resources,
    }


def detect_conflict(booking):

    clashes = check_conflict(
        booking.resource, booking.start_time, booking.end_time,
        exclude_id=booking.id,
    )
    logs = []
    for other in clashes:
        log, _ = ConflictLog.objects.get_or_create(
            booking_a=other,  # the existing booking
            booking_b=booking,  # the new booking
            defaults={'status': 'Open'},
        )
        logs.append(log)
    return logs


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
        day = timezone.localtime(b.start_time).date()
        by_day.setdefault(day, []).append(b)

    weeks = []
    for week in grid:
        weeks.append([
            {
                'date': d,
                'in_month': d.month == month,
                'is_today': d == today,
                'bookings': by_day.get(d, []),
            }
            for d in week
        ])

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

    return render(request, 'bookings/booking_history.html', {
        'bookings': bookings
    })


@staff_required
def conflict_list(request):
    conflicts = ConflictLog.objects.select_related(
        'booking_a__resource', 'booking_a__user', 'booking_b__user'
    ).order_by('-detected_at')

    status = request.GET.get('status')
    if status in ('Open', 'Resolved'):
        conflicts = conflicts.filter(status=status)

    return render(request, 'bookings/conflict_list.html', {
        'conflicts': conflicts
    })


@staff_required
def conflict_detail(request, id):
    conflict = get_object_or_404(ConflictLog, id=id)
    alternative = suggest_alternative(
        conflict.booking_b.resource,
        conflict.booking_b.start_time,
        conflict.booking_b.end_time,
    )
    return render(request, 'bookings/conflict_detail.html', {
        'conflict': conflict,
        'alternative': alternative,
    })


@staff_required
@require_POST
def resolve_conflict(request, id):
    conflict = get_object_or_404(ConflictLog, id=id, status='Open')
    choice = request.POST.get('resolution')
    a, b = conflict.booking_a, conflict.booking_b

    if choice == 'keep_a':
        loser = b
    elif choice in ('keep_b', 'reschedule', 'waitlist'):

        loser = a if choice == 'keep_b' else b
    else:
        messages.error(request, 'Please choose a resolution.')
        return redirect('bookings:conflict_detail', id=conflict.id)

    loser.status = 'Cancelled'
    loser.save()

    if choice == 'waitlist':
        WaitList.objects.get_or_create(
            user=loser.user, resource=loser.resource,
            start_time=loser.start_time, end_time=loser.end_time,
            status='Waiting',
        )

    if choice == 'reschedule':
        send_mail(
            'Please reschedule your booking',
            f'Your booking for {loser.resource.name} clashed with another one. '
            'Please make a new booking for a different time.',
            None, [loser.user.email], fail_silently=True,
        )

    conflict.status = 'Resolved'
    conflict.resolution = choice
    conflict.notes = request.POST.get('notes', '')
    conflict.resolved_by = request.user
    conflict.resolved_at = timezone.now()
    conflict.save()

    # The cancelled slot may now be free for someone on the waitlist
    notify_availability(loser)

    messages.success(request, 'Conflict resolved.')
    return redirect('bookings:conflict_list')


@login_required
def waitlist_view(request):
    entries = WaitList.objects.filter(
        user=request.user
    ).select_related('resource').order_by('-created_at')

    return render(request, 'bookings/waitlist.html', {
        'entries': entries,
        'resources': Resource.objects.all(),
    })


@login_required
@require_POST
def add_to_waitlist(request):
    resource = get_object_or_404(Resource, pk=request.POST.get('resource'))
    start = parse_datetime(request.POST.get('start_time', ''))
    end = parse_datetime(request.POST.get('end_time', ''))

    if not start or not end or end <= start:
        messages.error(request, 'Please enter a valid start and end time.')
        return redirect('bookings:waitlist')

    if timezone.is_naive(start):
        start = timezone.make_aware(start)
    if timezone.is_naive(end):
        end = timezone.make_aware(end)

    _, created = WaitList.objects.get_or_create(
        user=request.user, resource=resource,
        start_time=start, end_time=end, status='Waiting',
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
    entry.status = 'Cancelled'
    entry.save()
    messages.success(request, 'You have left the waitlist.')
    return redirect('bookings:waitlist')


def notify_availability(booking):
    """
    Call this after a booking is cancelled.
    Finds the first waiting user whose slot is now free and emails them.
    """
    waiting = WaitList.objects.filter(
        resource=booking.resource,
        status='Waiting',
        start_time__lt=booking.end_time,
        end_time__gt=booking.start_time,
    ).order_by('created_at')  # first come, first served

    for entry in waiting:
        if check_conflict(entry.resource, entry.start_time, entry.end_time).exists():
            continue  # still taken, try the next person

        entry.status = 'Notified'
        entry.save()
        send_mail(
            'A slot is available',
            f'{entry.resource.name} is now free on '
            f'{entry.start_time:%d %b %Y, %H:%M}. Book it before someone else does!',
            None, [entry.user.email], fail_silently=True,
        )
        return entry  # only the next person is alerted
    return None
