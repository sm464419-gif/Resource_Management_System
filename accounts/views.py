import secrets

from django.conf import settings
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
from django.db import transaction
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
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

            # Email verification is not required for registration.
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

            # Invalidate previous pending requests.
            EmailChangeRequest.objects.filter(
                user=request.user,
                used=False,
            ).update(used=True)

            # Generate a six-digit verification code.
            code = f"{secrets.randbelow(1_000_000):06d}"

            change_request = EmailChangeRequest.objects.create(
                user=request.user,
                new_email=new_email,
                verification_code=code,
            )

            try:
                send_mail(
                    subject="Your ResourceHub email verification code",
                    message=(
                        f"Hello {request.user.username},\n\n"
                        "You requested to change your ResourceHub "
                        "email address.\n\n"
                        f"Your six-digit verification code is: {code}\n\n"
                        "Enter this code on the verification page "
                        "to confirm your new email address.\n\n"
                        "This code expires according to your "
                        "email-change request expiry settings.\n\n"
                        "If you did not request this change, "
                        "you can ignore this email.\n\n"
                        "ResourceHub Team"
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[new_email],
                    fail_silently=False,
                )

            except Exception:
                # Invalidate the request if sending the email fails.
                change_request.used = True
                change_request.save(update_fields=["used"])

                messages.error(
                    request,
                    "We couldn't send the verification email. "
                    "Please check the email configuration and try again.",
                )

                return redirect("accounts:change_email")

            messages.success(
                request,
                f"A six-digit verification code has been sent to "
                f"{new_email}.",
            )

            return redirect(
                "accounts:verify_email_change",
                token=change_request.token,
            )

    else:
        form = ChangeEmailForm(user=request.user)

    return render(
        request,
        "accounts/change_email.html",
        {"form": form},
    )


# ==========================================================
# Verify email change using a six-digit code
# ==========================================================

@login_required
def verify_email_change(request, token):
    change_request = get_object_or_404(
        EmailChangeRequest,
        token=token,
        user=request.user,
    )

    # Check expiry and whether the request has already been used.
    if not change_request.is_valid():
        messages.error(
            request,
            "This verification request has expired or was already used. "
            "Please request a new code.",
        )

        return redirect("accounts:change_email")

    if request.method == "POST":
        code = request.POST.get("code", "").strip()

        # Validate the code format.
        if not code.isdigit() or len(code) != 6:
            messages.error(
                request,
                "Please enter a valid six-digit verification code.",
            )

        elif not secrets.compare_digest(
            code,
            change_request.verification_code,
        ):
            messages.error(
                request,
                "The verification code is incorrect. Please try again.",
            )

        else:
            # Check again that another account hasn't claimed this email.
            email_in_use = User.objects.filter(
                email__iexact=change_request.new_email,
            ).exclude(
                pk=request.user.pk,
            ).exists()

            if email_in_use:
                messages.error(
                    request,
                    "This email address is already in use. "
                    "Please request a different one.",
                )

                return redirect("accounts:change_email")

            # Update the email only after successful verification.
            with transaction.atomic():
                user = User.objects.select_for_update().get(
                    pk=request.user.pk,
                )

                # Recheck email uniqueness inside the transaction.
                email_in_use = User.objects.filter(
                    email__iexact=change_request.new_email,
                ).exclude(
                    pk=user.pk,
                ).exists()

                if email_in_use:
                    messages.error(
                        request,
                        "This email address is already in use.",
                    )

                    return redirect("accounts:change_email")

                user.email = change_request.new_email
                user.email_verified = True

                user.save(
                    update_fields=["email", "email_verified"],
                )

                change_request.used = True
                change_request.save(
                    update_fields=["used"],
                )

                # Invalidate any other pending requests for this user.
                EmailChangeRequest.objects.filter(
                    user=user,
                    used=False,
                ).update(used=True)

            messages.success(
                request,
                "Your email address has been changed successfully.",
            )

            return redirect("accounts:profile")

    return render(
        request,
        "accounts/verify_email_change.html",
        {"change_request": change_request},
    )