
from datetime import timedelta
import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


def token_expiry():
    return timezone.now() + timedelta(hours=24)


# ==========================================================
# Custom User Model
# ==========================================================

class User(AbstractUser):

    ROLE_CHOICES = [
        ("student", "Student"),
        ("teacher", "Teacher"),
        ("admin", "Administrator"),
    ]

    email = models.EmailField(unique=True)

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="student",
    )

    department = models.CharField(
        max_length=100,
        blank=True,
    )

    # Kept temporarily for compatibility.
    # Email verification is no longer required for registration.
    email_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.username


# ==========================================================
# User Profile
# ==========================================================

class Profile(models.Model):

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    first_name = models.CharField(
        max_length=120,
        blank=True,
    )

    last_name = models.CharField(
        max_length=100,
        blank=True,
    )

    phone = models.CharField(
        max_length=20,
        blank=True,
    )

    profile_picture = models.ImageField(
        upload_to="profile_pictures/",
        blank=True,
        null=True,
    )

    designation = models.CharField(
        max_length=100,
        blank=True,
    )

    def __str__(self):
        return f"{self.user.username}'s profile"


# ==========================================================
# Email Change Request
# ==========================================================

class EmailChangeRequest(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_change_requests",
    )

    new_email = models.EmailField()

    token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    expires_at = models.DateTimeField(
        default=token_expiry,
    )

    used = models.BooleanField(
        default=False,
    )

    def is_valid(self):
        return (
            not self.used
            and timezone.now() < self.expires_at
        )

    def __str__(self):
        return f"Email change for {self.user.username}"
