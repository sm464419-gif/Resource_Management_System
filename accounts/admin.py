from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, Profile,EmailChangeRequest


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Additional Information", {
            "fields": ("role", "department", "email_verified"),
        }),
    )

    list_display = (
        "username",
        "email",
        "role",
        "department",
        "email_verified",
        "is_staff",
    )


admin.site.register(Profile)
admin.site.register(EmailChangeRequest)