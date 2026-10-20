from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

from .models import Profile

User = get_user_model()


class RegisterForm(UserCreationForm):
    email = forms.EmailField()
    department = forms.CharField(max_length=100)

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "department",
            "password1",
            "password2",
        ]

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError(
                "An account with this email already exists."
            )

        return email


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            "first_name",
            "last_name",
            "phone",
            "profile_picture",
            "designation",
        ]


class ChangeEmailForm(forms.Form):
    new_email = forms.EmailField(label="New email address")

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_new_email(self):
        email = self.cleaned_data["new_email"].strip().lower()

        if self.user and email.lower() == self.user.email.lower():
            raise ValidationError(
                "This is already your current email."
            )

        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError(
                "This email address is already in use."
            )

        return email
