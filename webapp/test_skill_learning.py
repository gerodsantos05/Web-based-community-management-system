from io import BytesIO
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.http import QueryDict
from django.template.loader import get_template
from django.utils import timezone
from PIL import Image

from . import views
from .forms import SkillLearningMaterialForm, SkillLearningTopicForm
from .models import (
    RoleApplication,
    SkillLearningMaterial,
    SkillLearningMaterialEngagement,
    SkillLearningProgressAudit,
    SkillLearningTopic,
    SkillLearningTopicEngagement,
    UserProfile,
)


class SkillLearningMaterialUploadTests(TestCase):
    def test_beneficiary_template_renders_undo_confirmation_modal(self):
        html = get_template("user_dashboard/skill_learning_user.html").render({})

        self.assertIn('id="sl-undo-confirm-modal"', html)
        self.assertIn('id="sl-undo-confirm-btn"', html)

    def setUp(self):
        self.media_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.media_directory.cleanup)
        self.media_override = override_settings(MEDIA_ROOT=self.media_directory.name)
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)

        self.user = User.objects.create_user(
            username="learning-volunteer",
            password="test-password",
        )
        self.client.force_login(self.user)
        self.topic = SkillLearningTopic.objects.create(
            title="Reading practice",
            description="Practice reading.",
            badge_label="Literacy",
            filter_tags=["Children"],
            cover_image_url="https://example.test/cover.jpg",
        )

    @patch("webapp.views._has_dashboard_access", return_value=True)
    @patch("webapp.views._is_active_volunteer", return_value=True)
    def test_uploaded_pdf_is_saved_and_returned_as_previewable_material(
        self,
        _is_volunteer,
        _has_dashboard_access,
    ):
        upload = SimpleUploadedFile(
            "practice-guide.pdf",
            b"%PDF-1.4\nsample PDF content\n",
            content_type="application/pdf",
        )

        response = self.client.post(
            reverse("skill_learning_material_create", args=[self.topic.id]),
            {
                "material_type": "document",
                "title": "Practice guide",
                "description": "A PDF learning guide.",
                "file_upload": upload,
                "external_url": "https://example.test/alternate-guide.pdf",
            },
        )

        self.assertEqual(response.status_code, 200, response.content)
        material = SkillLearningMaterial.objects.get(topic=self.topic)
        payload_material = response.json()["topic"]["materials"][0]
        self.assertTrue(material.file_upload)
        self.assertEqual(material.external_url, "")
        self.assertEqual(payload_material["mimeType"], "application/pdf")
        self.assertEqual(
            payload_material["sourceUrl"],
            reverse("skill_learning_material_file", args=[material.id]),
        )
        saved_file_path = Path(self.media_directory.name) / material.file_upload.name
        self.assertTrue(saved_file_path.is_file())
        self.assertEqual(saved_file_path.read_bytes(), b"%PDF-1.4\nsample PDF content\n")
        file_response = self.client.get(payload_material["sourceUrl"])
        self.addCleanup(file_response.close)
        self.assertEqual(file_response.status_code, 200)
        self.assertEqual(file_response["Content-Type"], "application/pdf")
        self.assertIn("inline", file_response["Content-Disposition"])
        self.assertEqual(file_response["X-Frame-Options"], "SAMEORIGIN")
        self.assertEqual(
            b"".join(file_response.streaming_content),
            b"%PDF-1.4\nsample PDF content\n",
        )

    @patch("webapp.views._is_active_volunteer", return_value=True)
    def test_uploaded_pdf_can_be_replaced_by_an_external_link(self, _is_volunteer):
        material = SkillLearningMaterial.objects.create(
            topic=self.topic,
            material_type="document",
            title="Old guide",
            file_upload=SimpleUploadedFile("old-guide.pdf", b"%PDF-1.4\nold\n"),
        )
        old_file_path = Path(self.media_directory.name) / material.file_upload.name
        self.assertTrue(old_file_path.is_file())

        response = self.client.post(
            reverse("skill_learning_material_update", args=[material.id]),
            {
                "material_type": "document",
                "title": "Updated guide",
                "description": "",
                "external_url": "https://example.test/new-guide.pdf",
            },
        )

        self.assertEqual(response.status_code, 200, response.content)
        material.refresh_from_db()
        self.assertFalse(material.file_upload)
        self.assertEqual(material.external_url, "https://example.test/new-guide.pdf")
        self.assertFalse(old_file_path.exists())

    @patch("webapp.views._is_active_volunteer", return_value=True)
    def test_replacing_an_uploaded_pdf_removes_the_previous_file(self, _is_volunteer):
        material = SkillLearningMaterial.objects.create(
            topic=self.topic,
            material_type="document",
            title="Old guide",
            file_upload=SimpleUploadedFile("old-guide.pdf", b"%PDF-1.4\nold\n"),
        )
        old_file_path = Path(self.media_directory.name) / material.file_upload.name

        response = self.client.post(
            reverse("skill_learning_material_update", args=[material.id]),
            {
                "material_type": "document",
                "title": "New guide",
                "description": "",
                "file_upload": SimpleUploadedFile("new-guide.pdf", b"%PDF-1.4\nnew\n"),
                "external_url": "",
            },
        )

        self.assertEqual(response.status_code, 200, response.content)
        material.refresh_from_db()
        self.assertEqual(material.title, "New guide")
        self.assertTrue(material.file_upload.name.endswith(".pdf"))
        self.assertFalse(old_file_path.exists())

    @patch("webapp.views._has_dashboard_access", return_value=True)
    def test_opening_topic_records_topic_engagement(self, _has_dashboard_access):
        response = self.client.post(
            reverse("skill_learning_topic_open", args=[self.topic.id]),
        )

        self.assertEqual(response.status_code, 200, response.content)
        engagement = SkillLearningTopicEngagement.objects.get(
            user=self.user,
            topic=self.topic,
        )
        self.assertEqual(engagement.page_open_count, 1)
        self.assertIsNotNone(engagement.last_accessed_at)

    @patch("webapp.views._has_dashboard_access", return_value=True)
    def test_material_completion_updates_and_resets_topic_progress(self, _has_dashboard_access):
        material = SkillLearningMaterial.objects.create(
            topic=self.topic,
            title="Completion guide",
            material_type="document",
        )
        complete_response = self.client.post(
            reverse("skill_learning_material_engagement", args=[material.id]),
            {"action": "complete"},
        )

        self.assertEqual(complete_response.status_code, 200, complete_response.content)
        self.assertTrue(complete_response.json()["completed"])
        engagement = SkillLearningMaterialEngagement.objects.get(
            user=self.user,
            material=material,
        )
        self.assertIsNotNone(engagement.completed_at)

        payload_response = self.client.get(reverse("skill_learning_data_api"))
        self.assertEqual(payload_response.status_code, 200, payload_response.content)
        topic_payload = next(
            topic for topic in payload_response.json()["topics"]
            if topic["id"] == str(self.topic.id)
        )
        self.assertEqual(topic_payload["completedMaterials"], 1)
        self.assertEqual(topic_payload["totalMaterials"], 1)
        self.assertEqual(topic_payload["progressPercent"], 100)
        self.assertTrue(topic_payload["materials"][0]["completed"])

        uncomplete_response = self.client.post(
            reverse("skill_learning_material_engagement", args=[material.id]),
            {"action": "uncomplete"},
        )
        self.assertEqual(uncomplete_response.status_code, 200, uncomplete_response.content)
        self.assertFalse(uncomplete_response.json()["completed"])

        refreshed_payload = self.client.get(reverse("skill_learning_data_api")).json()
        refreshed_topic = next(
            topic for topic in refreshed_payload["topics"]
            if topic["id"] == str(self.topic.id)
        )
        self.assertEqual(refreshed_topic["completedMaterials"], 0)
        self.assertEqual(refreshed_topic["progressPercent"], 0)

    @patch("webapp.views._is_active_volunteer", return_value=True)
    def test_volunteer_progress_page_shows_beneficiary_topic_and_material_status(self, _is_volunteer):
        beneficiary = User.objects.create_user(
            username="progress-beneficiary",
            first_name="Progress",
            last_name="Beneficiary",
            password="test-password",
        )
        UserProfile.objects.create(user=beneficiary, account_role=UserProfile.ROLE_BENEFICIARY)
        RoleApplication.objects.create(
            user=beneficiary,
            role=RoleApplication.ROLE_BENEFICIARY,
            status=RoleApplication.STATUS_APPROVED,
            full_name="Progress Beneficiary",
            contact_details="progress@example.test",
        )
        material = SkillLearningMaterial.objects.create(
            topic=self.topic,
            material_type="document",
            title="Progress worksheet",
        )
        SkillLearningMaterialEngagement.objects.create(
            user=beneficiary,
            material=material,
            completed_at=timezone.now(),
        )
        SkillLearningTopic.objects.create(
            title="Gardening practice",
            description="Practice gardening.",
            badge_label="Outdoors",
        )

        response = self.client.get(reverse("volunteer_skill_learning_progress"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Progress Beneficiary")
        self.assertContains(response, "Reading practice")
        self.assertContains(response, "Progress worksheet")
        self.assertContains(response, 'data-completed-count="1"')
        self.assertContains(response, 'data-total-count="1"')
        self.assertEqual(response.content.count(b'data-beneficiary-name="Progress Beneficiary"'), 1)
        self.assertContains(response, "Confirmation")
        self.assertContains(response, 'id="lp-dialog-close"')
        self.assertContains(response, '<button id="lp-cancel" type="button">Cancel</button>')
        self.assertContains(response, '<button id="lp-confirm" type="button">Save</button>')

    @patch("webapp.views._is_active_volunteer", return_value=True)
    def test_volunteer_progress_edits_are_audited(self, _is_volunteer):
        beneficiary = User.objects.create_user(
            username="editable-beneficiary",
            first_name="Editable",
            last_name="Beneficiary",
            password="test-password",
        )
        UserProfile.objects.create(user=beneficiary, account_role=UserProfile.ROLE_BENEFICIARY)
        RoleApplication.objects.create(
            user=beneficiary,
            role=RoleApplication.ROLE_BENEFICIARY,
            status=RoleApplication.STATUS_APPROVED,
            full_name="Editable Beneficiary",
            contact_details="editable@example.test",
        )
        material = SkillLearningMaterial.objects.create(
            topic=self.topic,
            material_type="document",
            title="Editable worksheet",
        )

        complete_response = self.client.post(
            reverse("volunteer_skill_learning_progress_update"),
            {
                "beneficiary_id": beneficiary.id,
                "material_id": material.id,
                "action": "complete",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(complete_response.status_code, 200, complete_response.content)
        self.assertEqual(complete_response.json(), {"ok": True, "completed": True})
        engagement = SkillLearningMaterialEngagement.objects.get(user=beneficiary, material=material)
        self.assertIsNotNone(engagement.completed_at)

        undo_response = self.client.post(
            reverse("volunteer_skill_learning_progress_update"),
            {
                "beneficiary_id": beneficiary.id,
                "material_id": material.id,
                "action": "uncomplete",
            },
        )
        self.assertRedirects(undo_response, reverse("volunteer_skill_learning_progress"))
        engagement.refresh_from_db()
        self.assertIsNone(engagement.completed_at)
        self.assertEqual(
            SkillLearningProgressAudit.objects.filter(
                beneficiary=beneficiary,
                material=material,
                changed_by=self.user,
            ).count(),
            2,
        )

    @patch("webapp.views._is_active_volunteer", return_value=True)
    def test_volunteer_bulk_progress_updates_are_atomic_and_audited(self, _is_volunteer):
        beneficiary = User.objects.create_user(
            username="bulk-progress-beneficiary",
            first_name="Bulk",
            last_name="Beneficiary",
            password="test-password",
        )
        UserProfile.objects.create(user=beneficiary, account_role=UserProfile.ROLE_BENEFICIARY)
        RoleApplication.objects.create(
            user=beneficiary,
            role=RoleApplication.ROLE_BENEFICIARY,
            status=RoleApplication.STATUS_APPROVED,
            full_name="Bulk Beneficiary",
            contact_details="bulk@example.test",
        )
        materials = [
            SkillLearningMaterial.objects.create(
                topic=self.topic,
                material_type="document",
                title="Bulk worksheet " + str(index),
            )
            for index in range(3)
        ]
        url = reverse("volunteer_skill_learning_progress_bulk_update")
        payload = {
            "beneficiary_id": beneficiary.id,
            "topic_id": self.topic.id,
            "action": "complete",
        }

        complete_response = self.client.post(url, payload)

        self.assertEqual(complete_response.status_code, 200, complete_response.content)
        self.assertEqual(complete_response.json(), {
            "ok": True,
            "completed": True,
            "updated": 3,
            "total": 3,
        })
        self.assertTrue(all(
            SkillLearningMaterialEngagement.objects.get(
                user=beneficiary,
                material=material,
            ).completed_at
            for material in materials
        ))

        payload["action"] = "uncomplete"
        reset_response = self.client.post(url, payload)

        self.assertEqual(reset_response.status_code, 200, reset_response.content)
        self.assertEqual(reset_response.json()["updated"], 3)
        self.assertTrue(all(
            SkillLearningMaterialEngagement.objects.get(
                user=beneficiary,
                material=material,
            ).completed_at is None
            for material in materials
        ))
        self.assertEqual(
            SkillLearningProgressAudit.objects.filter(
                beneficiary=beneficiary,
                material__in=materials,
                changed_by=self.user,
            ).count(),
            6,
        )

    @patch("webapp.views._is_active_volunteer", return_value=True)
    def test_single_material_updates_use_bulk_endpoint_without_changing_neighbor_materials(
        self,
        _is_volunteer,
    ):
        beneficiary = User.objects.create_user(
            username="single-toggle-beneficiary",
            first_name="Single",
            last_name="Toggle",
            password="test-password",
        )
        UserProfile.objects.create(user=beneficiary, account_role=UserProfile.ROLE_BENEFICIARY)
        RoleApplication.objects.create(
            user=beneficiary,
            role=RoleApplication.ROLE_BENEFICIARY,
            status=RoleApplication.STATUS_APPROVED,
            full_name="Single Toggle",
            contact_details="single-toggle@example.test",
        )
        materials = [
            SkillLearningMaterial.objects.create(
                topic=self.topic,
                material_type="document",
                title="Toggle material " + str(index),
            )
            for index in range(3)
        ]
        url = reverse("volunteer_skill_learning_progress_bulk_update")
        payload = {
            "beneficiary_id": beneficiary.id,
            "material_id": materials[0].id,
            "action": "complete",
        }

        first_complete = self.client.post(url, payload, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(first_complete.status_code, 200, first_complete.content)
        self.assertEqual(first_complete.json(), {
            "ok": True,
            "completed": True,
            "updated": 1,
            "total": 1,
        })

        payload["material_id"] = materials[1].id
        second_complete = self.client.post(url, payload, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(second_complete.status_code, 200, second_complete.content)
        self.assertTrue(second_complete.json()["completed"])

        payload["material_id"] = materials[0].id
        payload["action"] = "uncomplete"
        first_reset = self.client.post(url, payload, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(first_reset.status_code, 200, first_reset.content)
        self.assertFalse(first_reset.json()["completed"])

        self.assertIsNone(SkillLearningMaterialEngagement.objects.get(
            user=beneficiary,
            material=materials[0],
        ).completed_at)
        self.assertIsNotNone(SkillLearningMaterialEngagement.objects.get(
            user=beneficiary,
            material=materials[1],
        ).completed_at)
        self.assertFalse(SkillLearningMaterialEngagement.objects.filter(
            user=beneficiary,
            material=materials[2],
        ).exists())

        topic_complete = self.client.post(url, {
            "beneficiary_id": beneficiary.id,
            "topic_id": self.topic.id,
            "action": "complete",
        }, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(topic_complete.status_code, 200, topic_complete.content)
        payload["material_id"] = materials[1].id
        payload["action"] = "uncomplete"
        second_reset = self.client.post(url, payload, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(second_reset.status_code, 200, second_reset.content)

        for material, expected_completed in zip(materials, (True, False, True)):
            self.assertEqual(
                bool(SkillLearningMaterialEngagement.objects.get(
                    user=beneficiary,
                    material=material,
                ).completed_at),
                expected_completed,
            )

        progress_page = self.client.get(
            reverse("volunteer_skill_learning_progress"),
            {"beneficiary": beneficiary.id},
        )
        self.assertEqual(progress_page.status_code, 200, progress_page.content)
        for material, expected in zip(materials, ("true", "false", "true")):
            self.assertContains(
                progress_page,
                'data-material-id="{}"'.format(material.id),
            )
            self.assertRegex(
                progress_page.content.decode(),
                r'data-material-id="{}"[^>]*data-completed="{}"'.format(material.id, expected),
            )

    @patch("webapp.views._is_active_volunteer", return_value=False)
    def test_progress_edits_are_forbidden_for_non_volunteers(self, _is_volunteer):
        response = self.client.post(
            reverse("volunteer_skill_learning_progress_update"),
            {"beneficiary_id": 1, "material_id": "invalid", "action": "complete"},
        )

        self.assertEqual(response.status_code, 403)


class SkillLearningTopicFormTests(TestCase):
    def setUp(self):
        self.media_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.media_directory.cleanup)
        self.media_override = override_settings(MEDIA_ROOT=self.media_directory.name)
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)

    def test_topic_form_accepts_multiple_filter_tags(self):
        response_data = QueryDict(
            "title=Reading+practice"
            "&description=Practice+reading."
            "&badge_label=Literacy"
            "&cover_image_url=https%3A%2F%2Fexample.test%2Fcover.jpg"
            "&filter_tags=Community"
            "&filter_tags=Popular"
        )

        form = SkillLearningTopicForm(data=response_data)

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["filter_tags"], ["Community", "Popular"])

    @patch("webapp.views._is_active_volunteer", return_value=True)
    def test_topic_create_accepts_uploaded_cover_and_multiple_tags(self, _is_volunteer):
        user = User.objects.create_user(username="topic-creator", password="test-password")
        self.client.force_login(user)
        image_buffer = BytesIO()
        Image.new("RGB", (2, 2), color="green").save(image_buffer, format="PNG")
        image_upload = SimpleUploadedFile(
            "cover.png",
            image_buffer.getvalue(),
            content_type="image/png",
        )

        response = self.client.post(
            reverse("skill_learning_topic_create"),
            {
                "title": "Reading practice",
                "description": "Practice reading.",
                "badge_label": "Literacy",
                "cover_image": image_upload,
                "cover_image_url": "",
                "filter_tags": ["Community", "Popular"],
            },
        )

        self.assertEqual(response.status_code, 201, response.content)
        topic = SkillLearningTopic.objects.get(title="Reading practice")
        self.assertTrue(topic.cover_image)
        self.assertEqual(topic.filter_tags, ["Community", "Popular"])


class SkillLearningMaterialFormTests(TestCase):
    def test_material_form_preserves_original_http_url(self):
        original_url = "https://drive.google.com/file/d/abc123/view?usp=sharing"
        form = SkillLearningMaterialForm(data={
            "material_type": "document",
            "title": "Shared guide",
            "description": "",
            "external_url": original_url,
        })

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["external_url"], original_url)

    def test_material_form_rejects_non_http_url(self):
        form = SkillLearningMaterialForm(data={
            "material_type": "document",
            "title": "Unsafe link",
            "description": "",
            "external_url": "javascript:alert(1)",
        })

        self.assertFalse(form.is_valid())
        self.assertIn("external_url", form.errors)

    def test_material_form_requires_a_file_or_link(self):
        form = SkillLearningMaterialForm(data={
            "material_type": "document",
            "title": "Empty material",
            "description": "",
            "external_url": "",
        })

        self.assertFalse(form.is_valid())


class SkillLearningDefaultSeedTests(TestCase):
    def test_default_content_can_be_seeded_after_all_topics_are_removed(self):
        views._ensure_skill_learning_content()
        first_seed_material_count = SkillLearningMaterial.objects.count()
        self.assertGreater(first_seed_material_count, 0)

        SkillLearningTopic.objects.all().delete()
        views._ensure_skill_learning_content()

        self.assertGreater(SkillLearningTopic.objects.count(), 0)
        self.assertEqual(SkillLearningMaterial.objects.count(), first_seed_material_count)
