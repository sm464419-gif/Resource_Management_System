from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import Booking


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