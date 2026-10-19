from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import AdminActivityLog, RoleApplication, UserProfile, VolunteerOjtSchedule


User = get_user_model()


class AdminCreatedProfileFieldsTests(TestCase):
    def setUp(self):
        admin = User.objects.create_superuser(
            username="profile-fields-admin",
            email="profile-fields-admin@example.com",
            password="T#6-vrgP9E-L3x!Wqk4-2026",
        )
        self.client.force_login(admin)

    def test_create_volunteer_saves_gender_and_address(self):
        response = self.client.post(
            reverse("create_volunteer"),
            {
                "full_name": "Profile Fields Volunteer",
                "email": "profile-fields-volunteer@example.com",
                "phone": "09181234567",
                "gender": "female",
                "address_line": "123 Sampaguita St, Bacoor",
                "availability": "Weekends",
                "username": "profile-fields-volunteer",
                "password": "T#6-vrgP9E-L3x!Wqk4-2026",
                "status": "active",
                "volunteer_type": UserProfile.VOLUNTEER_TYPE_OJT,
                "required_ojt_hours": "120",
                "schedule_days": "[0, 2, 4]",
            },
        )

        self.assertEqual(response.status_code, 201, response.content)
        profile = UserProfile.objects.get(user__username="profile-fields-volunteer")
        self.assertEqual(profile.gender, "female")
        self.assertEqual(profile.address_line, "123 Sampaguita St, Bacoor")
        self.assertEqual(profile.volunteer_type, UserProfile.VOLUNTEER_TYPE_OJT)
        self.assertEqual(profile.required_ojt_hours, 120)
        self.assertEqual(VolunteerOjtSchedule.objects.get(volunteer=profile.user).weekdays, [0, 2, 4])
        self.assertEqual(AdminActivityLog.objects.filter(section="Volunteers", record_id=str(profile.user_id)).count(), 1)

    def test_create_community_volunteer_skips_ojt_schedule(self):
        response = self.client.post(
            reverse("create_volunteer"),
            {
                "full_name": "Community Volunteer",
                "email": "community-volunteer@example.com",
                "phone": "09181234567",
                "gender": "female",
                "address_line": "Community Address",
                "availability": "Weekends",
                "username": "community-volunteer",
                "password": "T#6-vrgP9E-L3x!Wqk4-2026",
                "status": "active",
                "volunteer_type": UserProfile.VOLUNTEER_TYPE_COMMUNITY,
            },
        )

        self.assertEqual(response.status_code, 201, response.content)
        profile = UserProfile.objects.get(user__username="community-volunteer")
        self.assertEqual(profile.volunteer_type, UserProfile.VOLUNTEER_TYPE_COMMUNITY)
        self.assertFalse(VolunteerOjtSchedule.objects.filter(volunteer=profile.user).exists())
        self.assertEqual(AdminActivityLog.objects.filter(section="Volunteers", record_id=str(profile.user_id)).count(), 1)

    def test_create_regular_user_saves_gender_and_address(self):
        response = self.client.post(
            reverse("create_regular_user"),
            {
                "full_name": "Profile Fields User",
                "username": "profile-fields-user",
                "email": "profile-fields-user@example.com",
                "phone": "09181234567",
                "gender": "other",
                "address_line": "456 Mabini St, Bacoor",
                "password": "T#6-vrgP9E-L3x!Wqk4-2026",
                "confirm_password": "T#6-vrgP9E-L3x!Wqk4-2026",
            },
        )

        self.assertEqual(response.status_code, 201, response.content)
        profile = UserProfile.objects.get(user__username="profile-fields-user")
        self.assertEqual(profile.gender, "other")
        self.assertEqual(profile.address_line, "456 Mabini St, Bacoor")

    def test_create_admin_saves_gender_and_address(self):
        response = self.client.post(
            reverse("create_admin"),
            {
                "full_name": "Profile Fields Admin",
                "username": "profile-fields-new-admin",
                "email": "profile-fields-new-admin@example.com",
                "gender": "prefer_not",
                "address_line": "789 Rizal Ave, Bacoor",
                "password": "T#6-vrgP9E-L3x!Wqk4-2026",
                "confirm_password": "T#6-vrgP9E-L3x!Wqk4-2026",
            },
        )

        self.assertEqual(response.status_code, 201, response.content)
        profile = UserProfile.objects.get(user__username="profile-fields-new-admin")
        self.assertEqual(profile.gender, "prefer_not")
        self.assertEqual(profile.address_line, "789 Rizal Ave, Bacoor")

    def test_create_beneficiary_saves_gender_and_address(self):
        parent_user = User.objects.create_user(username="profile-fields-parent", email="parent@example.com")
        UserProfile.objects.create(
            user=parent_user,
            account_role=UserProfile.ROLE_BENEFICIARY,
            beneficiary_type=UserProfile.BENEFICIARY_TYPE_HAPPY_NANAYS,
        )
        response = self.client.post(
            reverse("create_beneficiary"),
            {
                "full_name": "Profile Fields Beneficiary",
                "email": "profile-fields-beneficiary@example.com",
                "phone": "09181234567",
                "gender": "male",
                "address": "321 Mabini St, Bacoor",
                "username": "profile-fields-beneficiary",
                "password": "T#6-vrgP9E-L3x!Wqk4-2026",
                "status": "Active",
                "beneficiary_type": UserProfile.BENEFICIARY_TYPE_HAPPY_KIDS,
                "linked_parent_id": parent_user.pk,
            },
        )

        self.assertEqual(response.status_code, 201, response.content)
        profile = UserProfile.objects.get(user__username="profile-fields-beneficiary")
        self.assertEqual(profile.gender, "male")
        self.assertEqual(profile.address_line, "321 Mabini St, Bacoor")
        self.assertEqual(profile.beneficiary_type, UserProfile.BENEFICIARY_TYPE_HAPPY_KIDS)
        self.assertIsNone(profile.linked_parent_id)
        self.assertEqual(AdminActivityLog.objects.filter(section="Beneficiaries", record_id=str(profile.user_id)).count(), 1)

    def test_beneficiary_type_change_adds_only_one_edit_log(self):
        created = self.client.post(
            reverse("create_beneficiary"),
            {
                "full_name": "Type Change Beneficiary",
                "email": "type-change@example.com",
                "phone": "09181239999",
                "gender": "female",
                "address": "Type Change Address",
                "username": "type-change-beneficiary",
                "password": "T#6-vrgP9E-L3x!Wqk4-2026",
                "status": "Active",
                "beneficiary_type": UserProfile.BENEFICIARY_TYPE_HAPPY_KIDS,
            },
        )
        self.assertEqual(created.status_code, 201, created.content)
        user = User.objects.get(username="type-change-beneficiary")
        application_id = created.json()["application"]["applicationId"]
        update_data = {
            "beneficiary_application_id": application_id,
            "full_name": "Type Change Beneficiary",
            "contact_details": "type-change@example.com / 09181239999",
            "gender": "female",
            "supporting_information": "Type Change Address",
            "status": "Active",
            "beneficiary_type": UserProfile.BENEFICIARY_TYPE_HAPPY_HEARTS,
        }
        updated = self.client.post(reverse("update_beneficiary_profile"), update_data)
        self.assertEqual(updated.status_code, 200, updated.content)
        unchanged = self.client.post(reverse("update_beneficiary_profile"), update_data)
        self.assertEqual(unchanged.status_code, 200, unchanged.content)
        self.assertEqual(
            AdminActivityLog.objects.filter(section="Beneficiaries", record_id=str(user.pk)).count(),
            2,
        )

    def test_people_directory_profile_modals_include_gender_and_address(self):
        for directory in ("regular_users", "admins", "volunteers", "beneficiaries"):
            with self.subTest(directory=directory):
                response = self.client.get(reverse(directory))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "Gender")
                self.assertContains(response, "Address")

    def test_update_regular_user_profile_saves_gender_and_address(self):
        user = User.objects.create_user(
            username="profile-fields-update-user",
            email="profile-fields-update-user@example.com",
            password="T#6-vrgP9E-L3x!Wqk4-2026",
        )
        UserProfile.objects.create(user=user, account_role=UserProfile.ROLE_REGULAR)

        response = self.client.post(
            reverse("update_regular_user_profile"),
            {
                "user_id": user.pk,
                "full_name": "Updated Profile User",
                "username": user.username,
                "email": user.email,
                "phone": "09181234567",
                "gender": "female",
                "address_line": "111 Updated St, Bacoor",
                "status": "active",
            },
        )

        self.assertEqual(response.status_code, 200, response.content)
        user.userprofile.refresh_from_db()
        self.assertEqual(user.userprofile.gender, "female")
        self.assertEqual(user.userprofile.address_line, "111 Updated St, Bacoor")

    def test_update_admin_profile_saves_gender_and_address(self):
        admin = User.objects.get(username="profile-fields-admin")

        response = self.client.post(
            reverse("update_admin_profile"),
            {
                "admin_id": admin.pk,
                "full_name": "Updated Profile Admin",
                "username": admin.username,
                "email": admin.email,
                "gender": "other",
                "address_line": "222 Updated St, Bacoor",
                "status": "active",
            },
        )

        self.assertEqual(response.status_code, 200, response.content)
        admin.userprofile.refresh_from_db()
        self.assertEqual(admin.userprofile.gender, "other")
        self.assertEqual(admin.userprofile.address_line, "222 Updated St, Bacoor")

    def test_update_volunteer_profile_saves_gender_and_address(self):
        volunteer = User.objects.create_user(
            username="profile-fields-update-volunteer",
            email="profile-fields-update-volunteer@example.com",
            password="T#6-vrgP9E-L3x!Wqk4-2026",
        )
        UserProfile.objects.create(user=volunteer, account_role=UserProfile.ROLE_VOLUNTEER)

        response = self.client.post(
            reverse("update_volunteer_profile"),
            {
                "volunteer_user_id": volunteer.pk,
                "full_name": "Updated Profile Volunteer",
                "email": volunteer.email,
                "phone": "09181234567",
                "gender": "prefer_not",
                "address_line": "333 Updated St, Bacoor",
                "availability": "Weekends",
                "volunteer_type": "ojt",
                "status": "Active",
            },
        )

        self.assertEqual(response.status_code, 200, response.content)
        volunteer.userprofile.refresh_from_db()
        self.assertEqual(volunteer.userprofile.gender, "prefer_not")
        self.assertEqual(volunteer.userprofile.address_line, "333 Updated St, Bacoor")

    def test_update_beneficiary_profile_saves_gender_and_address(self):
        beneficiary = User.objects.create_user(
            username="profile-fields-update-beneficiary",
            email="profile-fields-update-beneficiary@example.com",
            password="T#6-vrgP9E-L3x!Wqk4-2026",
        )
        profile = UserProfile.objects.create(
            user=beneficiary,
            account_role=UserProfile.ROLE_BENEFICIARY,
        )
        application = RoleApplication.objects.create(
            user=beneficiary,
            role=RoleApplication.ROLE_BENEFICIARY,
            status=RoleApplication.STATUS_APPROVED,
            full_name="Profile Fields Beneficiary",
            contact_details="profile-fields-update-beneficiary@example.com / 09181234567",
        )

        response = self.client.post(
            reverse("update_beneficiary_profile"),
            {
                "beneficiary_application_id": application.pk,
                "full_name": "Updated Profile Beneficiary",
                "contact_details": "profile-fields-update-beneficiary@example.com / 09181234567",
                "gender": "female",
                "supporting_information": "444 Updated St, Bacoor",
                "status": "Active",
            },
        )

        self.assertEqual(response.status_code, 200, response.content)
        profile.refresh_from_db()
        self.assertEqual(profile.gender, "female")
        self.assertEqual(profile.address_line, "444 Updated St, Bacoor")
