from django.urls import path
from . import views

app_name = "checkins"

urlpatterns = [
    # Check-in page (camera scan, pasted code, or button when REQUIRE_QR is False)
    path("", views.scan_checkin, name="checkins"),

    # Opened when a phone camera scans the resource's QR code
    path("scan/<str:code>/", views.qr_checkin, name="qr_checkin"),

    path("history/", views.checkin_history, name="checkin_history"),
    path("mark-no-show/", views.mark_no_show, name="mark_no_show"),
    path("release/<int:checkin_id>/", views.release_resource, name="release_resource"),
    path("apply-policy/", views.apply_policy, name="apply_policy"),
    path("policy/", views.no_show_policy_view, name="no_show_policy"),
]