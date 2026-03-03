from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import UserProfile


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=False)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing} form-input".strip()

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        if " " in username:
            raise forms.ValidationError("Username cannot contain spaces.")
        return username


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing} form-input".strip()


class ProfileSettingsForm(forms.ModelForm):
    username = forms.CharField(max_length=150, required=True, label="Username")

    class Meta:
        model = UserProfile
        fields = ("username", "display_name", "avatar", "preferred_language")
        labels = {
            "display_name": "Display name",
            "avatar": "Profile photo",
            "preferred_language": "Language",
        }

    def __init__(self, *args, user=None, **kwargs):
        if user is None:
            raise ValueError("ProfileSettingsForm requires user instance")
        self.user = user
        super().__init__(*args, **kwargs)

        self.fields["username"].initial = user.username
        self.fields["display_name"].required = False
        self.fields["avatar"].required = False

        for field in self.fields.values():
            widget = field.widget
            existing = widget.attrs.get("class", "")
            if isinstance(widget, forms.ClearableFileInput):
                widget.attrs["class"] = f"{existing} form-input".strip()
            else:
                widget.attrs["class"] = f"{existing} form-input".strip()

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        if not username:
            raise forms.ValidationError("Username is required.")
        if " " in username:
            raise forms.ValidationError("Username cannot contain spaces.")

        exists = User.objects.exclude(pk=self.user.pk).filter(username__iexact=username).exists()
        if exists:
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_display_name(self):
        return (self.cleaned_data.get("display_name") or "").strip()

    def save(self, commit=True):
        profile = super().save(commit=False)
        self.user.username = self.cleaned_data["username"]

        if commit:
            self.user.save(update_fields=["username"])
            profile.user = self.user
            profile.save()
        return profile
