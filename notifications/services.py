from django.conf import settings
from django.core.mail import send_mail

from .models import Notification


def send_notification(user, notification_type, message, send_email=True):

    # Create an in-app notification
    notification = Notification.objects.create(
        user=user,
        notification_type=notification_type,
        message=message
    )

    # Send email notification
    if send_email and user.email:
        send_mail(
            subject="ResourceHub Notification",
            message=message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[user.email],
            fail_silently=True,
        )

    return notification