from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.models import User

from .models import ResourceLibraryMaterial, RoleApplication, SkillLearningMaterial, SkillLearningTopic


SKILL_LEARNING_FILTER_CHOICES = (
    ("Community", "Community"),
    ("Children", "Children"),
    ("New", "New"),
    ("Popular", "Popular"),
)


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
        user = authenticate(username=username_or_email, password=password, backend='django.contrib.auth.backends.ModelBackend')

        # Fall back to email
        if user is None:
            try:
                user_obj = User.objects.get(email__iexact=username_or_email)
                user = authenticate(username=user_obj.username, password=password, backend='django.contrib.auth.backends.ModelBackend')
            except User.DoesNotExist:
                user = None

        # Handle an invalid password/username case first
        if user is None:
            raise forms.ValidationError("Invalid credentials.")

        if not user.is_active:
            raise forms.ValidationError("Invalid credentials.")

        cleaned_data["user"] = user
        return cleaned_data


class BeneficiaryApplicationForm(forms.ModelForm):
    class Meta:
        model = RoleApplication
        fields = ["full_name", "contact_details", "reason_for_assistance", "supporting_information"]
        labels = {
            "full_name": "Full Name",
            "contact_details": "Contact Details",
            "reason_for_assistance": "Reason for Assistance",
            "supporting_information": "Supporting Information",
        }
        widgets = {
            "contact_details": forms.TextInput(attrs={"placeholder": "Phone number and/or email"}),
            "reason_for_assistance": forms.Textarea(attrs={"rows": 4, "placeholder": "Why do you need assistance?"}),
            "supporting_information": forms.Textarea(attrs={"rows": 4, "placeholder": "Family situation, documents, or other notes"}),
        }

    def save(self, user=None, commit=True):
        application = super().save(commit=False)
        application.user = user
        application.role = RoleApplication.ROLE_BENEFICIARY
        application.status = RoleApplication.STATUS_PENDING
        if commit:
            application.save()
        return application


class VolunteerApplicationForm(forms.ModelForm):
    class Meta:
        model = RoleApplication
        fields = ["full_name", "contact_details", "skills", "availability", "areas_of_interest"]
        labels = {
            "full_name": "Full Name",
            "contact_details": "Contact Details",
            "skills": "Skills",
            "availability": "Availability",
            "areas_of_interest": "Areas of Interest",
        }
        widgets = {
            "contact_details": forms.TextInput(attrs={"placeholder": "Phone number and/or email"}),
            "skills": forms.Textarea(attrs={"rows": 4, "placeholder": "List your strongest skills"}),
            "availability": forms.TextInput(attrs={"placeholder": "Days, times, or schedule preferences"}),
            "areas_of_interest": forms.Textarea(attrs={"rows": 4, "placeholder": "Where would you like to help?"}),
        }

    def save(self, user=None, commit=True):
        application = super().save(commit=False)
        application.user = user
        application.role = RoleApplication.ROLE_VOLUNTEER
        application.status = RoleApplication.STATUS_PENDING
        if commit:
            application.save()
        return application

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["skills"].required = False
        self.fields["areas_of_interest"].required = False


class SkillLearningTopicForm(forms.ModelForm):
    filter_tags = forms.MultipleChoiceField(
        choices=SKILL_LEARNING_FILTER_CHOICES,
        required=True,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = SkillLearningTopic
        fields = ["title", "description", "badge_label", "cover_image", "cover_image_url", "filter_tags"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "cover_image_url": forms.URLInput(attrs={"placeholder": "https://..."}),
        }

    def clean_filter_tags(self):
        values = self.cleaned_data.get("filter_tags") or []
        ordered_values = []
        for value in values:
            if value not in ordered_values:
                ordered_values.append(value)
        return ordered_values

    def clean(self):
        cleaned_data = super().clean()
        cover_image = cleaned_data.get("cover_image")
        cover_image_url = str(cleaned_data.get("cover_image_url", "") or "").strip()
        if not cover_image and not cover_image_url and not getattr(self.instance, "cover_image", None) and not getattr(self.instance, "cover_image_url", ""):
            raise forms.ValidationError("Provide a cover image or a cover image URL.")
        return cleaned_data


class SkillLearningMaterialForm(forms.ModelForm):
    class Meta:
        model = SkillLearningMaterial
        fields = ["material_type", "title", "description", "file_upload", "external_url"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "external_url": forms.URLInput(attrs={"placeholder": "https://..."}),
        }

    def clean(self):
        cleaned_data = super().clean()
        file_upload = cleaned_data.get("file_upload")
        external_url = str(cleaned_data.get("external_url", "") or "").strip()
        if not file_upload and not external_url and not getattr(self.instance, "file_upload", None) and not getattr(self.instance, "external_url", ""):
            raise forms.ValidationError("Upload a file or provide a link for the material.")
        return cleaned_data


class ResourceLibraryMaterialForm(forms.ModelForm):
    class Meta:
        model = ResourceLibraryMaterial
        fields = ["title", "category", "custom_category", "description", "file_upload", "external_url", "is_published"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "file_upload": forms.FileInput(),
            "external_url": forms.URLInput(attrs={"placeholder": "https://..."}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "rla-control"
        self.fields["title"].widget.attrs["placeholder"] = "e.g. Volunteer Safety Guide"
        self.fields["custom_category"].widget.attrs["placeholder"] = "e.g. First Aid"
        category_choices = [(value, label) for value, label in self.fields["category"].choices if value]
        self.fields["category"].choices = [("", "Select a category"), *category_choices]
        self.fields["category"].required = False
        self.fields["category"].widget.attrs.update({
            "class": "rla-native-select",
            "aria-hidden": "true",
            "tabindex": "-1",
        })

    def clean_category(self):
        category = self.cleaned_data.get("category")
        if not category:
            raise forms.ValidationError("Select a category.")
        return category
