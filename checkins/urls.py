#urls.py


from django.urls import path
from . import views

app_name = "checkin"

urlpatterns = [
    # Check-in
    path("", views.scan_checkin, name="checkin"),

    # Check-in and no-show history
    path("history/", views.checkin_history, name="checkin_history"),

    # Mark missed bookings as no-show
    path("mark-no-show/", views.mark_no_show, name="mark_no_show"),

    # Release a resource
    path(
        "release/<int:checkin_id>/",
        views.release_resource,
        name="release_resource",
    ),

    # Apply no-show and auto-release policies
    path("apply-policy/", views.apply_policy, name="apply_policy"),

    # Configure no-show policies
    path("policy/", views.no_show_policy_view, name="no_show_policy"),
]