from django.conf import settings
from django.contrib import messages
from django.contrib.auth import (
    authenticate,
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
from django.views.decorators.http import require_POST

from .forms import RegisterForm, ProfileForm, ChangeEmailForm
from .models import Profile, EmailVerificationToken, EmailChangeRequest

User = get_user_model()


def register_view(request):
    if request.user.is_authenticated:
        return redirect("view_profile")

    if request.method == "POST":
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save(commit=False)
            user.email_verified = False
            user.save()

            Profile.objects.create(user=user)

            # Invalidate older verification tokens, if any.
            EmailVerificationToken.objects.filter(
                user=user, used=False
            ).update(used=True)

            token = EmailVerificationToken.objects.create(user=user)

            verification_url = request.build_absolute_uri(
                reverse(
                    "verify_email",
                    kwargs={"token": token.token},
                )
            )

            send_mail(
                subject="Verify your ResourceHub email",
                message=(
                    f"Hello {user.username},\n\n"
                    "Please verify your email using this link:\n"
                    f"{verification_url}\n\n"
                    "This link expires in 24 hours."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )

            messages.success(
                request,
                "Account created. Check your email to verify it.",
            )
            return redirect("login")
    else:
        form = RegisterForm()

    return render(
        request,
        "accounts/register.html",
        {"form": form},
    )


def login_view(request):
    if request.user.is_authenticated:
        return redirect("view_profile")

    if request.method == "POST":
        form = AuthenticationForm(
            request,
            data=request.POST,
        )

        if form.is_valid():
            user = form.get_user()

            if not user.email_verified:
                messages.error(
                    request,
                    "Please verify your email before logging in.",
                )
            else:
                login(request, user)
                return redirect("view_profile")
    else:
        form = AuthenticationForm(request)

    return render(
        request,
        "accounts/login.html",
        {"form": form},
    )


@login_required
@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, "You have logged out.")
    return redirect("login")


def verify_email(request, token):
    verification = get_object_or_404(
        EmailVerificationToken,
        token=token,
    )

    if not verification.is_valid():
        messages.error(
            request,
            "This verification link has expired or was already used.",
        )
        return redirect("resend_verification")

    user = verification.user
    user.email_verified = True
    user.save(update_fields=["email_verified"])

    verification.used = True
    verification.save(update_fields=["used"])

    # Invalidate any other outstanding verification links.
    EmailVerificationToken.objects.filter(
        user=user, used=False
    ).update(used=True)

    messages.success(
        request,
        "Your email has been verified. You can now log in.",
    )
    return redirect("login")


@require_POST
def resend_verification(request):
    email = request.POST.get("email", "").strip()

    user = User.objects.filter(email__iexact=email).first()

    # Avoid revealing whether an email is registered.
    if user and not user.email_verified:
        EmailVerificationToken.objects.filter(
            user=user, used=False
        ).update(used=True)

        token = EmailVerificationToken.objects.create(user=user)

        verification_url = request.build_absolute_uri(
            reverse(
                "verify_email",
                kwargs={"token": token.token},
            )
        )

        send_mail(
            subject="Your ResourceHub verification link",
            message=(
                "Use this link to verify your email:\n"
                f"{verification_url}\n\n"
                "This link expires in 24 hours."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

    messages.info(
        request,
        "If the account exists and needs verification, "
        "a new link has been sent.",
    )
    return redirect("login")


@login_required
def view_profile(request):
    profile, created = Profile.objects.get_or_create(
        user=request.user
    )

    return render(
        request,
        "accounts/profile.html",
        {
            "profile": profile,
            "account": request.user,
        },
    )


@login_required
def update_profile(request):
    profile, created = Profile.objects.get_or_create(
        user=request.user
    )

    if request.method == "POST":
        form = ProfileForm(
            request.POST,
            request.FILES,
            instance=profile,
        )

        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("view_profile")
    else:
        form = ProfileForm(instance=profile)

    return render(
        request,
        "accounts/update_profile.html",
        {"form": form, "profile": profile},
    )


@login_required
def change_password(request):
    if request.method == "POST":
        form = PasswordChangeForm(
            user=request.user,
            data=request.POST,
        )

        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(
                request,
                "Your password has been changed.",
            )
            return redirect("view_profile")
    else:
        form = PasswordChangeForm(user=request.user)

    return render(
        request,
        "accounts/change_password.html",
        {"form": form},
    )


@login_required
def change_email(request):
    if request.method == "POST":
        form = ChangeEmailForm(
            request.POST,
            user=request.user,
        )

        if form.is_valid():
            new_email = form.cleaned_data["new_email"]

            # Invalidate any older pending email-change requests.
            EmailChangeRequest.objects.filter(
                user=request.user, used=False
            ).update(used=True)

            change_request = EmailChangeRequest.objects.create(
                user=request.user,
                new_email=new_email,
            )

            confirmation_url = request.build_absolute_uri(
                reverse(
                    "confirm_email_change",
                    kwargs={"token": change_request.token},
                )
            )

            send_mail(
                subject="Confirm your new ResourceHub email",
                message=(
                    "Confirm your new email address using this link:\n"
                    f"{confirmation_url}\n\n"
                    "Your email will not change until you confirm it. "
                    "This link expires in 24 hours."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[new_email],
                fail_silently=False,
            )

            messages.success(
                request,
                "A confirmation link has been sent to your new email.",
            )
            return redirect("view_profile")
    else:
        form = ChangeEmailForm(user=request.user)

    return render(
        request,
        "accounts/change_email.html",
        {"form": form},
    )


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
        return redirect("change_email")

    if User.objects.filter(
        email__iexact=change_request.new_email
    ).exclude(pk=request.user.pk).exists():
        messages.error(
            request,
            "That email address is already in use. "
            "Please request a different one.",
        )
        return redirect("change_email")

    user = request.user
    user.email = change_request.new_email
    user.email_verified = True
    user.save(update_fields=["email", "email_verified"])

    change_request.used = True
    change_request.save(update_fields=["used"])

    EmailChangeRequest.objects.filter(
        user=user, used=False
    ).update(used=True)

    messages.success(
        request,
        "Your email address has been changed successfully.",
    )
    return redirect("view_profile")
