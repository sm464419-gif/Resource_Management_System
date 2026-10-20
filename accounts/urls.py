
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = "accounts"

urlpatterns = [
    # Authentication
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    # User profile
    path("profile/", views.view_profile, name="profile"),
    path("profile/update/", views.update_profile, name="update_profile"),

    # Change password
    path("change-password/", views.change_password, name="change_password"),

    # Change email
    path("change-email/", views.change_email, name="change_email"),
    path("confirm-email-change/<uuid:token>/", views.confirm_email_change, name="confirm_email_change"),

    # Password reset
    path("password-reset/", auth_views.PasswordResetView.as_view(template_name="accounts/password_reset_form.html"), name="password_reset"),
    path("password-reset/done/", auth_views.PasswordResetDoneView.as_view(template_name="accounts/password_reset_done.html"), name="password_reset_done"),
    path("password-reset-confirm/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(template_name="accounts/password_reset_confirm.html"), name="password_reset_confirm"),
    path("password-reset-complete/", auth_views.PasswordResetCompleteView.as_view(template_name="accounts/password_reset_complete.html"), name="password_reset_complete"),
]