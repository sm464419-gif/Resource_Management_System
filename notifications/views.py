
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Notification


@login_required
def notification_list(request):
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')

    unread_count = notifications.filter(is_read=False).count()

    return render(request, 'notifications/notifications.html', {
        'notifications': notifications,
        'unread_count': unread_count,
    })


@login_required
def mark_as_read(request, notification_id):
    notification = get_object_or_404(
        Notification,
        id=notification_id,
        user=request.user
    )

    notification.is_read = True
    notification.save()

    return redirect('notifications:notification_list')



