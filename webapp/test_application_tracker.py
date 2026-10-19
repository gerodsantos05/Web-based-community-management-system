from datetime import date
from io import BytesIO
import json
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.urls import reverse
from PIL import Image

from .models import RoleApplication, RoleApplicationDocument, UserProfile
from .views import (
    _serialize_pending_beneficiary_application,
    _serialize_pending_volunteer_application,
    _serialize_user_role_application,
    index,
)


class ApplicationTrackerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tracker-user", password="test-password")
        UserProfile.objects.create(user=self.user)
        self.application = RoleApplication.objects.create(
            user=self.user,
            role=RoleApplication.ROLE_BENEFICIARY,
            track="happy_kids",
            full_name="Tracker User",
            contact_details="09170000000 / tracker@example.com",
            reason_for_assistance="School support",
            supporting_information="Bacoor City",
        )
        self.client.force_login(self.user)

    def tearDown(self):
        for document in RoleApplicationDocument.objects.filter(application__user=self.user):
            document.file.delete(save=False)
        super().tearDown()

    def render_homepage_view(self):
        request = RequestFactory().get(reverse("home"))
        request.user = self.user
        with patch("webapp.views.render", return_value=HttpResponse()) as render_mock:
            response = index(request)
        return response, render_mock.call_args.args[2]

    def test_homepage_shows_every_submitted_application_to_its_owner(self):
        profile = UserProfile.objects.get(user=self.user)
        profile.account_role = UserProfile.ROLE_BENEFICIARY
        profile.save(update_fields=["account_role"])
        RoleApplication.objects.create(
            user=self.user,
            role=RoleApplication.ROLE_VOLUNTEER,
            track="intern",
            status=RoleApplication.STATUS_APPROVED,
            full_name="Tracker User",
            contact_details="09170000000",
        )

        response, context = self.render_homepage_view()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(context["application_tracker_items"]), 2)
        self.assertEqual(context["application_tracker_items"][0]["statusLabel"], "Approved")

    def test_completion_rejects_drafts_and_requires_consent(self):
        endpoint = reverse("complete_role_application_profile", args=[self.application.pk])
        response = self.client.post(endpoint, {
            "action": "draft",
            "details": '{"gender":"female","child_name":"Child Test"}',
        })
        self.assertEqual(response.status_code, 400)
        self.application.refresh_from_db()
        self.assertEqual(self.application.applicant_added_details, {})
        self.assertFalse(self.application.applicant_details_consent)

        response = self.client.post(endpoint, {
            "action": "submit",
            "details": '{"gender":"female"}',
        })
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Consent is required", status_code=400)

    def test_happy_nanays_application_can_submit_private_documents_with_consent(self):
        self.application.track = "happy_nanas"
        self.application.supporting_information = ""
        self.application.save(update_fields=["track", "supporting_information"])
        details = {
            "gender": "female",
            "birthdate": "1995-06-12",
            "barangay": "Alima",
            "street_address": "42 Palm Street",
            "household_size": 4,
            "monthly_income_range": "10000_14999",
        }
        response = self.client.post(
            reverse("complete_role_application_profile", args=[self.application.pk]),
            {
                "action": "submit",
                "consent": "on",
                "details": json.dumps(details),
                "document_types": ["valid_id_photo", "proof_of_residency"],
                "documents": [
                    SimpleUploadedFile("valid-id.pdf", b"%PDF-1.4\nID", content_type="application/pdf"),
                    SimpleUploadedFile("residency.pdf", b"%PDF-1.4\nProof", content_type="application/pdf"),
                ],
            },
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.application.refresh_from_db()
        self.assertTrue(self.application.applicant_details_consent)
        self.assertEqual(self.application.documents.count(), 2)
        document = self.application.documents.get(document_type="valid_id_photo")
        self.assertFalse(Path(document.file.path).is_relative_to(Path(settings.MEDIA_ROOT)))
        document_url = reverse("view_role_application_document", args=[document.pk])
        self.assertEqual(self.client.get(document_url).status_code, 403)

        administrator = User.objects.create_superuser(username="tracker-admin", email="admin@example.com", password="test-password")
        self.client.force_login(administrator)
        admin_response = self.client.get(document_url)
        self.assertEqual(admin_response.status_code, 200)
        self.assertEqual(admin_response["Content-Type"], "application/pdf")

    def test_completion_schema_only_includes_requested_fields_and_documents(self):
        applications = [
            (RoleApplication.ROLE_VOLUNTEER, "intern", {"school", "course"}, {"valid_id_photo", "endorsement_letter"}),
            (RoleApplication.ROLE_VOLUNTEER, "community_volunteer", {"skills_availability", "emergency_contact_name", "emergency_contact_phone"}, {"valid_id_photo"}),
            (RoleApplication.ROLE_BENEFICIARY, "happy_nanas", {"household_size", "monthly_income_range"}, {"valid_id_photo", "proof_of_residency"}),
            (RoleApplication.ROLE_BENEFICIARY, "happy_kids", {"child_birthdate", "school", "grade_level"}, {"valid_id_photo", "birth_certificate"}),
            (RoleApplication.ROLE_BENEFICIARY, "happy_hearts", {"disability_type"}, {"valid_id_photo", "pwd_id"}),
        ]
        for role, track, expected_fields, expected_documents in applications:
            application = RoleApplication.objects.create(
                user=self.user,
                role=role,
                track=track,
                full_name="Subtype Test",
                contact_details="09170000000",
            )
            payload = _serialize_user_role_application(application, UserProfile.objects.get(user=self.user))
            fields = {field["name"] for field in payload["completionFields"]}
            documents = {document["key"] for document in payload["completionDocuments"]}
            self.assertEqual(fields, {"gender", "birthdate", "barangay", "street_address"} | expected_fields, track)
            self.assertEqual(documents, expected_documents, track)
            self.assertEqual(len(payload["completionSections"]), 2)
            if track == "happy_nanas":
                self.assertEqual(payload["trackLabel"], "Happy Nanays (Parents)")

    def test_each_application_type_accepts_its_required_details_and_documents(self):
        application_types = [
            (RoleApplication.ROLE_VOLUNTEER, "intern"),
            (RoleApplication.ROLE_VOLUNTEER, "community_volunteer"),
            (RoleApplication.ROLE_BENEFICIARY, "happy_nanas"),
            (RoleApplication.ROLE_BENEFICIARY, "happy_kids"),
            (RoleApplication.ROLE_BENEFICIARY, "happy_hearts"),
        ]
        for index, (role, track) in enumerate(application_types):
            application = RoleApplication.objects.create(
                user=self.user,
                role=role,
                track=track,
                full_name="Subtype Test",
                contact_details="09170000000 / tracker@example.com",
            )
            payload = _serialize_user_role_application(application, UserProfile.objects.get(user=self.user))
            details = {}
            for field in payload["completionFields"]:
                if field["type"] == "select":
                    details[field["name"]] = field["options"][0]["value"]
                elif field["type"] == "date":
                    details[field["name"]] = "2000-01-01"
                elif field["type"] == "number":
                    details[field["name"]] = field.get("min", 1)
                else:
                    details[field["name"]] = "Test response"
            image_buffer = BytesIO()
            Image.new("RGB", (4, 4), color="green").save(image_buffer, format="PNG")
            documents = payload["completionDocuments"]
            response = self.client.post(
                reverse("complete_role_application_profile", args=[application.pk]),
                {
                    "action": "submit",
                    "consent": "on",
                    "details": json.dumps(details),
                    "document_types": [document["key"] for document in documents],
                    "documents": [
                        SimpleUploadedFile(
                            f"{document['key']}-{index}.png",
                            image_buffer.getvalue(),
                            content_type="image/png",
                        ) for document in documents
                    ],
                },
            )
            self.assertEqual(response.status_code, 200, f"{track}: {response.content!r}")
            application.refresh_from_db()
            self.assertTrue(application.applicant_details_consent, track)
            self.assertEqual(application.documents.count(), len(documents), track)

    def test_profile_values_are_not_asked_again(self):
        profile = UserProfile.objects.get(user=self.user)
        profile.gender = "female"
        profile.birthdate = date(1995, 6, 12)
        profile.phone = "09170000000"
        profile.barangay = "Alima"
        profile.address_line = "42 Palm Street"
        profile.save(update_fields=["gender", "birthdate", "phone", "barangay", "address_line"])

        _, context = self.render_homepage_view()
        fields = context["application_tracker_items"][0]["completionFields"]

        self.assertNotIn("gender", [field["name"] for field in fields])
        self.assertNotIn("birthdate", [field["name"] for field in fields])
        self.assertNotIn("phone", [field["name"] for field in fields])
        self.assertNotIn("barangay", [field["name"] for field in fields])
        self.assertNotIn("street_address", [field["name"] for field in fields])

    def test_completed_application_cannot_be_changed(self):
        self.application.status = RoleApplication.STATUS_APPROVED
        self.application.save(update_fields=["status"])

        response = self.client.post(
            reverse("complete_role_application_profile", args=[self.application.pk]),
            {"consent": "on", "household_size": "4"},
        )

        self.assertEqual(response.status_code, 409)

    def test_admin_application_payload_includes_applicant_added_details(self):
        self.application.applicant_added_details = {"household_size": 4}
        self.application.applicant_details_consent = True
        self.application.save(update_fields=["applicant_added_details", "applicant_details_consent"])

        beneficiary_payload = _serialize_pending_beneficiary_application(self.application)
        volunteer_application = RoleApplication.objects.create(
            user=self.user,
            role=RoleApplication.ROLE_VOLUNTEER,
            track="intern",
            full_name="Tracker User",
            contact_details="09170000000",
            applicant_added_details={"education_level": "college"},
            applicant_details_consent=True,
        )
        volunteer_payload = _serialize_pending_volunteer_application(volunteer_application)

        self.assertEqual(beneficiary_payload["applicantAddedDetails"], {"household_size": 4})
        self.assertEqual(volunteer_payload["applicantAddedDetails"], {"education_level": "college"})
        self.assertTrue(beneficiary_payload["detailsConsentGiven"])
        self.assertTrue(volunteer_payload["detailsConsentGiven"])