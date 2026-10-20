
from django.contrib import messages
from django.contrib.auth import (
    get_user_model,
    login,
    logout,
    update_session_auth_hash,
)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
)
from django.core.mail import send_mail
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.urls import reverse
from django.conf import settings
from django.views.decorators.http import require_POST

from .forms import RegisterForm, ProfileForm, ChangeEmailForm
from .models import Profile, EmailChangeRequest


User = get_user_model()


# ==========================================================
# Registration
# ==========================================================

def register_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:profile")

    if request.method == "POST":
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save(commit=False)

            # Email verification is not required.
            # Set this to True if the field still exists in your model.
            user.email_verified = True

            user.save()

            # Create the user's profile.
            Profile.objects.get_or_create(user=user)

            messages.success(
                request,
                "Your account has been created successfully. "
                "You can now log in.",
            )

            return redirect("accounts:login")

    else:
        form = RegisterForm()

    return render(
        request,
        "accounts/register.html",
        {"form": form},
    )


# ==========================================================
# Login
# ==========================================================

def login_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:profile")

    if request.method == "POST":
        form = AuthenticationForm(
            request,
            data=request.POST,
        )

        if form.is_valid():
            user = form.get_user()

            # No email verification check is needed.
            login(request, user)

            messages.success(
                request,
                "You have logged in successfully.",
            )

            return redirect("accounts:profile")

    else:
        form = AuthenticationForm(request)

    return render(
        request,
        "accounts/login.html",
        {"form": form},
    )


# ==========================================================
# Logout
# ==========================================================

@login_required
@require_POST
def logout_view(request):
    logout(request)

    messages.success(
        request,
        "You have logged out successfully.",
    )

    return redirect("accounts:login")


# ==========================================================
# View profile
# ==========================================================

@login_required
def view_profile(request):
    profile, created = Profile.objects.get_or_create(
        user=request.user,
    )

    return render(
        request,
        "accounts/profile.html",
        {
            "profile": profile,
            "account": request.user,
        },
    )


# ==========================================================
# Update profile
# ==========================================================

@login_required
def update_profile(request):
    profile, created = Profile.objects.get_or_create(
        user=request.user,
    )

    if request.method == "POST":
        form = ProfileForm(
            request.POST,
            request.FILES,
            instance=profile,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Your profile has been updated successfully.",
            )

            return redirect("accounts:profile")

    else:
        form = ProfileForm(instance=profile)

    return render(
        request,
        "accounts/profile_edit.html",
        {
            "form": form,
            "profile": profile,
        },
    )


# ==========================================================
# Change password
# ==========================================================

@login_required
def change_password(request):
    if request.method == "POST":
        form = PasswordChangeForm(
            user=request.user,
            data=request.POST,
        )

        if form.is_valid():
            user = form.save()

            # Keep the user logged in after changing the password.
            update_session_auth_hash(request, user)

            messages.success(
                request,
                "Your password has been changed successfully.",
            )

            return redirect("accounts:profile")

    else:
        form = PasswordChangeForm(user=request.user)

    return render(
        request,
        "accounts/change_password.html",
        {"form": form},
    )


# ==========================================================
# Request email change
# ==========================================================

@login_required
def change_email(request):
    if request.method == "POST":
        form = ChangeEmailForm(
            request.POST,
            user=request.user,
        )

        if form.is_valid():
            new_email = form.cleaned_data["new_email"]

            # Invalidate older pending email-change requests.
            EmailChangeRequest.objects.filter(
                user=request.user,
                used=False,
            ).update(used=True)

            change_request = EmailChangeRequest.objects.create(
                user=request.user,
                new_email=new_email,
            )

            confirmation_url = request.build_absolute_uri(
                reverse(
                    "accounts:confirm_email_change",
                    kwargs={"token": change_request.token},
                )
            )

            send_mail(
                subject="Confirm your new ResourceHub email",
                message=(
                    "Confirm your new email address using this link:\n"
                    f"{confirmation_url}\n\n"
                    "Your email address will not change until "
                    "you confirm it. This link expires in 24 hours."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[new_email],
                fail_silently=False,
            )

            messages.success(
                request,
                "A confirmation link has been sent to your new email.",
            )

            return redirect("accounts:profile")

    else:
        form = ChangeEmailForm(user=request.user)

    return render(
        request,
        "accounts/change_email.html",
        {"form": form},
    )


# ==========================================================
# Confirm email change
# ==========================================================

@login_required
def confirm_email_change(request, token):
    change_request = get_object_or_404(
        EmailChangeRequest,
        token=token,
        user=request.user,
    )

    if not change_request.is_valid():
        messages.error(
            request,
            "This email-change link has expired or was already used.",
        )

        return redirect("accounts:change_email")

    # Ensure the new email address is not used by another account.
    email_in_use = User.objects.filter(
        email__iexact=change_request.new_email,
    ).exclude(
        pk=request.user.pk,
    ).exists()

    if email_in_use:
        messages.error(
            request,
            "That email address is already in use. "
            "Please request a different one.",
        )

        return redirect("accounts:change_email")

    user = request.user
    user.email = change_request.new_email

    # Keep this if email_verified still exists in your User model.
    user.email_verified = True

    user.save(
        update_fields=["email", "email_verified"],
    )

    change_request.used = True
    change_request.save(update_fields=["used"])

    # Invalidate other pending email-change requests.
    EmailChangeRequest.objects.filter(
        user=user,
        used=False,
    ).update(used=True)

    messages.success(
        request,
        "Your email address has been changed successfully.",
    )

    return redirect("accounts:profile")
