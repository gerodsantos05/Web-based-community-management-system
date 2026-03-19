from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.models import User


class SignUpForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="Confirm password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    class Meta:
        model = User
        fields = ["username", "email"]

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("A user with that email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            self.add_error("password2", "Passwords do not match.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        # Ensure frontend signup cannot create staff/superuser accounts
        user.is_staff = False
        user.is_superuser = False
        if commit:
            user.save()
        return user


class SignInForm(forms.Form):
    username_or_email = forms.CharField(label="Username or Email", max_length=254)
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    def clean(self):
        cleaned_data = super().clean()
        username_or_email = cleaned_data.get("username_or_email")
        password = cleaned_data.get("password")

        if not username_or_email or not password:
            return cleaned_data

        user = None

        # Try username first
        user = authenticate(username=username_or_email, password=password)

        # Fall back to email
        if user is None:
            try:
                user_obj = User.objects.get(email__iexact=username_or_email)
                user = authenticate(username=user_obj.username, password=password)
            except User.DoesNotExist:
                user = None

        # Handle an invalid password/username case first
        if user is None:
            raise forms.ValidationError("Invalid credentials.")

        if not user.is_active:
            raise forms.ValidationError("Invalid credentials.")

        # Explicitly deny access to non-superusers
        if not user.is_superuser:
            raise forms.ValidationError("Access denied. Only administrators can log in.")

        cleaned_data["user"] = user
        return cleaned_data
