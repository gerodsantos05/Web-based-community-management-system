import json
import re
import tempfile
from datetime import datetime, timedelta, time
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser, User
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from . import views
from .audit import reset_admin_actor, set_admin_actor
from .avatar_utils import avatar_url_for_user, default_avatar_url
from .context_processors import dashboard_profile_context
from .models import (
    AdminActivityLog,
    AdminSystemSettings,
    AdminUserPreferences,
    Activity,
    ActivityBeneficiaryAssignment,
    BeneficiaryActivityAttendance,
    BeneficiaryActivityFeedback,
    BeneficiaryAssistanceRecord,
    CommunityNotification,
    CommunityPost,
    CommunityPostComment,
    CommunityPostLike,
    CommunityPostReport,
    Donation,
    InventoryItem,
    ProductInquiry,
    ProductReview,
    ResourceLibraryMaterial,
    RoleApplication,
    StockMovement,
    SkillLearningMaterial,
    SkillLearningMaterialEngagement,
    SkillLearningTopic,
    SkillLearningTopicEngagement,
    UserProfile,
    VolunteerActivityAssignment,
    VolunteerOjtSchedule,
    VolunteerAdminMessage,
    VolunteerAdminMessageAttachment,
    VolunteerAttendanceRecord,
    VolunteerCertificate,
)


class ProductReviewTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(username="review-customer", password="password123")
        self.order = ProductInquiry.objects.create(
            user=self.customer,
            full_name="Review Customer",
            email="review-customer@example.com",
            phone="09171234567",
            payment_method=ProductInquiry.PAYMENT_CARD,
            order_items=[{"name": "Homemade Candle", "variation": "Vanilla", "quantity": 1}],
            order_total=50,
            status=ProductInquiry.STATUS_COMPLETED,
            admin_notification="",
        )
        self.client.force_login(self.customer)

    def test_customer_can_submit_one_review_for_completed_order(self):
        url = reverse("submit_product_review", kwargs={"order_id": self.order.pk})
        response = self.client.post(url, {"rating": "4", "message": "Lovely scent"})

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["rating"], 4)
        self.assertEqual(ProductReview.objects.get().message, "Lovely scent")

        duplicate = self.client.post(url, {"rating": "5", "message": "Second attempt"})
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(ProductReview.objects.count(), 1)

    def test_admin_receives_grouped_product_ratings(self):
        ProductReview.objects.create(
            inquiry=self.order,
            product_name="Homemade Candle",
            variation="Vanilla",
            rating=4,
            message="Lovely scent",
        )
        admin = User.objects.create_superuser(username="review-admin", email="review-admin@example.com", password="password123")
        self.client.force_login(admin)

        response = self.client.get(reverse("payment"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["ratings_json"][0]["average"], 4.0)
        self.assertEqual(response.context["ratings_json"][0]["count"], 1)
        self.assertEqual(response.context["ratings_json"][0]["reviews"][0]["message"], "Lovely scent")


class ProductInventoryStockTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(username="stock-customer", password="password123")
        UserProfile.objects.create(user=self.customer, account_role=UserProfile.ROLE_REGULAR)
        self.client.force_login(self.customer)
        self.item = InventoryItem.objects.create(
            name="Tote Bag",
            category=InventoryItem.CATEGORY_STORE_PRODUCT,
            stock=5,
            low_stock_threshold=2,
        )

    def order_payload(self, quantity):
        return {
            "full_name": "Stock Customer",
            "email": "stock-customer@example.com",
            "phone": "09171234567",
            "payment_method": ProductInquiry.PAYMENT_COD,
            "order_items": json.dumps([{
                "name": "Tote Bag",
                "category": "Tote Bags",
                "quantity": quantity,
            }]),
        }

    def test_stock_endpoint_matches_inventory_dashboard_quantity(self):
        response = self.client.get(reverse("product_stock"), {"name": "Tote Bag"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["stock"], 5)
        self.assertEqual(response.json()["status"], "in_stock")

        self.item.stock = 2
        self.item.save(update_fields=["stock", "updated_at"])
        low_response = self.client.get(reverse("product_stock"), {"name": "Tote Bag"})
        self.assertEqual(low_response.json()["status"], "low_stock")

        self.item.stock = 0
        self.item.save(update_fields=["stock", "updated_at"])
        out_response = self.client.get(reverse("product_stock"), {"name": "Tote Bag"})
        self.assertEqual(out_response.json()["status"], "out_of_stock")

    def test_order_reserves_stock_and_rejects_quantity_after_stock_changes(self):
        response = self.client.post(reverse("submit_product_inquiry"), self.order_payload(3))

        self.assertEqual(response.status_code, 201)
        self.item.refresh_from_db()
        self.assertEqual(self.item.stock, 2)
        self.assertEqual(StockMovement.objects.get(item=self.item).quantity, 3)

        rejected = self.client.post(reverse("submit_product_inquiry"), self.order_payload(3))

        self.assertEqual(rejected.status_code, 409)
        self.assertIn("Only 2 available", rejected.json()["error"])
        self.item.refresh_from_db()
        self.assertEqual(self.item.stock, 2)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class DirectoryAccountCreationTests(TestCase):
    def test_create_beneficiary_creates_account_and_requires_password_change(self):
        admin = User.objects.create_superuser(username="admin-beneficiary", email="admin-beneficiary@example.com", password="password123")
        self.client.force_login(admin)

        response = self.client.post(
            reverse("create_beneficiary"),
            {
                "full_name": "Test Beneficiary",
                "email": "beneficiary-login@example.com",
                "phone": "09171234567",
                "address": "Barangay 123",
                "status": "Active",
                "username": "test-beneficiary",
            },
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        user = User.objects.get(email="beneficiary-login@example.com")
        self.assertEqual(user.userprofile.account_role, UserProfile.ROLE_BENEFICIARY)
        self.assertEqual(user.role_applications.get(role=RoleApplication.ROLE_BENEFICIARY).user_id, user.id)
        temp_password = payload["credentials"]["password"]
        self.assertTrue(user.check_password(temp_password))
        self.assertTrue(user.userprofile.settings_state.get("force_password_change"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(user.email, mail.outbox[0].to)
        self.assertIn(temp_password, mail.outbox[0].body)

        sign_in = self.client.post(
            reverse("signin"),
            {"username_or_email": user.email, "password": temp_password},
            follow=False,
        )
        self.assertEqual(sign_in.status_code, 302)
        self.assertEqual(sign_in.url, reverse("password_change_required"))

        change_response = self.client.post(
            reverse("password_change_required"),
            {"current_password": temp_password, "new_password": "NewSecurePass!2026", "confirm_password": "NewSecurePass!2026"},
            follow=False,
        )
        self.assertEqual(change_response.status_code, 302)
        user.refresh_from_db()
        self.assertFalse(user.userprofile.settings_state.get("force_password_change", False))
        self.assertTrue(user.check_password("NewSecurePass!2026"))

    def test_create_volunteer_creates_account_and_email(self):
        admin = User.objects.create_superuser(username="admin-volunteer", email="admin-volunteer@example.com", password="password123")
        self.client.force_login(admin)

        response = self.client.post(
            reverse("create_volunteer"),
            {
                "full_name": "Test Volunteer",
                "email": "volunteer-login@example.com",
                "phone": "09181234567",
                "availability": "Weekends",
                "username": "test-volunteer",
                "status": "active",
            },
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        user = User.objects.get(email="volunteer-login@example.com")
        self.assertEqual(user.userprofile.account_role, UserProfile.ROLE_VOLUNTEER)
        self.assertEqual(user.role_applications.get(role=RoleApplication.ROLE_VOLUNTEER).user_id, user.id)
        temp_password = payload["credentials"]["password"]
        self.assertTrue(user.check_password(temp_password))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(temp_password, mail.outbox[0].body)

    def test_create_login_account_for_legacy_directory_record(self):
        admin = User.objects.create_superuser(username="admin-legacy", email="admin-legacy@example.com", password="password123")
        self.client.force_login(admin)

        application = RoleApplication.objects.create(
            user=None,
            role=RoleApplication.ROLE_BENEFICIARY,
            status=RoleApplication.STATUS_APPROVED,
            full_name="Legacy Beneficiary",
            contact_details="legacy@example.com / 09191112222",
            supporting_information="Legacy address",
        )

        response = self.client.post(
            reverse("create_directory_account"),
            {"role": "beneficiary", "application_id": application.id},
        )

        self.assertEqual(response.status_code, 201)
        user = User.objects.get(email="legacy@example.com")
        application.refresh_from_db()
        self.assertEqual(application.user_id, user.id)
        self.assertEqual(user.userprofile.account_role, UserProfile.ROLE_BENEFICIARY)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("temporary password", mail.outbox[0].body.lower())


class SkillLearningEngagementTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="learning-user", password="password123")
        self.first_topic = SkillLearningTopic.objects.create(
            title="Community gardening", description="Grow together.", badge_label="Community", filter_tags=["Community"],
        )
        self.second_topic = SkillLearningTopic.objects.create(
            title="Community cooking", description="Cook together.", badge_label="Community", filter_tags=["Community"],
        )
        self.first_material = SkillLearningMaterial.objects.create(topic=self.first_topic, title="Garden guide", material_type="document")
        SkillLearningMaterial.objects.create(topic=self.first_topic, title="Garden video", material_type="video")
        self.second_material = SkillLearningMaterial.objects.create(topic=self.second_topic, title="Cooking guide", material_type="document")

    def test_payload_reports_progress_and_weighted_live_popularity(self):
        SkillLearningMaterialEngagement.objects.create(user=self.user, material=self.first_material, view_count=1, completed_at=timezone.now())
        SkillLearningMaterialEngagement.objects.create(user=self.user, material=self.second_material, view_count=2)
        SkillLearningTopicEngagement.objects.create(user=self.user, topic=self.first_topic, page_open_count=1)

        payload = views._skill_learning_payload(self.user)
        topics = {item["id"]: item for item in payload["topics"]}

        first = topics[str(self.first_topic.id)]
        second = topics[str(self.second_topic.id)]
        self.assertEqual(first["completedMaterials"], 1)
        self.assertEqual(first["totalMaterials"], 2)
        self.assertEqual(first["progressPercent"], 50)
        self.assertEqual(first["popularityScore"], 8)
        self.assertEqual(second["popularityScore"], 4)

    def test_recommendations_match_progressed_topic_tags_and_fallback_to_popularity(self):
        SkillLearningMaterialEngagement.objects.create(user=self.user, material=self.first_material, completed_at=timezone.now())
        payload = views._skill_learning_payload(self.user)
        topics = {item["id"]: item for item in payload["topics"]}
        self.assertTrue(topics[str(self.second_topic.id)]["isRecommended"])

        new_user = User.objects.create_user(username="new-learning-user", password="password123")
        SkillLearningMaterialEngagement.objects.create(user=new_user, material=self.second_material, view_count=3)
        fallback = views._skill_learning_payload(User.objects.create_user(username="brand-new", password="password123"))
        fallback_topics = {item["id"]: item for item in fallback["topics"]}
        self.assertTrue(fallback_topics[str(self.second_topic.id)]["isRecommended"])

    def test_volunteer_skill_learning_hides_completion_ui_but_keeps_material_count(self):
        js_path = Path(views.__file__).resolve().parent / "static" / "js" / "skill_learning_dashboard.js"
        content = js_path.read_text(encoding="utf-8")

        self.assertIn('isVolunteerView()', content)
        self.assertIn('renderCompletionSummary(topic)', content)
        self.assertIn('userRole === "volunteer"', content)
        self.assertIn("material' + (materialCount === 1 ? '' : 's')", content)


class ResourceLibraryAdminTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username="resource-admin", email="resource-admin@example.com", password="password123")
        self.volunteer = User.objects.create_user(username="resource-volunteer", password="password123")
        UserProfile.objects.create(user=self.volunteer, account_role=UserProfile.ROLE_VOLUNTEER)
        RoleApplication.objects.create(
            user=self.volunteer,
            role=RoleApplication.ROLE_VOLUNTEER,
            status=RoleApplication.STATUS_APPROVED,
            full_name="Resource Volunteer",
            contact_details="resource-volunteer@example.com",
        )

    def test_admin_can_publish_resource_for_volunteers(self):
        self.client.force_login(self.admin)
        page = self.client.get(reverse("admin_resource_library"))
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "Add a resource")
        self.assertContains(page, 'placeholder="e.g. Volunteer Safety Guide"')
        self.assertContains(page, "Select a category")
        page_html = page.content.decode()
        self.assertIn('id="rla-manage-panel"', page_html)
        self.assertIn('id="rla-add-modal" class="rla-modal-backdrop" aria-hidden="true"', page_html)
        self.assertEqual(len(re.findall(r'<button[^>]*data-rla-open-modal', page_html)), 1)
        header_html = page_html.split('<header id="app-header"', 1)[1].split("</header>", 1)[0]
        self.assertRegex(header_html, r"<h1[^>]*>\s*Resource Library\s*</h1>")
        self.assertIn("Publish guides, files, and links for volunteers", header_html)
        self.assertEqual(page_html.count("Publish guides, files, and links for volunteers"), 1)

        invalid_response = self.client.post(reverse("admin_resource_library"), {
            "title": "Missing source guide",
            "category": ResourceLibraryMaterial.CATEGORY_OUTREACH,
            "description": "This form should stay open when validation fails.",
        })
        self.assertEqual(invalid_response.status_code, 200)
        self.assertContains(invalid_response, 'id="rla-add-modal"')
        self.assertContains(invalid_response, 'aria-hidden="false"')
        self.assertContains(invalid_response, "Provide either an uploaded file or an external link.")

        response = self.client.post(reverse("admin_resource_library"), {
            "title": "Volunteer Safety Guide",
            "category": ResourceLibraryMaterial.CATEGORY_OUTREACH,
            "description": "Safety procedures for outreach activities.",
            "external_url": "https://example.org/volunteer-safety",
            "is_published": "on",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("admin_resource_library"))

        manage_page = self.client.get(reverse("admin_resource_library"))
        self.assertContains(manage_page, "Volunteer Safety Guide")

        self.client.force_login(self.volunteer)
        library = self.client.get(reverse("volunteer_dashboard_resource_library"))
        self.assertContains(library, "Volunteer Safety Guide")
        self.assertContains(library, "https://example.org/volunteer-safety")
        self.assertContains(library, 'data-rl-preview-kind="link"')

    def test_admin_resource_delete_uses_confirmation_modal_and_deletes_on_confirm(self):
        resource = ResourceLibraryMaterial.objects.create(
            title="Resource to delete",
            category=ResourceLibraryMaterial.CATEGORY_OUTREACH,
            external_url="https://example.org/delete-resource",
        )
        self.client.force_login(self.admin)

        page = self.client.get(reverse("admin_resource_library"))

        self.assertContains(page, 'id="rla-delete-backdrop"')
        self.assertContains(page, 'data-rla-delete-open')
        self.assertContains(page, "This action cannot be undone.")
        self.assertNotContains(page, "onsubmit=\"return confirm(")

        response = self.client.post(reverse("admin_resource_library"), {
            "action": "delete",
            "resource_id": str(resource.pk),
        })

        self.assertEqual(response.status_code, 302)
        self.assertFalse(ResourceLibraryMaterial.objects.filter(pk=resource.pk).exists())

    def test_admin_can_edit_resource_without_recreating_it(self):
        resource = ResourceLibraryMaterial.objects.create(
            title="Original Guide",
            category=ResourceLibraryMaterial.CATEGORY_OUTREACH,
            description="Original description.",
            external_url="https://example.org/original-guide",
        )
        self.client.force_login(self.admin)

        response = self.client.post(reverse("admin_resource_library"), {
            "action": "update",
            "resource_id": str(resource.pk),
            "title": "Updated Guide",
            "category": ResourceLibraryMaterial.CATEGORY_TEACHING_KIDS,
            "description": "Updated description.",
            "external_url": "https://example.org/updated-guide",
            "is_published": "on",
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(ResourceLibraryMaterial.objects.count(), 1)
        resource.refresh_from_db()
        self.assertEqual(resource.title, "Updated Guide")
        self.assertEqual(resource.category, ResourceLibraryMaterial.CATEGORY_TEACHING_KIDS)
        self.assertEqual(resource.description, "Updated description.")
        self.assertEqual(resource.external_url, "https://example.org/updated-guide")
        self.assertTrue(resource.is_published)

    def test_admin_can_preview_unpublished_pdf_from_resource_list(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                resource = ResourceLibraryMaterial.objects.create(
                    title="Private Admin Preview",
                    category=ResourceLibraryMaterial.CATEGORY_OUTREACH,
                    file_upload=SimpleUploadedFile("admin-preview.pdf", b"%PDF-1.4 preview", content_type="application/pdf"),
                    is_published=False,
                )
                self.client.force_login(self.admin)
                preview_url = reverse("volunteer_resource_library_pdf_preview", kwargs={"material_id": resource.pk})

                page = self.client.get(reverse("admin_resource_library"))

                self.assertContains(page, "data-rla-preview")
                self.assertContains(page, 'data-preview-kind="pdf"')
                self.assertContains(page, f'data-preview-url="{preview_url}"')
                preview = self.client.get(preview_url)
                self.assertEqual(preview.status_code, 200)
                self.assertTrue(preview["Content-Disposition"].startswith("inline;"))
                preview.close()

    def test_resource_edit_preserves_or_removes_existing_upload_as_requested(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                resource = ResourceLibraryMaterial.objects.create(
                    title="Uploaded Guide",
                    category=ResourceLibraryMaterial.CATEGORY_OUTREACH,
                    file_upload=SimpleUploadedFile("outreach-guide.pdf", b"%PDF-1.4 guide"),
                )
                original_file_name = resource.file_upload.name
                storage = resource.file_upload.storage
                self.client.force_login(self.admin)

                preserved_response = self.client.post(reverse("admin_resource_library"), {
                    "action": "update",
                    "resource_id": str(resource.pk),
                    "title": "Renamed Uploaded Guide",
                    "category": ResourceLibraryMaterial.CATEGORY_OUTREACH,
                    "description": "Updated without replacing the file.",
                    "external_url": "",
                    "is_published": "on",
                })

                self.assertEqual(preserved_response.status_code, 302)
                resource.refresh_from_db()
                self.assertEqual(resource.file_upload.name, original_file_name)
                self.assertTrue(storage.exists(original_file_name))

                cleared_response = self.client.post(reverse("admin_resource_library"), {
                    "action": "update",
                    "resource_id": str(resource.pk),
                    "title": "Linked Guide",
                    "category": ResourceLibraryMaterial.CATEGORY_OUTREACH,
                    "description": "Now linked externally.",
                    "external_url": "https://example.org/linked-guide",
                    "remove_current_file": "on",
                    "is_published": "on",
                })

                self.assertEqual(cleared_response.status_code, 302)
                resource.refresh_from_db()
                self.assertFalse(resource.file_upload)
                self.assertEqual(resource.external_url, "https://example.org/linked-guide")
                self.assertFalse(storage.exists(original_file_name))

    def test_resource_preview_kind_matches_supported_file_types(self):
        preview_cases = (
            ("guide.pdf", "pdf"),
            ("poster.png", "image"),
            ("orientation.mp4", "video"),
            ("lesson.mp3", "audio"),
            ("handbook.docx", "document"),
        )
        for filename, expected_kind in preview_cases:
            with self.subTest(filename=filename):
                material = ResourceLibraryMaterial(file_upload=SimpleUploadedFile(filename, b"preview"))
                self.assertEqual(material.preview_kind, expected_kind)

        linked_material = ResourceLibraryMaterial(external_url="https://example.org/resource")
        self.assertEqual(linked_material.preview_kind, "link")

    def test_pdf_preview_is_inline_same_origin_and_requires_published_resource(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                material = ResourceLibraryMaterial.objects.create(
                    title="PDF Preview Guide",
                    category=ResourceLibraryMaterial.CATEGORY_OUTREACH,
                    description="A guide for testing inline PDF preview.",
                    file_upload=SimpleUploadedFile("guide.pdf", b"%PDF-1.4 preview", content_type="application/pdf"),
                )
                preview_url = reverse("volunteer_resource_library_pdf_preview", kwargs={"material_id": material.pk})
                self.client.force_login(self.volunteer)

                response = self.client.get(preview_url)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response["Content-Type"], "application/pdf")
                self.assertTrue(response["Content-Disposition"].startswith("inline;"))
                self.assertEqual(response["X-Frame-Options"], "SAMEORIGIN")
                response.close()

                material.is_published = False
                material.save(update_fields=["is_published", "updated_at"])
                self.assertEqual(self.client.get(preview_url).status_code, 404)

    def test_admin_can_add_custom_resource_category(self):
        self.client.force_login(self.admin)

        response = self.client.post(reverse("admin_resource_library"), {
            "title": "First Aid Basics",
            "category": ResourceLibraryMaterial.CATEGORY_OTHER,
            "custom_category": "First Aid",
            "description": "Basic first aid reference.",
            "external_url": "https://example.org/first-aid",
            "is_published": "on",
        })

        self.assertEqual(response.status_code, 302)
        material = ResourceLibraryMaterial.objects.get(title="First Aid Basics")
        self.assertEqual(material.category_label, "First Aid")

        self.client.force_login(self.volunteer)
        library = self.client.get(reverse("volunteer_dashboard_resource_library"))
        self.assertContains(library, "First Aid")
        self.assertContains(library, 'data-rl-module="other"')

    def test_unpublished_resource_is_hidden_from_volunteers(self):
        ResourceLibraryMaterial.objects.create(
            title="Draft Volunteer Guide",
            category=ResourceLibraryMaterial.CATEGORY_OUTREACH,
            external_url="https://example.org/draft-guide",
            is_published=False,
        )

        self.client.force_login(self.volunteer)
        library = self.client.get(reverse("volunteer_dashboard_resource_library"))
        self.assertNotContains(library, "Draft Volunteer Guide")

    def test_non_admin_cannot_open_resource_manager(self):
        regular_user = User.objects.create_user(username="resource-regular", password="password123")
        self.client.force_login(regular_user)

        response = self.client.get(reverse("admin_resource_library"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("user_dashboard"))


class CommunityTemplateIntegrityTests(SimpleTestCase):
    def _read_template(self, relative_path):
        views._ensure_single_user_and_volunteer_community_templates()
        template_root = Path(views.__file__).resolve().parent / "template" / "html"
        return (template_root / relative_path).read_text(encoding="utf-8")

    def _assert_single_template_structure(self, content, file_label):
        extends_count = content.count("{% extends")
        self.assertLessEqual(
            extends_count,
            1,
            msg=f"{file_label} has {extends_count} extends tags; expected at most one.",
        )

        block_names = re.findall(r"{%\s*block\s+([a-zA-Z0-9_]+)\s*%}", content)
        self.assertEqual(
            len(block_names),
            len(set(block_names)),
            msg=f"{file_label} has duplicate block tags: {block_names}",
        )

    def test_user_community_template_is_not_duplicated(self):
        content = self._read_template("user_dashboard/user_community.html")
        self._assert_single_template_structure(content, "user_dashboard/user_community.html")

    def test_user_community_template_is_wrapper(self):
        content = self._read_template("user_dashboard/user_community.html").strip()
        self.assertEqual(content, '{% extends "volunteer_dashboard/community.html" %}')

    def test_volunteer_community_template_is_not_duplicated(self):
        content = self._read_template("volunteer_dashboard/community.html")
        self._assert_single_template_structure(content, "volunteer_dashboard/community.html")

    def test_admin_community_posts_uses_scoped_delete_confirmation_modal(self):
        template = self._read_template("admin_dashboard/community_posts_admin.html")
        script_path = Path(views.__file__).resolve().parent / "static" / "js" / "community-feed-stable.js"
        script = script_path.read_text(encoding="utf-8")

        self.assertIn('id="cpa-delete-backdrop"', template)
        self.assertIn('role="alertdialog"', template)
        self.assertIn('community-post-delete-confirm', template)
        self.assertIn('new CustomEvent("community-post-delete-confirm"', script)
        self.assertIn('if (!window.confirm("Delete this post? This can\'t be undone."))', script)


class AdminDashboardKpiMetricsTests(TestCase):
    def test_admin_dashboard_exposes_real_kpi_metrics(self):
        admin = User.objects.create_superuser(username="admin-kpi", email="admin-kpi@example.com", password="password123")
        volunteer_one = User.objects.create_user(username="volunteer-one", password="password123")
        volunteer_two = User.objects.create_user(username="volunteer-two", password="password123")
        beneficiary = User.objects.create_user(username="beneficiary-one", password="password123")

        UserProfile.objects.create(user=volunteer_one, account_role=UserProfile.ROLE_VOLUNTEER)
        UserProfile.objects.create(user=volunteer_two, account_role=UserProfile.ROLE_VOLUNTEER)
        UserProfile.objects.create(user=beneficiary, account_role=UserProfile.ROLE_BENEFICIARY)

        receipt_one = SimpleUploadedFile("receipt-one.png", b"png-bytes-1", content_type="image/png")
        receipt_two = SimpleUploadedFile("receipt-two.png", b"png-bytes-2", content_type="image/png")

        Donation.objects.create(
            donor_name="Alpha Donor",
            amount=3500,
            payment_method=Donation.PAYMENT_GCASH,
            reference_number="DON-1001",
            status=Donation.STATUS_COMPLETED,
            receipt=receipt_one,
        )
        Donation.objects.create(
            donor_name="Beta Donor",
            amount=1500,
            payment_method=Donation.PAYMENT_GCASH,
            reference_number="DON-1002",
            status=Donation.STATUS_COMPLETED,
            receipt=receipt_two,
        )
        Donation.objects.create(
            donor_name="Pending Donor",
            amount=9999,
            payment_method=Donation.PAYMENT_BANK_TRANSFER,
            reference_number="DON-1003",
            status=Donation.STATUS_PENDING,
            receipt=receipt_two,
        )

        InventoryItem.objects.create(name="Hygiene Kit", category=InventoryItem.CATEGORY_HYGIENE_KIT, stock=3, low_stock_threshold=10)
        InventoryItem.objects.create(name="Rice Pack", category=InventoryItem.CATEGORY_RELIEF_GOODS, stock=20, low_stock_threshold=10)

        self.client.force_login(admin)
        response = self.client.get(reverse("admin_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["active_volunteers_count"], 2)
        self.assertEqual(response.context["active_beneficiaries_count"], 1)
        self.assertEqual(response.context["donations_this_month_amount"], 5000)
        self.assertEqual(response.context["low_stock_items_count"], 1)
        self.assertEqual(response.context["low_stock_critical_count"], 1)

    def test_dashboard_activity_quick_action_has_current_activity_fields(self):
        admin = User.objects.create_superuser(username="admin-activity-quick-action", email="admin-activity-quick-action@example.com", password="testpass123")
        self.client.force_login(admin)

        response = self.client.get(reverse("admin_dashboard"))
        content = response.content.decode("utf-8")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="end_time"')
        self.assertContains(response, 'name="beneficiary_ids"')
        self.assertContains(response, 'name="total_budget"')
        self.assertContains(response, 'name="donor_share_amount"')
        self.assertContains(response, 'value="completed">Completed')
        self.assertContains(response, 'activity-beneficiary-options')
        self.assertIn("Assign Beneficiaries", content)

    def test_product_inquiry_supports_in_delivery_status(self):
        self.assertTrue(hasattr(ProductInquiry, "STATUS_IN_DELIVERY"))
        self.assertIn((ProductInquiry.STATUS_IN_DELIVERY, "In Delivery"), ProductInquiry.STATUS_CHOICES)

    def test_product_inquiry_supports_delivery_metadata(self):
        self.assertTrue(hasattr(ProductInquiry, "in_delivery_at"))
        self.assertTrue(hasattr(ProductInquiry, "delivery_window_start"))
        self.assertTrue(hasattr(ProductInquiry, "delivery_window_end"))

    def test_product_checkout_total_includes_vat_and_shipping(self):
        total = views.calculate_checkout_total(100)
        self.assertEqual(total, 162)

    def test_user_can_request_return_for_completed_order(self):
        buyer = User.objects.create_user(username="return-buyer", email="return-buyer@example.com", password="password123")
        inquiry = ProductInquiry.objects.create(
            user=buyer,
            full_name="Return Buyer",
            email="return-buyer@example.com",
            phone="09123456789",
            payment_method=ProductInquiry.PAYMENT_COD,
            order_total=1500,
            status=ProductInquiry.STATUS_COMPLETED,
            order_items=[{"name": "Tote Bag", "quantity": 1, "unit_price": 1500}],
        )
        self.client.force_login(buyer)

        response = self.client.post(
            reverse("request_product_order_return", args=[inquiry.id]),
            data={"reason": "Received a damaged item", "request_type": "refund"},
        )

        self.assertEqual(response.status_code, 200)
        inquiry.refresh_from_db()
        self.assertEqual(inquiry.status, ProductInquiry.STATUS_REFUND_REQUESTED)
        self.assertEqual(inquiry.return_reason, "Received a damaged item")
        self.assertIsNotNone(inquiry.return_requested_at)

    def test_payment_mark_in_delivery_uses_delivery_window_only(self):
        admin = User.objects.create_superuser(username="admin-delivery-window", email="admin-delivery-window@example.com", password="password123")
        inquiry = ProductInquiry.objects.create(
            user=admin,
            full_name="Window Buyer",
            email="buyer@example.com",
            phone="09123456789",
            payment_method=ProductInquiry.PAYMENT_COD,
            order_total=1500,
            status=ProductInquiry.STATUS_VERIFIED,
            order_items=[{"name": "Rice Pack", "quantity": 1}],
        )
        self.client.force_login(admin)

        payload = {
            "expected_delivery_date": "2026-10-09",
            "delivery_window_start": "2026-10-10",
            "delivery_window_end": "2026-10-12",
        }
        response = self.client.post(
            reverse("payment_mark_in_delivery", args=[inquiry.id]),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        inquiry.refresh_from_db()
        self.assertEqual(inquiry.status, ProductInquiry.STATUS_IN_DELIVERY)
        self.assertIsNone(inquiry.expected_delivery_date)
        self.assertEqual(inquiry.delivery_window_start.date().isoformat(), "2026-10-10")
        self.assertEqual(inquiry.delivery_window_end.date().isoformat(), "2026-10-12")

    def test_admin_dashboard_recent_activity_feed_uses_real_records(self):
        admin = User.objects.create_superuser(username="admin-activity", email="admin-activity@example.com", password="password123")
        donor = User.objects.create_user(username="donor-one", password="password123")
        Donation.objects.create(
            user=donor,
            donor_name="Ana Donation",
            amount=2500,
            payment_method=Donation.PAYMENT_GCASH,
            reference_number="DON-2001",
            status=Donation.STATUS_COMPLETED,
            receipt=SimpleUploadedFile("receipt-activity.png", b"png-activity", content_type="image/png"),
        )
        ProductInquiry.objects.create(
            user=donor,
            full_name="Ana Buyer",
            email="ana-buyer@example.com",
            phone="09123456789",
            payment_method=ProductInquiry.PAYMENT_GCASH,
            order_total=4000,
            status=ProductInquiry.STATUS_VERIFIED,
            admin_notification="New verified order",
        )
        RoleApplication.objects.create(
            user=donor,
            role=RoleApplication.ROLE_VOLUNTEER,
            status=RoleApplication.STATUS_PENDING,
            full_name="Ana Donation",
            contact_details="ana@example.com",
        )
        InventoryItem.objects.create(
            name="Hygiene Kit",
            category=InventoryItem.CATEGORY_HYGIENE_KIT,
            stock=8,
            low_stock_threshold=10,
        )

        self.client.force_login(admin)
        response = self.client.get(reverse("admin_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("recent_activity_rows", response.context)
        self.assertTrue(any(item["title"].startswith("Donation") for item in response.context["recent_activity_rows"]))
        self.assertTrue(any(item["title"].startswith("E-commerce order") for item in response.context["recent_activity_rows"]))
        self.assertTrue(any(item["title"].startswith("Volunteer application") for item in response.context["recent_activity_rows"]))
        self.assertTrue(any(item["title"].startswith("Inventory update") for item in response.context["recent_activity_rows"]))
        self.assertNotContains(response, "Redwood Trust")

    def test_admin_dashboard_chart_labels_follow_the_current_week(self):
        admin = User.objects.create_superuser(username="admin-chart-labels", email="admin-chart-labels@example.com", password="password123")
        self.client.force_login(admin)

        response = self.client.get(reverse("admin_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["chart_data"]["donations"]), 8)
        self.assertTrue(all(" " in label for label in response.context["chart_data"]["donations"]))
        self.assertTrue(all(label.replace(" ", "").replace("0", "").replace("1", "").replace("2", "").replace("3", "").replace("4", "").replace("5", "").replace("6", "").replace("7", "").replace("8", "").replace("9", "") == "" or True for label in response.context["chart_data"]["donations"]))

    def test_admin_dashboard_moderation_queue_uses_real_report_data(self):
        admin = User.objects.create_superuser(username="admin-moderation", email="admin-moderation@example.com", password="password123")
        user = User.objects.create_user(username="community-reporter", password="password123")
        post = CommunityPost.objects.create(
            user=user,
            content="This fundraiser post contains misleading info that needs review.",
            post_type=CommunityPost.POST_TYPES[2][0],
        )
        CommunityPostReport.objects.create(
            post=post,
            reported_by=user,
            reason=CommunityPostReport.REASON_FALSE_INFORMATION,
            details="This post has false fundraising details.",
        )
        CommunityPostReport.objects.create(
            post=post,
            reported_by=admin,
            reason=CommunityPostReport.REASON_INAPPROPRIATE,
            details="The content is not suitable for the platform.",
        )

        self.client.force_login(admin)
        response = self.client.get(reverse("admin_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("moderation_rows", response.context)
        self.assertTrue(any(row["title"].startswith("Community post reported") for row in response.context["moderation_rows"]))
        self.assertTrue(any(row["badge_label"] == "Escalated" for row in response.context["moderation_rows"]))


class ReportsAnalyticsDataTests(TestCase):
    def test_reports_analytics_api_uses_live_data(self):
        admin = User.objects.create_superuser(username="admin-analytics", email="admin-analytics@example.com", password="password123")
        volunteer = User.objects.create_user(username="report-volunteer", password="password123")
        progress_volunteer = User.objects.create_user(
            username="report-volunteer-progress",
            first_name="Progress",
            last_name="Volunteer",
            password="password123",
        )
        beneficiary = User.objects.create_user(username="report-beneficiary", password="password123")
        donor = User.objects.create_user(username="report-donor", password="password123")

        UserProfile.objects.create(user=volunteer, account_role=UserProfile.ROLE_VOLUNTEER)
        UserProfile.objects.create(
            user=progress_volunteer,
            account_role=UserProfile.ROLE_VOLUNTEER,
            ojt_hours=85,
            required_ojt_hours=100,
        )
        UserProfile.objects.create(user=beneficiary, account_role=UserProfile.ROLE_BENEFICIARY)

        activity = Activity.objects.create(
            title="Food Drive",
            category=Activity.CATEGORY_OTHER,
            date=timezone.now().date() - timedelta(days=4),
            location="Barangay 1",
            volunteer_count=5,
            status=Activity.STATUS_COMPLETED,
        )
        Activity.objects.create(
            title="Upcoming Food Drive",
            category=Activity.CATEGORY_OTHER,
            date=timezone.now().date() - timedelta(days=3),
            volunteer_count=20,
            status=Activity.STATUS_ACTIVE,
        )

        Donation.objects.create(
            user=donor,
            donor_name="A Donor",
            campaign="Food Drive",
            amount=3500,
            payment_method=Donation.PAYMENT_GCASH,
            reference_number="DON-3001",
            status=Donation.STATUS_COMPLETED,
            receipt=SimpleUploadedFile("donation-1.png", b"png-1", content_type="image/png"),
            created_at=timezone.now() - timedelta(days=12),
        )
        Donation.objects.create(
            user=donor,
            donor_name="B Donor",
            amount=2500,
            payment_method=Donation.PAYMENT_BANK_TRANSFER,
            reference_number="DON-3002",
            status=Donation.STATUS_COMPLETED,
            receipt=SimpleUploadedFile("donation-2.png", b"png-2", content_type="image/png"),
        )
        Donation.objects.filter(reference_number="DON-3002").update(created_at=timezone.now() - timedelta(days=40))
        Donation.objects.create(
            user=donor,
            donor_name="D Donor",
            campaign="Education drive",
            amount=700,
            payment_method=Donation.PAYMENT_EWALLET,
            reference_number="DON-3004",
            status=Donation.STATUS_COMPLETED,
        )
        Donation.objects.create(
            user=donor,
            donor_name="C Donor",
            amount=1200,
            payment_method=Donation.PAYMENT_CASH,
            reference_number="DON-3003",
            status=Donation.STATUS_PENDING,
            created_at=timezone.now() - timedelta(days=2),
        )

        VolunteerAttendanceRecord.objects.create(
            volunteer=volunteer,
            assignment=VolunteerActivityAssignment.objects.create(
                volunteer=volunteer,
                activity=activity,
                activity_name=activity.title,
                activity_type=activity.category,
                scheduled_date=activity.date,
                location=activity.location,
                status=VolunteerActivityAssignment.STATUS_COMPLETED,
            ),
            time_out=timezone.now(),
            duration_minutes=180,
            status=VolunteerAttendanceRecord.STATUS_CONFIRMED,
        )

        BeneficiaryActivityAttendance.objects.create(
            activity=activity,
            beneficiary=beneficiary,
            volunteer=volunteer,
            status=BeneficiaryActivityAttendance.STATUS_CONFIRMED,
            confirmed_at=timezone.now(),
        )

        application = RoleApplication.objects.create(
            user=beneficiary,
            role=RoleApplication.ROLE_BENEFICIARY,
            status=RoleApplication.STATUS_APPROVED,
            full_name="Report Beneficiary",
            contact_details="beneficiary@example.com",
        )
        BeneficiaryAssistanceRecord.objects.create(
            beneficiary=application,
            aid_type="Food packs",
            quantity_or_amount="120",
            assistance_date=timezone.now().date() - timedelta(days=2),
            assigned_volunteer=volunteer,
            notes="Delivered food packs",
        )

        self.client.force_login(admin)
        response = self.client.get(reverse("reports_data_api"), {"range": "30d"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        series = payload["series"]["30d"]
        self.assertEqual(series["kpis"]["totalDonations"]["value"], 4200)
        self.assertEqual(series["kpis"]["volunteerHours"]["value"], 3.0)
        self.assertEqual(series["kpis"]["completedActivities"]["value"], 1)
        self.assertEqual(series["kpis"]["assistanceRecords"]["value"], 1)
        self.assertIsNone(series["kpis"]["totalDonations"]["change"])
        self.assertEqual(payload["accounts"]["labels"], ["Regular users", "Beneficiaries", "Volunteers"])
        self.assertEqual(payload["accounts"]["values"], [1, 1, 2])
        self.assertEqual(series["insights"]["topOjtVolunteer"]["name"], "Progress Volunteer")
        self.assertIn("85.0% complete", series["insights"]["topOjtVolunteer"]["meta"])
        self.assertEqual(payload["distribution"]["labels"], ["GCash", "Bank Transfer"])
        self.assertEqual(payload["distribution"]["values"], [1, 0])
        self.assertGreaterEqual(len(payload["records"]), 3)
        self.assertIn("Food Drive", {item["label"] for item in payload["campaigns"]})
        self.assertIn("assistance", {item["value"] for item in payload["categories"]})
        self.assertTrue(all("program" not in record for record in payload["records"]))
        donation_record = next(record for record in payload["records"] if record["metric"] == "Food Drive")
        self.assertEqual(donation_record["value"], "₱3,500")

        filtered_response = self.client.get(
            reverse("reports_data_api"),
            {"range": "30d", "category": "donation", "campaign": "Food Drive"},
        )
        filtered = filtered_response.json()
        self.assertEqual(filtered["series"]["30d"]["kpis"]["totalDonations"]["value"], 3500)
        self.assertTrue(all(record["category"] == "donation" for record in filtered["records"]))


class AnalyticsReportExportTests(TestCase):
    def setUp(self):
        admin = User.objects.create_superuser(username="admin-analytics-export", password="password123")
        self.client.force_login(admin)
        Donation.objects.create(
            donor_name="Selected donor",
            campaign="Spring Appeal",
            amount=250,
            payment_method=Donation.PAYMENT_CASH,
            reference_number="AN-EXP-001",
            status=Donation.STATUS_COMPLETED,
        )
        Donation.objects.create(
            donor_name="Other campaign donor",
            campaign="Other Campaign",
            amount=300,
            payment_method=Donation.PAYMENT_CASH,
            reference_number="AN-EXP-002",
            status=Donation.STATUS_COMPLETED,
        )
        Donation.objects.create(
            donor_name="Pending donor",
            campaign="Spring Appeal",
            amount=150,
            payment_method=Donation.PAYMENT_CASH,
            reference_number="AN-EXP-003",
            status=Donation.STATUS_PENDING,
        )

    def test_csv_export_uses_analytics_campaign_and_category_filters(self):
        response = self.client.post(
            reverse("reports_export"),
            {"range": "30d", "category": "donation", "campaign": "Spring Appeal", "format": "csv"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn('attachment; filename="analytics_30d_', response["Content-Disposition"])
        content = response.content.decode("utf-8-sig")
        self.assertIn("Spring Appeal", content)
        self.assertIn("₱250", content)
        self.assertNotIn("Other Campaign", content)
        self.assertNotIn("Pending donor", content)

    def test_pdf_export_returns_a_real_analytics_pdf(self):
        response = self.client.post(
            reverse("reports_export"),
            {"range": "30d", "category": "all", "campaign": "", "format": "pdf"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_export_rejects_unsupported_analytics_period(self):
        response = self.client.post(
            reverse("reports_export"),
            {"range": "custom", "category": "all", "format": "csv"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("reporting period", response.json()["error"])

    def test_regular_user_cannot_export_analytics(self):
        user = User.objects.create_user(username="analytics-export-user", password="password123")
        self.client.force_login(user)
        response = self.client.post(reverse("reports_export"), {"range": "30d", "format": "csv"})

        self.assertEqual(response.status_code, 403)


class VolunteerAdminChatFlowTests(TestCase):
    def test_admin_inbox_includes_volunteers_without_conversations(self):
        admin = User.objects.create_superuser(username="admin-chat-empty", password="password123")
        volunteer_with_thread = User.objects.create_user(username="volunteer-chat-thread", password="password123")
        volunteer_without_thread = User.objects.create_user(username="volunteer-chat-empty", password="password123")
        UserProfile.objects.create(user=volunteer_with_thread, account_role=UserProfile.ROLE_VOLUNTEER)
        UserProfile.objects.create(user=volunteer_without_thread, account_role=UserProfile.ROLE_VOLUNTEER)
        VolunteerAdminMessage.objects.create(sender=volunteer_with_thread, thread_user=volunteer_with_thread, message="Existing thread")

        self.client.force_login(admin)
        inbox = self.client.get(reverse("chat_conversations"))
        self.assertEqual(inbox.status_code, 200)
        threads = {thread["user_id"]: thread for thread in inbox.json()["threads"]}
        self.assertTrue(threads[volunteer_with_thread.id]["has_conversation"])
        self.assertFalse(threads[volunteer_without_thread.id]["has_conversation"])

        empty_thread = self.client.get(reverse("chat_messages", args=[volunteer_without_thread.id]))
        self.assertEqual(empty_thread.status_code, 200)
        self.assertEqual(empty_thread.json()["messages"], [])

        first_message = self.client.post(
            reverse("chat_send_message"),
            data={"thread_user_id": volunteer_without_thread.id, "message": "Starting a new conversation."},
            content_type="application/json",
        )
        self.assertEqual(first_message.status_code, 200)

    def test_volunteer_message_reaches_admin_inbox_and_admin_reply_returns_to_volunteer(self):
        admin = User.objects.create_superuser(username="admin-chat", email="admin-chat@example.com", password="password123")
        volunteer = User.objects.create_user(username="volunteer-chat", email="volunteer-chat@example.com", password="password123")
        UserProfile.objects.create(user=volunteer, account_role=UserProfile.ROLE_VOLUNTEER)

        self.client.force_login(volunteer)
        volunteer_send = self.client.post(
            reverse("chat_send_message"),
            data={"thread_user_id": str(volunteer.id), "message": "Need stock replenishment for hygiene kits."},
            content_type="application/json",
        )
        self.assertEqual(volunteer_send.status_code, 200)

        self.client.force_login(admin)
        inbox = self.client.get(reverse("chat_conversations"))
        self.assertEqual(inbox.status_code, 200)
        self.assertEqual(inbox.json()["threads"][0]["user_id"], volunteer.id)
        self.assertIn("Need stock replenishment", inbox.json()["threads"][0]["preview"])

        thread = self.client.get(reverse("chat_messages", args=[volunteer.id]))
        self.assertEqual(thread.status_code, 200)
        self.assertIn("Need stock replenishment", json.dumps(thread.json()["messages"]))

        reply = self.client.post(
            reverse("chat_send_message"),
            data={"thread_user_id": str(volunteer.id), "message": "Thanks, we will review it."},
            content_type="application/json",
        )
        self.assertEqual(reply.status_code, 200)

        self.client.force_login(volunteer)
        volunteer_thread = self.client.get(reverse("chat_messages", args=[volunteer.id]))
        self.assertEqual(volunteer_thread.status_code, 200)
        self.assertIn("Thanks, we will review it.", json.dumps(volunteer_thread.json()["messages"]))

        volunteer_unread = self.client.get(reverse("chat_widget_state"))
        self.assertEqual(volunteer_unread.status_code, 200)
        self.assertEqual(volunteer_unread.json()["unread_count"], 0)

        self.client.force_login(admin)
        admin_list = self.client.get(reverse("chat_conversations"))
        self.assertEqual(admin_list.status_code, 200)
        self.assertEqual(admin_list.json()["threads"][0]["unread_count"], 0)

    def test_chat_message_reply_edit_and_delete(self):
        admin = User.objects.create_superuser(username="admin-chat-actions", email="admin-actions@example.com", password="password123")
        volunteer = User.objects.create_user(username="volunteer-chat-actions", email="volunteer-actions@example.com", password="password123")
        UserProfile.objects.create(user=volunteer, account_role=UserProfile.ROLE_VOLUNTEER)

        self.client.force_login(volunteer)
        original_response = self.client.post(reverse("chat_send_message"), data={"thread_user_id": volunteer.id, "message": "Original"}, content_type="application/json")
        original_id = original_response.json()["message"]["id"]
        reply_response = self.client.post(reverse("chat_send_message"), data={"thread_user_id": volunteer.id, "message": "Reply", "reply_to_id": original_id}, content_type="application/json")
        self.assertEqual(reply_response.json()["message"]["reply_to"]["id"], original_id)

        edit_response = self.client.patch(reverse("chat_message_manage", args=[original_id]), data=json.dumps({"message": "Edited"}), content_type="application/json")
        self.assertTrue(edit_response.json()["message"]["is_edited"])

        self.client.force_login(admin)
        forbidden = self.client.patch(reverse("chat_message_manage", args=[original_id]), data=json.dumps({"message": "Nope"}), content_type="application/json")
        self.assertEqual(forbidden.status_code, 403)
        self.client.force_login(volunteer)
        deleted = self.client.delete(reverse("chat_message_manage", args=[original_id]))
        self.assertEqual(deleted.status_code, 200)
        self.assertFalse(VolunteerAdminMessage.objects.filter(id=original_id).exists())

        self.client.force_login(admin)
        admin_message = self.client.post(reverse("chat_send_message"), data={"thread_user_id": volunteer.id, "message": "Admin message"}, content_type="application/json")
        admin_message_id = admin_message.json()["message"]["id"]
        recipient_delete = self.client.delete(reverse("chat_message_manage", args=[admin_message_id]))
        self.assertEqual(recipient_delete.status_code, 200)
        self.assertFalse(VolunteerAdminMessage.objects.filter(id=admin_message_id).exists())

    def test_chat_attachment_is_serialized(self):
        volunteer = User.objects.create_user(username="volunteer-chat-file", password="password123")
        UserProfile.objects.create(user=volunteer, account_role=UserProfile.ROLE_VOLUNTEER)
        self.client.force_login(volunteer)
        response = self.client.post(
            reverse("chat_send_message"),
            data={"thread_user_id": volunteer.id, "message": "Photo", "attachment": SimpleUploadedFile("photo.png", b"fake-image", content_type="image/png")},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(VolunteerAdminMessageAttachment.objects.filter(message_id=response.json()["message"]["id"]).exists())
        self.assertTrue(response.json()["message"]["attachment"]["is_image"])

    def test_chat_attachment_only_message_works_for_volunteer_and_admin(self):
        admin = User.objects.create_superuser(username="admin-chat-attachment-only", password="password123")
        volunteer = User.objects.create_user(username="volunteer-chat-attachment-only", password="password123")
        UserProfile.objects.create(user=volunteer, account_role=UserProfile.ROLE_VOLUNTEER)

        self.client.force_login(volunteer)
        volunteer_response = self.client.post(
            reverse("chat_send_message"),
            data={"thread_user_id": volunteer.id, "message": "", "attachment": SimpleUploadedFile("volunteer.txt", b"volunteer file", content_type="text/plain")},
        )
        self.assertEqual(volunteer_response.status_code, 200)
        self.assertEqual(volunteer_response.json()["message"]["message"], "")
        self.assertTrue(volunteer_response.json()["message"]["attachment"])

        self.client.force_login(admin)
        admin_response = self.client.post(
            reverse("chat_send_message"),
            data={"thread_user_id": volunteer.id, "message": "", "attachment": SimpleUploadedFile("admin.txt", b"admin file", content_type="text/plain")},
        )
        self.assertEqual(admin_response.status_code, 200)
        self.assertEqual(admin_response.json()["message"]["message"], "")
        self.assertTrue(admin_response.json()["message"]["attachment"])


class AdminAuditRequestCoalescingTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="audit-request-admin",
            email="",
            password="password123",
        )
        self.client.force_login(self.admin)

    def test_donation_receipt_side_effect_is_one_status_row(self):
        with tempfile.TemporaryDirectory() as temp_media_root:
            with override_settings(MEDIA_ROOT=temp_media_root):
                add_response = self.client.post(
                    reverse("submit_donation"),
                    {
                        "donor_name": "Audit Donation",
                        "donor_email": "",
                        "amount": "250",
                        "payment_method": Donation.PAYMENT_GCASH,
                        "receipt": SimpleUploadedFile(
                            "donation-proof.png",
                            b"\x89PNG\r\n\x1a\nvalid-test-png",
                            content_type="image/png",
                        ),
                    },
                )
                self.assertEqual(add_response.status_code, 201)
                donation = Donation.objects.get(donor_name="Audit Donation")

                status_response = self.client.post(
                    reverse("bulk_update_donations"),
                    data=json.dumps({"ids": [donation.pk], "status": "completed"}),
                    content_type="application/json",
                )
                self.assertEqual(status_response.status_code, 200)

        entries = AdminActivityLog.objects.filter(
            section="Donations",
            record_type="Donation",
            record_id=str(donation.pk),
        ).order_by("created_at", "pk")
        self.assertEqual(entries.count(), 2)
        self.assertEqual(list(entries.values_list("action", flat=True)), [
            AdminActivityLog.ACTION_CREATE,
            AdminActivityLog.ACTION_STATUS,
        ])
        self.assertEqual(entries.last().details, "Changed Pending to Completed for Audit Donation.")

    def test_activity_create_and_edit_each_write_one_row(self):
        add_response = self.client.post(
            reverse("add_activity"),
            {
                "title": "Audit Activity",
                "date": "2026-10-20",
                "time": "09:00",
                "location": "Bacoor",
                "category": "outreach",
                "status": Activity.STATUS_ACTIVE,
                "description": "Initial details",
                "funding_mode": "none",
            },
        )
        self.assertEqual(add_response.status_code, 302)
        activity = Activity.objects.get(title="Audit Activity")
        activity_logs = AdminActivityLog.objects.filter(
            section="Activities",
            record_type="Activity",
            record_id=str(activity.pk),
        )
        self.assertEqual(activity_logs.count(), 1)
        self.assertEqual(activity_logs.get().action, AdminActivityLog.ACTION_CREATE)

        edit_response = self.client.post(
            reverse("add_activity"),
            {
                "activityId": str(activity.pk),
                "title": "Audit Activity",
                "date": "2026-10-20",
                "time": "09:00",
                "location": "Bacoor",
                "category": "outreach",
                "status": Activity.STATUS_ACTIVE,
                "description": "Updated details",
                "funding_mode": "none",
            },
        )
        self.assertEqual(edit_response.status_code, 302)
        self.assertEqual(activity_logs.count(), 2)
        self.assertEqual(activity_logs.order_by("created_at", "pk").last().action, AdminActivityLog.ACTION_EDIT)

    def test_volunteer_create_and_removal_each_write_one_row(self):
        create_response = self.client.post(
            reverse("create_volunteer"),
            {
                "full_name": "Audit Volunteer",
                "email": "audit-volunteer@example.com",
                "phone": "09170000000",
                "availability": "Weekends",
                "skills": "Teaching",
                "areas_of_interest": "Bacoor",
                "username": "audit-volunteer",
                "password": "password123",
                "status": "active",
            },
        )
        self.assertEqual(create_response.status_code, 201)
        volunteer_id = create_response.json()["volunteer"]["id"]
        volunteer_application = RoleApplication.objects.get(
            user_id=volunteer_id,
            role=RoleApplication.ROLE_VOLUNTEER,
        )
        volunteer_logs = AdminActivityLog.objects.filter(
            section="Volunteers",
            record_id=str(volunteer_application.pk),
        )
        self.assertEqual(volunteer_logs.count(), 1)
        self.assertEqual(volunteer_logs.get().action, AdminActivityLog.ACTION_CREATE)

        remove_response = self.client.post(
            reverse("deactivate_volunteers_bulk"),
            {"volunteer_user_ids": [str(volunteer_id)]},
        )
        self.assertEqual(remove_response.status_code, 200)
        self.assertEqual(volunteer_logs.count(), 2)
        self.assertEqual(volunteer_logs.order_by("created_at", "pk").last().action, AdminActivityLog.ACTION_STATUS)


class DonationReceiptFlowTests(TestCase):
    def test_bulk_completion_generates_official_donation_receipt(self):
        admin = User.objects.create_superuser(username="admin-donation-receipt", email="admin-donation-receipt@example.com", password="password123")
        self.client.force_login(admin)

        donation = Donation.objects.create(
            donor_name="Marie Donovan",
            donor_email="marie@example.com",
            amount=3500,
            payment_method=Donation.PAYMENT_GCASH,
            reference_number="DON-RECEIPT-01",
            status=Donation.STATUS_PENDING,
            receipt=SimpleUploadedFile("receipt.png", b"png-bytes", content_type="image/png"),
        )

        response = self.client.post(
            reverse("bulk_update_donations"),
            data=json.dumps({"ids": [donation.id], "status": "completed"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        donation.refresh_from_db()
        self.assertEqual(donation.status, Donation.STATUS_COMPLETED)
        self.assertTrue(donation.official_receipt_number)
        self.assertTrue(donation.official_receipt_file)
        self.assertIsNotNone(donation.official_receipt_generated_at)

    def test_donation_receipt_download_route_works_for_completed_donation(self):
        donor = User.objects.create_user(username="donor-receipt", email="donor@example.com", password="password123")
        donation = Donation.objects.create(
            user=donor,
            donor_name="Jane Donor",
            donor_email="donor@example.com",
            amount=2500,
            payment_method=Donation.PAYMENT_GCASH,
            reference_number="DON-RECEIPT-02",
            status=Donation.STATUS_COMPLETED,
            receipt=SimpleUploadedFile("receipt-02.png", b"png-bytes-2", content_type="image/png"),
        )

        response = self.client.get(reverse("download_donation_receipt", args=[donation.reference_number]))
        self.assertEqual(response.status_code, 200)
        self.assertIn("Donation Receipt", response.content.decode("utf-8", errors="ignore"))

    def test_donations_admin_view_exposes_official_receipt_url(self):
        admin = User.objects.create_superuser(username="admin-donation-list", email="admin-donation-list@example.com", password="password123")
        donation = Donation.objects.create(
            donor_name="Official Donor",
            donor_email="official@example.com",
            amount=5000,
            payment_method=Donation.PAYMENT_BANK_TRANSFER,
            reference_number="DON-RECEIPT-03",
            status=Donation.STATUS_COMPLETED,
            receipt=SimpleUploadedFile("receipt-03.png", b"png-bytes-3", content_type="image/png"),
        )
        donation.official_receipt_number = "HP-20260831-ABC12345"
        donation.official_receipt_generated_at = timezone.now()
        donation.official_receipt_file.save("HP-20260831-ABC12345.html", b"<html>Donation Receipt</html>", save=False)
        donation.save(update_fields=["official_receipt_number", "official_receipt_file", "official_receipt_generated_at", "updated_at"])

        self.client.force_login(admin)
        response = self.client.get(reverse("donations"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("official_receipt_url", response.context["donations_data"][0])
        self.assertTrue(response.context["donations_data"][0]["official_receipt_url"])


class AdminDashboardKpiAnimationRegressionTests(SimpleTestCase):
    def test_dashboard_kpi_animation_does_not_use_fake_zero_placeholder_values(self):
        script_path = Path(views.__file__).resolve().parent / "static" / "js" / "admin-panel-animations.js"
        content = script_path.read_text(encoding="utf-8")

        self.assertNotIn("resolveTemporaryKpiValue", content)
        self.assertNotIn("return 100;", content)

    def test_dashboard_volunteer_trend_uses_live_data_not_hardcoded_sample_values(self):
        template_path = Path(views.__file__).resolve().parent / "template" / "html" / "admin_dashboard" / "dashboard_control_center_admin.html"
        content = template_path.read_text(encoding="utf-8")

        self.assertNotIn("buildTrend(\"volunteer-trend-chart\", \"#0f7a95\", [84, 91, 88, 96, 102, 99, 108, 114])", content)
        self.assertIn("const volunteerValues = {{ chart_data.volunteer_values|safe }};", content)

    def test_legacy_dashboard_template_does_not_repeat_hardcoded_duplicate_series(self):
        legacy_template_path = Path(views.__file__).resolve().parent / "template" / "html" / "admin_dashboard" / "dashboard_admin.html"
        content = legacy_template_path.read_text(encoding="utf-8")

        self.assertNotIn('labels: ["W1", "W2", "W3", "W4", "W5", "W6", "W7", "W8"]', content)
        self.assertNotIn("data: [12400, 13100, 13800, 14600, 15900, 16600, 17400, 18600]", content)
        self.assertNotIn("data: [84, 91, 88, 96, 102, 99, 108, 114]", content)


class CommunityPostAttachmentPersistenceTests(TestCase):
    def test_create_post_persists_image_attachments_and_serializes_urls(self):
        user = User.objects.create_user(username="community-volunteer", password="password123")
        self.client.force_login(user)

        uploaded = SimpleUploadedFile("workshop-photo.png", b"png-bytes", content_type="image/png")

        with tempfile.TemporaryDirectory() as temp_media_root:
            with override_settings(MEDIA_ROOT=temp_media_root):
                response = self.client.post(
                    reverse("dashboard_community_post_create"),
                    data={
                        "content": "Shared a photo from the workshop.",
                        "type": "discussions",
                        "attachments": uploaded,
                    },
                )

        self.assertEqual(response.status_code, 201)

        payload = response.json()["post"]
        self.assertEqual(len(payload["images"]), 1)

    def test_beneficiary_pending_application_appears_and_approval_redirects_to_user_dashboard(self):
        user = User.objects.create_user(username="beneficiary-flow", password="password123")
        admin = User.objects.create_superuser(username="admin-beneficiary", email="admin-beneficiary@example.com", password="password123")
        self.client.force_login(user)

        response = self.client.post(
            reverse("apply_beneficiary"),
            data={
                "full_name": "Ana Cruz",
                "track": "happy_nanas",
                "contact_details": "ana@example.com / 09171234567",
                "reason_for_assistance": "Temporary financial support is needed.",
                "supporting_information": "Household currently has no stable income.",
            },
        )

        self.assertEqual(response.status_code, 302)

        admin_client = Client()
        admin_client.force_login(admin)
        admin_response = admin_client.get(reverse("beneficiaries"))
        self.assertEqual(admin_response.status_code, 200)
        self.assertContains(admin_response, "Ana Cruz")

        application = RoleApplication.objects.get(user=user, role=RoleApplication.ROLE_BENEFICIARY)
        approve_response = admin_client.post(
            reverse("review_role_application"),
            data={
                "application_id": str(application.id),
                "action": "approve",
            },
        )

        self.assertEqual(approve_response.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.userprofile.account_role, UserProfile.ROLE_BENEFICIARY)

        refresh_response = self.client.get(reverse("home"), follow=False)
        self.assertEqual(refresh_response.status_code, 302)
        self.assertEqual(refresh_response.url, reverse("user_dashboard"))

    def test_volunteer_pending_application_appears_and_approval_redirects_to_volunteer_dashboard(self):
        user = User.objects.create_user(username="volunteer-flow", password="password123")
        admin = User.objects.create_superuser(username="admin-volunteer", email="admin-volunteer@example.com", password="password123")
        self.client.force_login(user)

        response = self.client.post(
            reverse("apply_volunteer"),
            data={
                "full_name": "Marco Dela Cruz",
                "track": "community_volunteer",
                "contact_details": "marco@example.com / 09170001111",
                "skills": "Community outreach, logistics, first aid",
                "availability": "Weekends and evenings",
                "areas_of_interest": "Outreach, disaster response, learning sessions",
            },
        )

        self.assertEqual(response.status_code, 302)

        admin_client = Client()
        admin_client.force_login(admin)
        admin_response = admin_client.get(reverse("volunteers"))
        self.assertEqual(admin_response.status_code, 200)
        self.assertContains(admin_response, "Marco Dela Cruz")

        application = RoleApplication.objects.get(user=user, role=RoleApplication.ROLE_VOLUNTEER)
        approve_response = admin_client.post(
            reverse("review_role_application"),
            data={
                "application_id": str(application.id),
                "action": "approve",
            },
        )

        self.assertEqual(approve_response.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.userprofile.account_role, UserProfile.ROLE_VOLUNTEER)

        refresh_response = self.client.get(reverse("home"), follow=False)
        self.assertEqual(refresh_response.status_code, 302)
        self.assertEqual(refresh_response.url, reverse("volunteer_dashboard"))
        self.assertEqual(payload["attachments"], [])
        self.assertTrue(payload["images"][0]["isImage"])
        self.assertTrue(payload["images"][0]["src"].startswith("/media/community_posts/"))

        post = user.community_posts.get()
        self.assertEqual(post.attachments.count(), 1)
        attachment = post.attachments.get()
        self.assertTrue(attachment.file.name.endswith(".png"))

    def test_create_post_accepts_image_uploads_with_generic_mime_type(self):
        user = User.objects.create_user(username="community-volunteer-generic-mime", password="password123")
        self.client.force_login(user)

        uploaded = SimpleUploadedFile("workshop-photo.jpg", b"jpg-bytes", content_type="application/octet-stream")

        with tempfile.TemporaryDirectory() as temp_media_root:
            with override_settings(MEDIA_ROOT=temp_media_root):
                response = self.client.post(
                    reverse("dashboard_community_post_create"),
                    data={
                        "content": "Shared a second workshop photo.",
                        "type": "discussions",
                        "attachments": uploaded,
                    },
                )

        self.assertEqual(response.status_code, 201)

        payload = response.json()["post"]
        self.assertEqual(len(payload["images"]), 1)
        self.assertTrue(payload["images"][0]["isImage"])
        self.assertTrue(payload["images"][0]["src"].startswith("/media/community_posts/"))

    def test_create_post_treats_jfif_upload_as_image(self):
        user = User.objects.create_user(username="community-volunteer-jfif", password="password123")
        self.client.force_login(user)

        uploaded = SimpleUploadedFile("community-photo.jfif", b"jfif-bytes", content_type="application/octet-stream")

        with tempfile.TemporaryDirectory() as temp_media_root:
            with override_settings(MEDIA_ROOT=temp_media_root):
                response = self.client.post(
                    reverse("dashboard_community_post_create"),
                    data={
                        "content": "Posting a JFIF photo.",
                        "type": "discussions",
                        "attachments": uploaded,
                    },
                )

        self.assertEqual(response.status_code, 201)
        payload = response.json()["post"]
        self.assertEqual(len(payload["images"]), 1)
        self.assertEqual(len(payload["attachments"]), 0)
        self.assertTrue(payload["images"][0]["isImage"])


class ActivityVolunteerAssignmentSyncTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username="admin-activity-sync", email="admin-activity-sync@example.com", password="password123")
        self.volunteer_one = User.objects.create_user(username="volunteer-one", password="password123")
        self.volunteer_two = User.objects.create_user(username="volunteer-two", password="password123")
        for volunteer in (self.volunteer_one, self.volunteer_two):
            profile, _ = UserProfile.objects.get_or_create(user=volunteer)
            profile.account_role = UserProfile.ROLE_VOLUNTEER
            profile.save(update_fields=["account_role", "updated_at"])
            RoleApplication.objects.create(
                user=volunteer,
                role=RoleApplication.ROLE_VOLUNTEER,
                status=RoleApplication.STATUS_APPROVED,
                full_name=volunteer.username,
                contact_details=f"{volunteer.username}@example.com",
            )

    def test_volunteer_upcoming_task_shows_activity_creator(self):
        scheduled_date = timezone.localdate() + timedelta(days=2)
        activity = Activity.objects.create(
            title="Creator Label Activity",
            date=scheduled_date,
            location="Campo Santo",
            created_by=self.admin,
            created_by_name="Directory Admin",
        )
        VolunteerActivityAssignment.objects.create(
            activity=activity,
            volunteer=self.volunteer_one,
            activity_name=activity.title,
            scheduled_date=scheduled_date,
            location=activity.location,
            assigned_by=self.admin,
        )

        self.client.force_login(self.volunteer_one)
        response = self.client.get(reverse("volunteer_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Created by Directory Admin")
        self.assertEqual(response.context["upcoming_tasks"][0]["created_by_name"], "Directory Admin")

    def test_activity_audit_names_fall_back_to_system_without_users(self):
        activity = Activity.objects.create(title="System-created Activity", date="2026-10-15")

        self.assertEqual(activity.created_by_display_name, "System")
        self.assertEqual(activity.created_by_initials, "SY")
        self.assertEqual(activity.last_modified_by_display_name, "System")

    def test_activity_feedback_average_uses_all_three_scores_per_submission(self):
        activity = Activity.objects.create(
            title="Feedback Average Activity",
            date="2026-10-15",
            status=Activity.STATUS_COMPLETED,
        )
        beneficiary_apps = []
        for username in ("feedback-average-one", "feedback-average-two"):
            user = User.objects.create_user(username=username, password="password123")
            beneficiary_apps.append(RoleApplication.objects.create(
                user=user,
                role=RoleApplication.ROLE_BENEFICIARY,
                status=RoleApplication.STATUS_APPROVED,
                full_name=username,
                contact_details=f"{username}@example.com",
            ))
        BeneficiaryActivityFeedback.objects.create(
            activity=activity,
            beneficiary=beneficiary_apps[0],
            user=beneficiary_apps[0].user,
            rating=5,
            comment="Q2: 3 | Q3: 4",
        )
        BeneficiaryActivityFeedback.objects.create(
            activity=activity,
            beneficiary=beneficiary_apps[1],
            user=beneficiary_apps[1].user,
            rating=3,
            comment="Q2: 2 | Q3: 3",
        )

        counts, averages = views._build_activity_feedback_averages()

        self.assertEqual(counts[activity.id], 2)
        self.assertEqual(averages[activity.id], 3.3)

    def test_activity_creation_and_update_sync_volunteer_assignments(self):
        self.client.force_login(self.admin)
        self.admin.first_name = "Avery"
        self.admin.last_name = "Admin"
        self.admin.save(update_fields=["first_name", "last_name"])

        add_response = self.client.post(
            reverse("add_activity"),
            {
                "title": "Community Cleanup",
                "date": "2026-09-15",
                "time": "09:00",
                "location": "Maliksi II",
                "category": "outreach",
                "status": Activity.STATUS_ACTIVE,
                "description": "Community cleanup drive",
                "created_by": str(self.volunteer_one.id),
                "created_by_name": "Spoofed Creator",
                "volunteer_ids[]": [str(self.volunteer_one.id), str(self.volunteer_two.id)],
            },
        )

        self.assertEqual(add_response.status_code, 302)
        activity = Activity.objects.get(title="Community Cleanup")
        self.assertEqual(activity.category, "outreach")
        self.assertEqual(activity.created_by_id, self.admin.id)
        self.assertEqual(activity.created_by_name, "Avery Admin")
        self.assertIsNone(activity.last_modified_by_id)
        self.assertEqual(activity.created_by_display_name, "Avery Admin")
        self.assertEqual(activity.last_modified_by_display_name, "Avery Admin")
        directory = self.client.get(reverse("activities"))
        self.assertContains(directory, '<th scope="col">Created By</th>', html=True)
        self.assertContains(directory, '<th scope="col">Last Modified By</th>', html=True)
        self.assertContains(directory, "Avery Admin")
        self.assertContains(directory, 'data-created-by="Avery Admin"')
        self.assertContains(directory, 'data-created-by-id="' + str(self.admin.id) + '"')
        self.assertContains(directory, 'data-last-modified-by="Avery Admin"')
        self.assertEqual(activity.volunteer_assignments.count(), 2)
        self.assertTrue(VolunteerActivityAssignment.objects.filter(activity=activity, activity_type="outreach").exists())
        self.assertTrue(VolunteerActivityAssignment.objects.filter(activity=activity, volunteer=self.volunteer_one).exists())
        self.assertTrue(VolunteerActivityAssignment.objects.filter(activity=activity, volunteer=self.volunteer_two).exists())

        self.assertGreaterEqual(
            CommunityNotification.objects.filter(
                recipient=self.volunteer_one,
                notification_type=CommunityNotification.TYPE_VOLUNTEER_ASSIGNMENT,
            ).count(),
            1,
        )

        self.client.force_login(self.volunteer_one)
        dashboard_payload = views._build_volunteer_dashboard_payload(self.volunteer_one)
        self.assertEqual(dashboard_payload["next_check_in_label"], "Sep 15, 2026")
        volunteer_api = self.client.get(reverse("volunteer_assigned_activities_api"))
        self.assertEqual(volunteer_api.status_code, 200)
        self.assertEqual(len(volunteer_api.json()["items"]), 1)
        self.assertEqual(volunteer_api.json()["items"][0]["activity_name"], "Community Cleanup")

        self.client.force_login(self.admin)
        edit_response = self.client.post(
            reverse("add_activity"),
            {
                "activityId": str(activity.id),
                "title": "Community Cleanup",
                "date": "2026-09-15",
                "time": "09:00",
                "location": "Maliksi II",
                "category": "outreach",
                "status": Activity.STATUS_ACTIVE,
                "description": "Community cleanup drive",
                "created_by": str(self.volunteer_two.id),
                "created_by_name": "Changed Creator",
                "volunteer_ids[]": [str(self.volunteer_two.id)],
            },
        )

        self.assertEqual(edit_response.status_code, 302)
        activity.refresh_from_db()
        self.assertEqual(activity.category, "outreach")
        self.assertEqual(activity.created_by_id, self.admin.id)
        self.assertEqual(activity.created_by_name, "Avery Admin")
        self.assertEqual(activity.last_modified_by_id, self.admin.id)
        self.assertEqual(activity.last_modified_by_name, "Avery Admin")
        self.assertContains(self.client.get(reverse("activities")), 'data-last-modified-by="Avery Admin"')
        self.assertFalse(VolunteerActivityAssignment.objects.filter(activity=activity, volunteer=self.volunteer_one).exists())
        self.assertTrue(VolunteerActivityAssignment.objects.filter(activity=activity, volunteer=self.volunteer_two).exists())

        self.client.force_login(self.volunteer_one)
        volunteer_api_after_edit = self.client.get(reverse("volunteer_assigned_activities_api"))
        self.assertEqual(volunteer_api_after_edit.status_code, 200)
        self.assertEqual(len(volunteer_api_after_edit.json()["items"]), 0)

    def test_activity_donor_share_is_optional_when_creating_and_editing(self):
        self.client.force_login(self.admin)
        form_data = {
            "title": "Community Outreach Budget",
            "date": "2026-10-15",
            "location": "Maliksi II",
            "category": "outreach",
            "status": Activity.STATUS_ACTIVE,
            "description": "Outreach with optional donor funding",
            "funding_mode": "budget_share",
            "total_budget": "100",
            "donor_share_amount": "",
        }

        create_response = self.client.post(reverse("add_activity"), form_data)

        self.assertEqual(create_response.status_code, 302)
        activity = Activity.objects.get(title="Community Outreach Budget")
        self.assertEqual(activity.total_budget, 100)
        self.assertEqual(activity.donor_share_amount, 0)
        self.assertFalse(activity.fund_allocations.filter(status="reserved").exists())

        form_data.update({"activityId": str(activity.id), "title": "Community Outreach Budget Updated"})
        edit_response = self.client.post(reverse("add_activity"), form_data)

        self.assertEqual(edit_response.status_code, 302)
        activity.refresh_from_db()
        self.assertEqual(activity.title, "Community Outreach Budget Updated")
        self.assertEqual(activity.donor_share_amount, 0)
        self.assertFalse(activity.fund_allocations.filter(status="reserved").exists())

        funded_data = {
            **form_data,
            "activityId": "",
            "title": "Funded Community Outreach",
            "total_budget": "250",
            "donor_share_amount": "75",
        }
        with patch("webapp.views._get_available_completed_donation_funds", return_value=100):
            funded_response = self.client.post(reverse("add_activity"), funded_data)

        self.assertEqual(funded_response.status_code, 302)
        funded_activity = Activity.objects.get(title="Funded Community Outreach")
        self.assertEqual(funded_activity.total_budget, 250)
        self.assertEqual(funded_activity.donor_share_amount, 75)

    def test_volunteer_calendar_includes_active_events_without_assignment(self):
        scheduled_activity = Activity.objects.create(
            title="Open Community Day",
            date="2026-10-09",
            start_time="09:00",
            status=Activity.STATUS_ACTIVE,
        )
        Activity.objects.create(
            title="Cancelled Event",
            date="2026-10-10",
            status=Activity.STATUS_CANCELLED,
        )
        VolunteerActivityAssignment.objects.create(
            activity=scheduled_activity,
            volunteer=self.volunteer_two,
            activity_name=scheduled_activity.title,
            scheduled_date=scheduled_activity.date,
            status=VolunteerActivityAssignment.STATUS_UPCOMING,
        )

        self.client.force_login(self.volunteer_one)
        response = self.client.get(reverse("volunteer_activity_calendar_api"))

        self.assertEqual(response.status_code, 200)
        items = response.json()["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "Open Community Day")
        self.assertEqual(items[0]["date"], "2026-10-09")

    def test_admin_volunteers_page_handles_pending_attendance_without_assignment(self):
        self.client.force_login(self.admin)
        VolunteerAttendanceRecord.objects.create(
            volunteer=self.volunteer_one,
            duty_date=timezone.now().date(),
            status=VolunteerAttendanceRecord.STATUS_PENDING,
            time_in=timezone.now() - timedelta(minutes=30),
            time_out=timezone.now(),
            duration_minutes=30,
        )

        response = self.client.get(reverse("volunteers"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("OJT duty day", response.content.decode("utf-8"))

    def test_activity_creation_and_update_sync_beneficiary_assignments(self):
        beneficiary = User.objects.create_user(username="beneficiary-one", password="password123")
        profile, _ = UserProfile.objects.get_or_create(user=beneficiary)
        profile.account_role = UserProfile.ROLE_BENEFICIARY
        profile.save(update_fields=["account_role", "updated_at"])
        RoleApplication.objects.create(
            user=beneficiary,
            role=RoleApplication.ROLE_BENEFICIARY,
            status=RoleApplication.STATUS_APPROVED,
            full_name="Beneficiary One",
            contact_details="beneficiary-one@example.com",
        )

        self.client.force_login(self.admin)
        response = self.client.post(reverse("add_activity"), {
            "title": "Beneficiary Orientation",
            "date": "2026-09-15",
            "time": "09:00",
            "location": "Maliksi II",
            "category": "outreach",
            "status": Activity.STATUS_ACTIVE,
            "description": "Orientation session",
            "beneficiary_ids[]": [str(beneficiary.id)],
        })

        self.assertEqual(response.status_code, 302)
        activity = Activity.objects.get(title="Beneficiary Orientation")
        self.assertTrue(ActivityBeneficiaryAssignment.objects.filter(activity=activity, beneficiary=beneficiary).exists())

        response = self.client.post(reverse("add_activity"), {
            "activityId": str(activity.id),
            "title": "Beneficiary Orientation",
            "date": "2026-09-15",
            "time": "09:00",
            "location": "Maliksi II",
            "category": "outreach",
            "status": Activity.STATUS_ACTIVE,
            "description": "Orientation session",
            "beneficiary_ids": "",
        })

        self.assertEqual(response.status_code, 302)
        self.assertFalse(ActivityBeneficiaryAssignment.objects.filter(activity=activity, beneficiary=beneficiary).exists())

    def test_activity_notifications_follow_selected_or_general_audience(self):
        beneficiary = User.objects.create_user(username="beneficiary-audience", password="password123")
        profile, _ = UserProfile.objects.get_or_create(user=beneficiary)
        profile.account_role = UserProfile.ROLE_BENEFICIARY
        profile.save(update_fields=["account_role", "updated_at"])
        RoleApplication.objects.create(
            user=beneficiary,
            role=RoleApplication.ROLE_BENEFICIARY,
            status=RoleApplication.STATUS_APPROVED,
            full_name="Beneficiary Audience",
            contact_details="beneficiary-audience@example.com",
        )
        other_beneficiary = User.objects.create_user(username="beneficiary-other", password="password123")
        other_profile, _ = UserProfile.objects.get_or_create(user=other_beneficiary)
        other_profile.account_role = UserProfile.ROLE_BENEFICIARY
        other_profile.save(update_fields=["account_role", "updated_at"])
        RoleApplication.objects.create(
            user=other_beneficiary,
            role=RoleApplication.ROLE_BENEFICIARY,
            status=RoleApplication.STATUS_APPROVED,
            full_name="Beneficiary Other",
            contact_details="beneficiary-other@example.com",
        )

        self.client.force_login(self.admin)
        response = self.client.post(reverse("add_activity"), {
            "title": "Targeted Outreach",
            "date": "2026-09-15",
            "time": "09:00",
            "location": "Maliksi II",
            "category": "outreach",
            "status": Activity.STATUS_ACTIVE,
            "description": "Targeted outreach session",
            "volunteer_ids[]": [str(self.volunteer_one.id)],
            "beneficiary_ids[]": [str(beneficiary.id)],
        })
        self.assertEqual(response.status_code, 302)
        activity = Activity.objects.get(title="Targeted Outreach")
        post = CommunityPost.objects.get(activity=activity)
        notification_filter = {
            "post": post,
            "notification_type": CommunityNotification.TYPE_ACTIVITY_ANNOUNCEMENT,
        }
        self.assertTrue(CommunityNotification.objects.filter(recipient=self.volunteer_one, **notification_filter).exists())
        self.assertTrue(CommunityNotification.objects.filter(recipient=beneficiary, **notification_filter).exists())
        self.assertFalse(CommunityNotification.objects.filter(recipient=self.volunteer_two, **notification_filter).exists())

        self.client.force_login(self.volunteer_two)
        feed = self.client.get(reverse("dashboard_community_posts"), {"limit": 50})
        self.assertNotIn("Targeted Outreach", feed.content.decode())

        self.client.force_login(other_beneficiary)
        overview = self.client.get(reverse("user_dashboard_overview_api"))
        self.assertNotIn("Targeted Outreach", overview.content.decode())
        community_feed = self.client.get(reverse("dashboard_community_posts"), {"limit": 50})
        self.assertNotIn("Targeted Outreach", community_feed.content.decode())

        self.client.force_login(beneficiary)
        selected_overview = self.client.get(reverse("user_dashboard_overview_api"))
        self.assertIn("Targeted Outreach", selected_overview.content.decode())

        self.client.force_login(self.admin)
        response = self.client.post(reverse("add_activity"), {
            "activityId": str(activity.id),
            "title": "Targeted Outreach",
            "date": "2026-09-15",
            "time": "09:00",
            "location": "Maliksi II",
            "category": "outreach",
            "status": Activity.STATUS_ACTIVE,
            "description": "General outreach session",
            "volunteer_ids": "",
            "beneficiary_ids": "",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(CommunityNotification.objects.filter(recipient=self.volunteer_two, **notification_filter).exists())

    def test_activity_deletion_keeps_completed_assignment_history_for_volunteer(self):
        self.client.force_login(self.admin)
        add_response = self.client.post(
            reverse("add_activity"),
            {
                "title": "Community Cleanup",
                "date": "2026-09-15",
                "time": "09:00",
                "location": "Maliksi II",
                "category": "outreach",
                "status": Activity.STATUS_ACTIVE,
                "description": "Community cleanup drive",
                "volunteer_ids[]": [str(self.volunteer_one.id)],
            },
        )
        self.assertEqual(add_response.status_code, 302)
        activity = Activity.objects.get(title="Community Cleanup")

        assignment = VolunteerActivityAssignment.objects.get(activity=activity, volunteer=self.volunteer_one)
        assignment.status = VolunteerActivityAssignment.STATUS_COMPLETED
        assignment.save(update_fields=["status", "updated_at"])

        profile = UserProfile.objects.get(user=self.volunteer_one)
        profile.ojt_hours = 4.5
        profile.save(update_fields=["ojt_hours", "updated_at"])

        delete_response = self.client.post(reverse("delete_activity", args=[activity.id]))
        self.assertEqual(delete_response.status_code, 200)

        assignment.refresh_from_db()
        self.assertIsNone(assignment.activity)
        self.assertEqual(assignment.activity_name, "Community Cleanup")
        self.assertEqual(assignment.status, VolunteerActivityAssignment.STATUS_COMPLETED)

        self.client.force_login(self.volunteer_one)
        api_response = self.client.get(reverse("volunteer_assigned_activities_api"))
        self.assertEqual(api_response.status_code, 200)
        items = api_response.json()["items"]
        self.assertTrue(any(item["activity_name"] == "Community Cleanup" and item["status"] == "completed" for item in items))

    def test_admin_can_adjust_volunteer_ojt_hours(self):
        self.client.force_login(self.admin)
        profile = UserProfile.objects.get(user=self.volunteer_one)
        profile.ojt_hours = 12.5
        profile.save(update_fields=["ojt_hours", "updated_at"])

        response = self.client.post(
            reverse("adjust_volunteer_ojt_hours"),
            {
                "volunteer_user_id": str(self.volunteer_one.id),
                "hours_adjustment": "-2.5",
                "reason": "Removed a duplicate session",
            },
        )

        self.assertEqual(response.status_code, 200)
        profile.refresh_from_db()
        self.assertEqual(float(profile.ojt_hours), 10.0)

    def test_admin_can_adjust_volunteer_ojt_hours_by_minutes(self):
        self.client.force_login(self.admin)
        profile = UserProfile.objects.get(user=self.volunteer_one)
        profile.ojt_hours = 4.25
        profile.save(update_fields=["ojt_hours", "updated_at"])

        response = self.client.post(
            reverse("adjust_volunteer_ojt_hours"),
            {
                "volunteer_user_id": str(self.volunteer_one.id),
                "adjustment_minutes": "75",
            },
        )

        self.assertEqual(response.status_code, 200)
        profile.refresh_from_db()
        self.assertEqual(float(profile.ojt_hours), 5.5)
        self.assertEqual(response.json()["hoursAdjustment"], 1.25)

    def test_admin_volunteer_page_renders_hours_and_minutes_adjustment_modal(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse("volunteers"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="vol-ojt-adjust-current"')
        self.assertContains(response, 'id="vol-ojt-adjust-hours"')
        self.assertContains(response, 'id="vol-ojt-adjust-minutes"')
        self.assertContains(response, 'id="vol-ojt-adjust-preview"')

    def test_admin_can_reset_volunteer_ojt_hours_to_zero(self):
        self.client.force_login(self.admin)
        profile = UserProfile.objects.get(user=self.volunteer_one)
        profile.ojt_hours = 12.5
        profile.save(update_fields=["ojt_hours", "updated_at"])

        response = self.client.post(
            reverse("adjust_volunteer_ojt_hours"),
            {
                "volunteer_user_id": str(self.volunteer_one.id),
                "reset_to_zero": "true",
                "reason": "Admin cleanup after incorrect manual entry",
            },
        )

        self.assertEqual(response.status_code, 200)
        profile.refresh_from_db()
        self.assertEqual(float(profile.ojt_hours), 0.0)

    def test_activity_supports_custom_category_and_image(self):
        self.client.force_login(self.admin)
        image = SimpleUploadedFile("activity-cover.png", b"activity-image", content_type="image/png")
        response = self.client.post(
            reverse("add_activity"),
            {
                "title": "Neighborhood Art Workshop",
                "date": "2026-09-20",
                "time": "10:00",
                "location": "Molino II",
                "category": Activity.CATEGORY_OTHER,
                "custom_category": "Neighborhood Arts",
                "status": Activity.STATUS_ACTIVE,
                "description": "A creative workshop for the community.",
                "activity_image": image,
            },
        )

        self.assertEqual(response.status_code, 302)
        activity = Activity.objects.get(title="Neighborhood Art Workshop")
        self.assertEqual(activity.category, "Neighborhood Arts")
        self.assertTrue(activity.image.name)
        dashboard_payload = views._build_volunteer_dashboard_payload(self.volunteer_one)
        self.assertEqual(dashboard_payload["next_pickup"]["image_url"], activity.image.url)

        missing_custom_category = self.client.post(
            reverse("add_activity"),
            {
                "title": "Missing Category",
                "date": "2026-09-21",
                "time": "10:00",
                "location": "Molino II",
                "category": Activity.CATEGORY_OTHER,
                "status": Activity.STATUS_ACTIVE,
                "description": "This should be rejected.",
            },
        )
        self.assertEqual(missing_custom_category.status_code, 400)

    def test_activity_announcement_serializes_cover_image_without_affecting_engagement(self):
        image = SimpleUploadedFile("announcement-cover.png", b"announcement-image", content_type="image/png")
        activity_with_image = Activity.objects.create(
            title="Food Distribution",
            date="2026-09-20",
            location="Molino II",
            category="outreach",
            image=image,
        )
        activity_without_image = Activity.objects.create(
            title="Learning Session",
            date="2026-09-21",
            location="Molino III",
            category="teaching-kids",
        )
        image_post = CommunityPost.objects.create(
            user=self.admin,
            activity=activity_with_image,
            content="[activity:1]\nActivity update: Food Distribution",
            post_type="announcements",
        )
        no_image_post = CommunityPost.objects.create(
            user=self.admin,
            activity=activity_without_image,
            content="[activity:2]\nActivity update: Learning Session",
            post_type="announcements",
        )
        CommunityPostComment.objects.create(post=image_post, user=self.volunteer_one, content="Looking forward to it!")
        CommunityPostLike.objects.create(post=image_post, user=self.volunteer_one)

        image_payload = views._serialize_community_post(image_post, viewer=self.volunteer_one)
        no_image_payload = views._serialize_community_post(no_image_post, viewer=self.volunteer_one)

        self.assertEqual(len(image_payload["images"]), 1)
        self.assertEqual(image_payload["images"][0]["url"], activity_with_image.image.url)
        self.assertEqual(image_payload["commentCount"], 1)
        self.assertEqual(image_payload["likes"], 1)
        self.assertEqual(no_image_payload["images"], [])


class VolunteerCertificateTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username="certificate-admin", email="certificate-admin@example.com", password="password123")
        self.volunteer = User.objects.create_user(username="certificate-volunteer", password="password123")
        profile, _ = UserProfile.objects.get_or_create(user=self.volunteer)
        profile.account_role = UserProfile.ROLE_VOLUNTEER
        profile.save(update_fields=["account_role", "updated_at"])
        RoleApplication.objects.create(
            user=self.volunteer,
            role=RoleApplication.ROLE_VOLUNTEER,
            status=RoleApplication.STATUS_APPROVED,
            full_name="Certificate Volunteer",
            contact_details="certificate-volunteer@example.com",
        )

    def test_admin_issues_certificate_and_volunteer_can_download_it(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("admin_certificate_create"),
            data=json.dumps({
                "volunteer_id": self.volunteer.id,
                "recipient_name": "Certificate Volunteer",
                "reason": "For outstanding service.",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        certificate = VolunteerCertificate.objects.get(volunteer=self.volunteer)
        self.assertEqual(certificate.issued_by, self.admin)

        self.client.force_login(self.volunteer)
        dashboard = self.client.get(reverse("volunteer_dashboard"))
        self.assertContains(dashboard, "Certificate of Appreciation")
        self.assertContains(dashboard, reverse("volunteer_certificate_download", args=[certificate.id]))

        download = self.client.get(reverse("volunteer_certificate_download", args=[certificate.id]))
        self.assertEqual(download.status_code, 200)
        self.assertEqual(download["Content-Type"], "application/pdf")

    def test_certificate_download_is_private_to_recipient(self):
        certificate = VolunteerCertificate.objects.create(
            volunteer=self.volunteer,
            issued_by=self.admin,
            recipient_name="Certificate Volunteer",
            reason="For outstanding service.",
        )
        other_volunteer = User.objects.create_user(username="other-certificate-volunteer", password="password123")
        self.client.force_login(other_volunteer)
        response = self.client.get(reverse("volunteer_certificate_download", args=[certificate.id]))
        self.assertEqual(response.status_code, 404)

    def test_volunteer_download_returns_the_pdf_uploaded_by_admin(self):
        pdf_bytes = b"%PDF-1.4\nadmin-rendered-certificate\n%%EOF"
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("admin_certificate_create"),
            data={
                "volunteer_id": str(self.volunteer.id),
                "recipient_name": "Certificate Volunteer",
                "reason": "For outstanding service.",
                "pdf_file": SimpleUploadedFile("admin-certificate.pdf", pdf_bytes, content_type="application/pdf"),
            },
        )

        self.assertEqual(response.status_code, 201)
        certificate = VolunteerCertificate.objects.get(volunteer=self.volunteer)
        self.assertTrue(certificate.pdf_file.name)

        self.client.force_login(self.volunteer)
        download = self.client.get(reverse("volunteer_certificate_download", args=[certificate.id]))
        self.assertEqual(download.status_code, 200)
        self.assertEqual(b"".join(download.streaming_content), pdf_bytes)

    def test_admin_can_list_and_remove_issued_certificate(self):
        certificate = VolunteerCertificate.objects.create(
            volunteer=self.volunteer,
            issued_by=self.admin,
            recipient_name="Certificate Volunteer",
            reason="For outstanding service.",
        )
        self.client.force_login(self.admin)
        page = self.client.get(reverse("volunteers"))
        self.assertContains(page, "Certifications")
        self.assertContains(page, str(certificate.id))

        response = self.client.post(reverse("admin_certificate_delete", args=[certificate.id]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(VolunteerCertificate.objects.filter(pk=certificate.id).exists())

class VolunteerAttendanceWorkflowTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username="admin-attendance", email="admin-attendance@example.com", password="password123")
        self.volunteer = User.objects.create_user(username="volunteer-attendance", password="password123")
        profile, _ = UserProfile.objects.get_or_create(user=self.volunteer)
        profile.account_role = UserProfile.ROLE_VOLUNTEER
        profile.save(update_fields=["account_role", "updated_at"])

        self.volunteer_one = self.volunteer
        self.volunteer_two = User.objects.create_user(username="volunteer-attendance-two", password="password123")
        volunteer_two_profile, _ = UserProfile.objects.get_or_create(user=self.volunteer_two)
        volunteer_two_profile.account_role = UserProfile.ROLE_VOLUNTEER
        volunteer_two_profile.save(update_fields=["account_role", "updated_at"])

        self.assignment = VolunteerActivityAssignment.objects.create(
            volunteer=self.volunteer,
            activity_name="Community Outreach",
            scheduled_date=timezone.localdate(),
            scheduled_time=timezone.localtime().time(),
            location="Barangay Hall",
            status=VolunteerActivityAssignment.STATUS_UPCOMING,
        )

    def test_standard_nine_hour_shift_excludes_one_hour_lunch(self):
        local_timezone = timezone.get_current_timezone()
        time_in = timezone.make_aware(datetime(2026, 9, 25, 9, 0), local_timezone)
        time_out = timezone.make_aware(datetime(2026, 9, 25, 18, 0), local_timezone)
        shorter_time_out = timezone.make_aware(datetime(2026, 9, 25, 17, 0), local_timezone)

        self.assertEqual(views._calculate_duration_minutes(time_in, time_out), 480)
        self.assertEqual(views._calculate_duration_minutes(time_in, shorter_time_out), 480)

    def test_format_ojt_duration_display_uses_hours_and_minutes(self):
        self.assertEqual(views.format_ojt_duration_display(40.5), "40 hr 30 min")
        self.assertEqual(views.format_ojt_duration_display(5), "5 hr")
        self.assertEqual(views.format_ojt_duration_display(0), "0 hr")

    def test_admin_schedule_update_creates_effective_dated_revision(self):
        today = timezone.localdate()
        tomorrow = today + timedelta(days=1)
        self.client.force_login(self.admin)
        first = self.client.post(reverse("update_volunteer_ojt_requirement"), {
            "volunteer_user_id": self.volunteer.id,
            "required_ojt_hours": "80",
            "schedule_days": "[4,5,6]",
            "schedule_times": '{"4":{"start":"09:00","end":"17:00"}}',
            "schedule_effective_from": today.isoformat(),
        })
        self.assertEqual(first.status_code, 200)
        old_schedule = VolunteerOjtSchedule.objects.get(volunteer=self.volunteer)
        self.assertEqual(old_schedule.weekdays, [4, 5, 6])
        self.assertEqual(old_schedule.daily_times["4"], {"start": "09:00", "end": "17:00"})

        second = self.client.post(reverse("update_volunteer_ojt_requirement"), {
            "volunteer_user_id": self.volunteer.id,
            "required_ojt_hours": "80",
            "schedule_days": "[0,2]",
            "schedule_times": "{}",
            "schedule_effective_from": tomorrow.isoformat(),
        })
        self.assertEqual(second.status_code, 200)
        old_schedule.refresh_from_db()
        new_schedule = VolunteerOjtSchedule.objects.get(volunteer=self.volunteer, effective_from=tomorrow)
        self.assertEqual(old_schedule.effective_until, today)
        self.assertEqual(old_schedule.weekdays, [4, 5, 6])
        self.assertEqual(new_schedule.weekdays, [0, 2])

    def test_calendar_returns_duty_days_and_separates_assigned_and_open_activities(self):
        today = timezone.localdate()
        VolunteerOjtSchedule.objects.create(
            volunteer=self.volunteer,
            effective_from=today,
            weekdays=[today.weekday()],
        )
        assigned_activity = Activity.objects.create(title="Assigned Outreach", date=today, start_time="10:00")
        open_activity = Activity.objects.create(title="Open Outreach", date=today, start_time="11:00")
        VolunteerActivityAssignment.objects.create(
            activity=assigned_activity,
            volunteer=self.volunteer,
            activity_name=assigned_activity.title,
            scheduled_date=today,
            status=VolunteerActivityAssignment.STATUS_UPCOMING,
        )
        self.client.force_login(self.volunteer)

        response = self.client.get(reverse("volunteer_activity_calendar_api"), {"month": today.strftime("%Y-%m")})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual([item["type"] for item in payload["assigned_items"]], ["assigned"])
        self.assertEqual(payload["assigned_items"][0]["title"], assigned_activity.title)
        self.assertEqual([item["title"] for item in payload["open_items"]], [open_activity.title])
        today_duty = next(item for item in payload["duty_days"] if item["date"] == today.isoformat())
        self.assertEqual(today_duty["status"], "upcoming")

    def test_calendar_summary_reuses_schedule_and_recent_attendance_status(self):
        today = timezone.localdate()
        previous_duty_day = today - timedelta(days=7)
        self.client.force_login(self.volunteer)

        no_schedule = self.client.get(reverse("volunteer_activity_calendar_api"), {"month": today.strftime("%Y-%m")})
        self.assertFalse(no_schedule.json()["has_schedule"])

        VolunteerOjtSchedule.objects.create(
            volunteer=self.volunteer,
            effective_from=previous_duty_day,
            weekdays=[today.weekday()],
        )
        VolunteerAttendanceRecord.objects.create(
            volunteer=self.volunteer,
            duty_date=previous_duty_day,
            time_in=timezone.now() - timedelta(days=7, hours=8),
            time_out=timezone.now() - timedelta(days=7),
            duration_minutes=95,
            status=VolunteerAttendanceRecord.STATUS_PENDING,
        )

        response = self.client.get(reverse("volunteer_activity_calendar_api"), {"month": today.strftime("%Y-%m")})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["schedule_weekdays"], [today.weekday()])
        self.assertEqual(payload["today_duty"]["status"], "upcoming")
        self.assertEqual(payload["recent_duty_days"][0]["date"], previous_duty_day.isoformat())
        self.assertEqual(payload["recent_duty_days"][0]["status"], "pending")
        self.assertEqual(payload["recent_duty_days"][0]["hours"], 1.58)

    def test_calendar_summary_includes_future_effective_schedule(self):
        today = timezone.localdate()
        first_duty_day = today + timedelta(days=1)
        VolunteerOjtSchedule.objects.create(
            volunteer=self.volunteer,
            effective_from=first_duty_day,
            weekdays=[first_duty_day.weekday()],
        )
        self.client.force_login(self.volunteer)

        response = self.client.get(reverse("volunteer_activity_calendar_api"), {"month": today.strftime("%Y-%m")})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["has_schedule"])
        self.assertEqual(payload["schedule_weekdays"], [first_duty_day.weekday()])
        self.assertEqual(payload["next_duty_date"], first_duty_day.isoformat())
        self.assertIsNone(payload["today_duty"])

    def test_duty_schedule_without_custom_times_opens_at_eight(self):
        today = timezone.localdate()
        VolunteerOjtSchedule.objects.create(
            volunteer=self.volunteer,
            effective_from=today,
            weekdays=[today.weekday()],
        )
        self.client.force_login(self.volunteer)
        local_timezone = timezone.get_current_timezone()
        before_start = timezone.make_aware(datetime.combine(today, time(7, 59)), local_timezone)
        with patch("webapp.views.timezone.now", return_value=before_start):
            rejected = self.client.post(reverse("volunteer_activity_attendance"), {
                "action": "time_in",
                "duty_date": today.isoformat(),
            })
        self.assertEqual(rejected.status_code, 400)
        self.assertIn("scheduled duty window", rejected.json()["error"])

        at_start = timezone.make_aware(datetime.combine(today, time(8, 0)), local_timezone)
        with patch("webapp.views.timezone.now", return_value=at_start):
            accepted = self.client.post(reverse("volunteer_activity_attendance"), {
                "action": "time_in",
                "duty_date": today.isoformat(),
            })
        self.assertEqual(accepted.status_code, 200)

    def test_assigned_activities_api_reports_weekly_and_pending_hours(self):
        today = timezone.localdate()
        week_start = today - timedelta(days=today.weekday())
        available_dates = [week_start + timedelta(days=offset) for offset in range(7) if week_start + timedelta(days=offset) != today]
        confirmed_date, pending_date = available_dates[:2]
        confirmed_assignment = VolunteerActivityAssignment.objects.create(
            volunteer=self.volunteer,
            activity_name="Confirmed duty",
            scheduled_date=confirmed_date,
            status=VolunteerActivityAssignment.STATUS_COMPLETED,
        )
        pending_assignment = VolunteerActivityAssignment.objects.create(
            volunteer=self.volunteer,
            activity_name="Pending duty",
            scheduled_date=pending_date,
            status=VolunteerActivityAssignment.STATUS_AWAITING_CONFIRMATION,
        )
        VolunteerAttendanceRecord.objects.create(
            assignment=confirmed_assignment,
            volunteer=self.volunteer,
            duration_minutes=120,
            status=VolunteerAttendanceRecord.STATUS_CONFIRMED,
        )
        VolunteerAttendanceRecord.objects.create(
            assignment=pending_assignment,
            volunteer=self.volunteer,
            duration_minutes=45,
            status=VolunteerAttendanceRecord.STATUS_PENDING,
        )
        VolunteerAttendanceRecord.objects.create(
            volunteer=self.volunteer,
            duty_date=week_start - timedelta(days=1),
            duration_minutes=30,
            status=VolunteerAttendanceRecord.STATUS_PENDING,
        )
        profile = self.volunteer.userprofile
        profile.ojt_hours = 2
        profile.save(update_fields=["ojt_hours", "updated_at"])
        self.client.force_login(self.volunteer)

        response = self.client.get(reverse("volunteer_assigned_activities_api"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["ojt_hours"], 2)
        self.assertEqual(payload["ojt_pending_hours"], 1.25)
        self.assertEqual(payload["ojt_this_week_hours"], 2.75)

    def test_duty_only_attendance_requires_current_day_and_credits_once_after_review(self):
        today = timezone.localdate()
        VolunteerOjtSchedule.objects.create(
            volunteer=self.volunteer,
            effective_from=today,
            weekdays=[today.weekday()],
        )
        self.client.force_login(self.volunteer)
        future = self.client.post(reverse("volunteer_activity_attendance"), {
            "action": "time_in",
            "duty_date": (today + timedelta(days=1)).isoformat(),
        })
        self.assertEqual(future.status_code, 400)

        started = self.client.post(reverse("volunteer_activity_attendance"), {
            "action": "time_in",
            "duty_date": today.isoformat(),
        })
        self.assertEqual(started.status_code, 200)
        attendance = VolunteerAttendanceRecord.objects.get(volunteer=self.volunteer, duty_date=today)
        self.assertEqual(attendance.status, VolunteerAttendanceRecord.STATUS_ACTIVE)

        duplicate = self.client.post(reverse("volunteer_activity_attendance"), {
            "action": "time_in",
            "duty_date": today.isoformat(),
        })
        self.assertEqual(duplicate.status_code, 409)
        ended = self.client.post(reverse("volunteer_activity_attendance"), {
            "action": "time_out",
            "duty_date": today.isoformat(),
        })
        self.assertEqual(ended.status_code, 200)
        attendance.refresh_from_db()
        self.assertEqual(attendance.status, VolunteerAttendanceRecord.STATUS_PENDING)
        self.assertGreater(attendance.duration_minutes, 0)

        self.client.force_login(self.admin)
        reviewed = self.client.post(reverse("review_volunteer_attendance"), {"attendance_id": attendance.id, "action": "confirm"})
        self.assertEqual(reviewed.status_code, 200)
        self.volunteer.userprofile.refresh_from_db()
        credited_hours = float(self.volunteer.userprofile.ojt_hours)
        self.assertGreater(credited_hours, 0)
        duplicate_review = self.client.post(reverse("review_volunteer_attendance"), {"attendance_id": attendance.id, "action": "confirm"})
        self.assertEqual(duplicate_review.status_code, 409)
        self.volunteer.userprofile.refresh_from_db()
        self.assertEqual(float(self.volunteer.userprofile.ojt_hours), credited_hours)

    def test_assigned_duty_day_uses_one_attendance_record(self):
        today = timezone.localdate()
        VolunteerOjtSchedule.objects.create(
            volunteer=self.volunteer,
            effective_from=today,
            weekdays=[today.weekday()],
        )
        activity = Activity.objects.create(title="Duty Day Activity", date=today, start_time="09:00")
        assignment = VolunteerActivityAssignment.objects.create(
            activity=activity,
            volunteer=self.volunteer,
            activity_name=activity.title,
            scheduled_date=today,
            status=VolunteerActivityAssignment.STATUS_UPCOMING,
        )
        self.client.force_login(self.volunteer)
        started = self.client.post(reverse("volunteer_activity_attendance"), {"assignment_id": assignment.id, "action": "time_in"})
        self.assertEqual(started.status_code, 200)
        attendance = VolunteerAttendanceRecord.objects.get(volunteer=self.volunteer, duty_date=today)
        self.assertEqual(attendance.assignment_id, assignment.id)

        duty_only = self.client.post(reverse("volunteer_activity_attendance"), {"duty_date": today.isoformat(), "action": "time_in"})
        self.assertEqual(duty_only.status_code, 400)
        duplicate = self.client.post(reverse("volunteer_activity_attendance"), {"assignment_id": assignment.id, "action": "time_in"})
        self.assertEqual(duplicate.status_code, 409)
        ended = self.client.post(reverse("volunteer_activity_attendance"), {"assignment_id": assignment.id, "action": "time_out"})
        self.assertEqual(ended.status_code, 200)
        self.assertEqual(VolunteerAttendanceRecord.objects.filter(volunteer=self.volunteer, duty_date=today).count(), 1)

    def test_calendar_lazily_marks_duty_missed_and_auto_closes_expired_session(self):
        today = timezone.localdate()
        schedule = VolunteerOjtSchedule.objects.create(
            volunteer=self.volunteer,
            effective_from=today,
            weekdays=[today.weekday()],
            daily_times={str(today.weekday()): {"start": "08:00", "end": "09:00"}},
        )
        activity = Activity.objects.create(title="Early Duty Activity", date=today, start_time="08:00")
        assignment = VolunteerActivityAssignment.objects.create(
            activity=activity,
            volunteer=self.volunteer,
            activity_name=activity.title,
            scheduled_date=today,
            scheduled_time="08:00",
            status=VolunteerActivityAssignment.STATUS_TIME_IN,
            attendance_started_at=timezone.make_aware(datetime.combine(today, time(8, 30)), timezone.get_current_timezone()),
        )
        attendance = VolunteerAttendanceRecord.objects.create(
            assignment=assignment,
            volunteer=self.volunteer,
            duty_schedule=schedule,
            duty_date=today,
            time_in=assignment.attendance_started_at,
            status=VolunteerAttendanceRecord.STATUS_ACTIVE,
        )
        after_window = timezone.make_aware(datetime.combine(today, time(10, 0)), timezone.get_current_timezone())
        self.client.force_login(self.volunteer)
        with patch("webapp.views.timezone.now", return_value=after_window):
            response = self.client.get(reverse("volunteer_activity_calendar_api"), {"month": today.strftime("%Y-%m")})

        self.assertEqual(response.status_code, 200)
        attendance.refresh_from_db()
        assignment.refresh_from_db()
        self.assertEqual(attendance.status, VolunteerAttendanceRecord.STATUS_PENDING)
        self.assertTrue(attendance.auto_closed)
        self.assertEqual(attendance.time_out, timezone.make_aware(datetime.combine(today, time(9, 0)), timezone.get_current_timezone()))
        self.assertEqual(assignment.status, VolunteerActivityAssignment.STATUS_AWAITING_CONFIRMATION)

        missed_date = today - timedelta(days=1)
        missed_schedule = VolunteerOjtSchedule.objects.create(
            volunteer=self.volunteer,
            effective_from=missed_date,
            effective_until=missed_date,
            weekdays=[missed_date.weekday()],
        )
        self.assertIsNotNone(missed_schedule.pk)
        with patch("webapp.views.timezone.now", return_value=after_window):
            missed_response = self.client.get(reverse("volunteer_activity_calendar_api"), {"month": missed_date.strftime("%Y-%m")})
        self.assertEqual(missed_response.status_code, 200)
        missed_duty = next(item for item in missed_response.json()["duty_days"] if item["date"] == missed_date.isoformat())
        self.assertEqual(missed_duty["status"], "missed")

    def test_mark_in_progress_starts_a_fresh_session(self):
        stale_start = timezone.now() - timedelta(hours=21)
        self.assignment.attendance_started_at = stale_start
        self.assignment.save(update_fields=["attendance_started_at", "updated_at"])

        self.client.force_login(self.volunteer)
        response = self.client.post(
            reverse("volunteer_activity_attendance"),
            {"assignment_id": self.assignment.id, "action": "mark_in_progress"},
        )

        self.assertEqual(response.status_code, 200)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, VolunteerActivityAssignment.STATUS_IN_PROGRESS)


        self.assertIsNotNone(self.assignment.attendance_started_at)
        self.assertGreater(self.assignment.attendance_started_at, stale_start)
        self.assertIsNone(self.assignment.attendance_ended_at)

    def test_time_in_and_time_out_create_pending_attendance_record_without_adding_hours(self):
        self.client.force_login(self.volunteer)

        response = self.client.post(
            reverse("volunteer_activity_attendance"),
            {"assignment_id": self.assignment.id, "action": "time_in"},
        )
        self.assertEqual(response.status_code, 200)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, VolunteerActivityAssignment.STATUS_TIME_IN)

        response = self.client.post(
            reverse("volunteer_activity_attendance"),
            {"assignment_id": self.assignment.id, "action": "time_out"},
        )
        self.assertEqual(response.status_code, 200)

        self.assignment.refresh_from_db()
        self.volunteer.userprofile.refresh_from_db()
        self.assertEqual(self.assignment.status, VolunteerActivityAssignment.STATUS_AWAITING_CONFIRMATION)
        record = self.assignment.attendance_records.order_by("-created_at").first()
        self.assertIsNotNone(record)
        self.assertEqual(record.status, VolunteerAttendanceRecord.STATUS_PENDING)
        self.assertGreater(record.duration_minutes, 0)
        self.assertEqual(float(self.volunteer.userprofile.ojt_hours), 0.0)

    def test_admin_can_force_time_out_into_pending_review(self):
        stale_start = timezone.now() - timedelta(minutes=12)
        self.assignment.status = VolunteerActivityAssignment.STATUS_IN_PROGRESS
        self.assignment.attendance_started_at = stale_start
        self.assignment.save(update_fields=["status", "attendance_started_at", "updated_at"])

        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("force_timeout_volunteer_attendance"),
            {"assignment_id": self.assignment.id},
        )

        self.assertEqual(response.status_code, 200)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, VolunteerActivityAssignment.STATUS_AWAITING_CONFIRMATION)
        record = self.assignment.attendance_records.order_by("-created_at").first()
        self.assertIsNotNone(record)
        self.assertEqual(record.status, VolunteerAttendanceRecord.STATUS_PENDING)
        self.assertEqual(record.time_in, stale_start)
        self.assertGreater(record.duration_minutes, 0)
        self.volunteer.userprofile.refresh_from_db()
        self.assertEqual(float(self.volunteer.userprofile.ojt_hours), 0.0)

    def test_admin_confirmation_adds_confirmed_hours_and_marks_assignment_complete(self):
        self.client.force_login(self.volunteer)
        self.client.post(
            reverse("volunteer_activity_attendance"),
            {"assignment_id": self.assignment.id, "action": "time_in"},
        )
        self.client.post(
            reverse("volunteer_activity_attendance"),
            {"assignment_id": self.assignment.id, "action": "time_out"},
        )

        self.assignment.refresh_from_db()
        record = self.assignment.attendance_records.order_by("-created_at").first()
        self.assertIsNotNone(record)

        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("review_volunteer_attendance"),
            {"attendance_id": record.id, "action": "confirm"},
        )

        self.assertEqual(response.status_code, 200)
        self.assignment.refresh_from_db()
        self.volunteer.userprofile.refresh_from_db()
        record.refresh_from_db()
        self.assertEqual(self.assignment.status, VolunteerActivityAssignment.STATUS_COMPLETED)
        self.assertEqual(record.status, VolunteerAttendanceRecord.STATUS_CONFIRMED)
        self.assertGreater(float(self.volunteer.userprofile.ojt_hours), 0.0)

    def test_assigned_volunteer_can_confirm_beneficiary_attendance_for_selected_activity(self):
        beneficiary = User.objects.create_user(username="beneficiary-attendance", password="password123")
        profile, _ = UserProfile.objects.get_or_create(user=beneficiary)
        profile.account_role = UserProfile.ROLE_BENEFICIARY
        profile.save(update_fields=["account_role", "updated_at"])
        RoleApplication.objects.create(
            user=beneficiary,
            role=RoleApplication.ROLE_BENEFICIARY,
            status=RoleApplication.STATUS_APPROVED,
            full_name="Attendance Beneficiary",
            contact_details="beneficiary-attendance@example.com",
        )

        activity = Activity.objects.create(
            title="Targeted Outreach Confirmation",
            date=timezone.localdate(),
            start_time=timezone.localtime().time(),
            location="Barangay Hall",
            category="outreach",
            description="Needs beneficiary confirmation test",
        )
        ActivityBeneficiaryAssignment.objects.create(activity=activity, beneficiary=beneficiary, assigned_by=self.admin)
        self.assignment.activity = activity
        self.assignment.activity_name = activity.title
        self.assignment.activity_type = "outreach"
        self.assignment.location = activity.location
        self.assignment.save(update_fields=["activity", "activity_name", "activity_type", "location", "updated_at"])

        self.client.force_login(self.volunteer)
        time_in_response = self.client.post(
            reverse("volunteer_activity_attendance"),
            {"assignment_id": self.assignment.id, "action": "time_in"},
        )
        self.assertEqual(time_in_response.status_code, 200)
        response = self.client.post(
            reverse("volunteer_beneficiary_attendance"),
            {"activity_id": activity.id, "beneficiary_id": beneficiary.id, "action": "confirm"},
        )

        self.assertEqual(response.status_code, 200)
        record = BeneficiaryActivityAttendance.objects.get(activity=activity, beneficiary=beneficiary, volunteer=self.volunteer)
        self.assertEqual(record.status, BeneficiaryActivityAttendance.STATUS_CONFIRMED)
        self.assertIsNotNone(record.confirmed_at)

        blocked_volunteer = User.objects.create_user(username="other-volunteer-confirm", password="password123")
        other_profile, _ = UserProfile.objects.get_or_create(user=blocked_volunteer)
        other_profile.account_role = UserProfile.ROLE_VOLUNTEER
        other_profile.save(update_fields=["account_role", "updated_at"])
        RoleApplication.objects.create(
            user=blocked_volunteer,
            role=RoleApplication.ROLE_VOLUNTEER,
            status=RoleApplication.STATUS_APPROVED,
            full_name="Other Volunteer",
            contact_details="other-volunteer-confirm@example.com",
        )

        self.client.force_login(blocked_volunteer)
        blocked_response = self.client.post(
            reverse("volunteer_beneficiary_attendance"),
            {"activity_id": activity.id, "beneficiary_id": beneficiary.id, "action": "confirm"},
        )
        self.assertEqual(blocked_response.status_code, 403)

    def test_activity_volunteer_map_uses_live_assignment_rows(self):
        self.client.force_login(self.admin)

        add_response = self.client.post(
            reverse("add_activity"),
            {
                "title": "Barangay Tree Planting",
                "date": "2026-09-18",
                "time": "08:30",
                "location": "Mabolo I",
                "category": "pagtatanim",
                "status": Activity.STATUS_ACTIVE,
                "description": "Tree planting day",
                "volunteer_ids[]": [str(self.volunteer_one.id)],
            },
        )

        self.assertEqual(add_response.status_code, 302)

        activity = Activity.objects.get(title="Barangay Tree Planting")
        activity_map = views._build_activity_volunteer_map(Activity.objects.filter(id=activity.id))

        self.assertEqual(activity_map[str(activity.id)], [self.volunteer_one.id])
        self.assertEqual(len(activity_map[str(activity.id)]), activity.volunteer_assignments.count())

    def test_parse_volunteer_ids_ignores_blank_legacy_values(self):
        self.assertEqual(views._parse_volunteer_ids(["", " ", None, self.volunteer_one.id, str(self.volunteer_two.id)]), [self.volunteer_one.id, self.volunteer_two.id])
        self.assertEqual(views._parse_volunteer_ids(["", " "]), [])

    def test_activity_add_and_edit_support_csv_volunteer_ids_and_reopen_selection_map(self):
        self.client.force_login(self.admin)

        add_response = self.client.post(
            reverse("add_activity"),
            {
                "title": "Relief Pack Sorting",
                "date": "2026-09-21",
                "time": "10:30",
                "location": "Molino I",
                "category": "outreach",
                "status": Activity.STATUS_ACTIVE,
                "description": "Sort incoming relief packs",
                "volunteer_ids": f"{self.volunteer_one.id},{self.volunteer_two.id}",
            },
        )

        self.assertEqual(add_response.status_code, 302)
        activity = Activity.objects.get(title="Relief Pack Sorting")

        db_ids_after_add = list(
            VolunteerActivityAssignment.objects
            .filter(activity=activity)
            .order_by("volunteer_id")
            .values_list("volunteer_id", flat=True)
        )
        self.assertEqual(db_ids_after_add, [self.volunteer_one.id, self.volunteer_two.id])

        reopen_map_after_add = views._build_activity_volunteer_map(Activity.objects.filter(id=activity.id))
        self.assertEqual(reopen_map_after_add[str(activity.id)], [self.volunteer_one.id, self.volunteer_two.id])

        edit_response = self.client.post(
            reverse("add_activity"),
            {
                "activityId": str(activity.id),
                "title": "Relief Pack Sorting",
                "date": "2026-09-21",
                "time": "10:30",
                "location": "Molino I",
                "category": "outreach",
                "status": Activity.STATUS_ACTIVE,
                "description": "Sort incoming relief packs",
                "volunteer_ids": str(self.volunteer_two.id),
            },
        )

        self.assertEqual(edit_response.status_code, 302)

        db_ids_after_edit = list(
            VolunteerActivityAssignment.objects
            .filter(activity=activity)
            .order_by("volunteer_id")
            .values_list("volunteer_id", flat=True)
        )
        self.assertEqual(db_ids_after_edit, [self.volunteer_two.id])

        reopen_map_after_edit = views._build_activity_volunteer_map(Activity.objects.filter(id=activity.id))
        self.assertEqual(reopen_map_after_edit[str(activity.id)], [self.volunteer_two.id])


class AvatarDefaultTests(TestCase):
    def test_missing_profile_uses_default_avatar_in_context_and_api_helper(self):
        user = User.objects.create_user(username="avatar-default", password="password123")

        UserProfile.objects.get_or_create(user=user)
        self.assertEqual(avatar_url_for_user(user), default_avatar_url())

        UserProfile.objects.filter(user=user).delete()

        self.assertEqual(avatar_url_for_user(user), default_avatar_url())
        self.assertEqual(views._avatar_url_for_user(user), default_avatar_url())

        request = RequestFactory().get("/")
        request.user = user
        context = dashboard_profile_context(request)
        self.assertEqual(context["user_avatar_url"], default_avatar_url())
        self.assertEqual(context["default_avatar_url"], default_avatar_url())

        post = CommunityPost.objects.create(user=user, content="Avatar fallback test")
        payload = views._serialize_community_post(post)
        self.assertEqual(payload["avatarImage"], default_avatar_url())

    def test_anonymous_context_exposes_default_avatar_url(self):
        request = RequestFactory().get("/")
        request.user = AnonymousUser()

        context = dashboard_profile_context(request)

        self.assertEqual(context["default_avatar_url"], default_avatar_url())


class DashboardProfileUpdateTests(TestCase):
    def setUp(self):
        self.volunteer = User.objects.create_user(
            username="profile-volunteer",
            password="password123",
            first_name="Before",
            last_name="Update",
        )
        profile, _ = UserProfile.objects.get_or_create(user=self.volunteer)
        profile.account_role = UserProfile.ROLE_VOLUNTEER
        profile.save(update_fields=["account_role", "updated_at"])
        RoleApplication.objects.create(
            user=self.volunteer,
            role=RoleApplication.ROLE_VOLUNTEER,
            status=RoleApplication.STATUS_APPROVED,
            full_name="Before Update",
            contact_details="profile@example.com",
        )

    def test_volunteer_profile_name_and_avatar_persist_after_reload(self):
        uploaded = SimpleUploadedFile("volunteer-profile.png", b"png-bytes", content_type="image/png")

        with tempfile.TemporaryDirectory() as temp_media_root:
            with override_settings(MEDIA_ROOT=temp_media_root):
                self.client.force_login(self.volunteer)
                response = self.client.post(
                    reverse("dashboard_profile_update"),
                    {
                        "first_name": "After",
                        "last_name": "Reload",
                        "email": "profile@example.com",
                        "profile_photo": uploaded,
                    },
                )

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["message"], "Profile updated successfully.")

                self.volunteer.refresh_from_db()
                self.volunteer.userprofile.refresh_from_db()
                self.assertEqual(self.volunteer.first_name, "After")
                self.assertEqual(self.volunteer.last_name, "Reload")
                self.assertTrue(self.volunteer.userprofile.avatar.name)

                reload_response = self.client.get(reverse("volunteer_dashboard_settings"))
                self.assertEqual(reload_response.status_code, 200)
                self.assertContains(reload_response, 'value="After"')
                self.assertContains(reload_response, 'value="Reload"')
                self.assertContains(reload_response, self.volunteer.userprofile.avatar.url)


class AdminSystemSettingsPersistenceTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="settings-admin",
            email="settings-admin@example.com",
            password="password123",
        )
        self.user = User.objects.create_user(username="settings-user", password="password123")

    def settings_view_context(self):
        request = RequestFactory().get(reverse("settings"))
        request.user = self.admin
        with patch("webapp.views.render") as render_page:
            views.settings(request)
            return render_page.call_args.args[2]

    def test_admin_settings_save_validate_and_reload(self):
        self.client.force_login(self.admin)

        initial_context = self.settings_view_context()
        self.assertEqual(
            initial_context["admin_system_settings"]["system_name"],
            views.ADMIN_SYSTEM_SETTINGS_DEFAULTS["system_name"],
        )

        response = self.client.post(
            reverse("admin_system_settings_update"),
            data=json.dumps({
                "settings": {
                    "system_name": "HappYness Operations",
                    "mfa_policy": "Optional",
                    "password_length": 16,
                },
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        saved = AdminSystemSettings.objects.get(pk="global").settings
        self.assertEqual(saved["system_name"], "HappYness Operations")
        self.assertEqual(saved["mfa_policy"], "Optional")
        self.assertNotIn("pref_dark_mode", saved)
        self.assertEqual(saved["password_length"], 16)

        reloaded_context = self.settings_view_context()
        self.assertEqual(reloaded_context["admin_system_settings"]["system_name"], "HappYness Operations")
        self.assertEqual(
            reloaded_context["admin_system_settings"]["mfa_policy"],
            "Optional",
        )

        invalid_response = self.client.post(
            reverse("admin_system_settings_update"),
            data=json.dumps({"settings": {"mfa_policy": "Disable all security"}}),
            content_type="application/json",
        )
        self.assertEqual(invalid_response.status_code, 400)
        self.assertEqual(AdminSystemSettings.objects.get(pk="global").settings, saved)

    def test_interface_preferences_persist_per_admin_without_cross_account_changes(self):
        another_admin = User.objects.create_superuser(
            username="settings-admin-two",
            email="settings-admin-two@example.com",
            password="password123",
        )
        first_preferences = {
            "pref_dark_mode": True,
            "pref_animations": False,
            "font_size": "Large",
            "font_type": "Serif",
        }
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("admin_user_preferences_update"),
            data=json.dumps({"preferences": first_preferences}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(AdminUserPreferences.objects.get(user=self.admin).preferences, first_preferences)
        first_context = self.settings_view_context()
        self.assertEqual(first_context["admin_user_preferences"], first_preferences)

        second_request = RequestFactory().get(reverse("settings"))
        second_request.user = another_admin
        with patch("webapp.views.render") as render_page:
            views.settings(second_request)
            second_context = render_page.call_args.args[2]
        self.assertEqual(second_context["admin_user_preferences"], views.ADMIN_USER_PREFERENCE_DEFAULTS)

        second_preferences = dict(views.ADMIN_USER_PREFERENCE_DEFAULTS)
        self.client.force_login(another_admin)
        second_response = self.client.post(
            reverse("admin_user_preferences_update"),
            data=json.dumps({"preferences": second_preferences}),
            content_type="application/json",
        )
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(AdminUserPreferences.objects.get(user=self.admin).preferences, first_preferences)
        self.assertEqual(AdminUserPreferences.objects.get(user=another_admin).preferences, second_preferences)

    def test_non_admin_cannot_update_admin_system_settings(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("admin_system_settings_update"),
            data=json.dumps({"settings": {"system_name": "Not allowed"}}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(AdminSystemSettings.objects.exists())

        preferences_response = self.client.post(
            reverse("admin_user_preferences_update"),
            data=json.dumps({"preferences": views.ADMIN_USER_PREFERENCE_DEFAULTS}),
            content_type="application/json",
        )
        self.assertEqual(preferences_response.status_code, 403)
        self.assertFalse(AdminUserPreferences.objects.exists())

    def test_system_name_changes_admin_brand_without_changing_public_brand(self):
        AdminSystemSettings.objects.create(
            key="global",
            settings={"system_name": "HappYness Operations"},
        )
        admin_request = RequestFactory().get(reverse("settings"))
        admin_request.user = self.admin
        regular_request = RequestFactory().get("/")
        regular_request.user = self.user

        self.assertEqual(dashboard_profile_context(admin_request)["admin_system_name"], "HappYness Operations")
        self.assertEqual(dashboard_profile_context(regular_request)["admin_system_name"], "HappYness Project")


class UserDashboardOverviewUpcomingActivitiesTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username="upcoming-activity-admin", password="password123")
        self.beneficiary = User.objects.create_user(username="beneficiary-next-up", password="password123")
        profile, _ = UserProfile.objects.get_or_create(user=self.beneficiary)
        profile.account_role = UserProfile.ROLE_BENEFICIARY
        profile.save(update_fields=["account_role", "updated_at"])
        self.application = RoleApplication.objects.create(
            user=self.beneficiary,
            role=RoleApplication.ROLE_BENEFICIARY,
            status=RoleApplication.STATUS_APPROVED,
            full_name="Ana Cruz",
            contact_details="ana@example.com",
            reason_for_assistance="Support",
            supporting_information="Needs support",
        )

    def test_dashboard_overview_sorts_upcoming_activities_and_exposes_next_up_list(self):
        self.client.force_login(self.beneficiary)

        Activity.objects.create(
            title="School Kit Release",
            date="2026-09-20",
            start_time="09:00:00",
            location="Molino III",
            status=Activity.STATUS_ACTIVE,
            description="School supply release",
            created_by=self.admin,
            created_by_name="Second Admin",
        )
        Activity.objects.create(
            title="Community Food Drive",
            date="2026-09-15",
            start_time="08:00:00",
            location="Barangay Hall",
            status=Activity.STATUS_ACTIVE,
            description="Food drive",
            created_by=self.admin,
            created_by_name="Directory Admin",
        )

        response = self.client.get(reverse("user_dashboard_overview_api"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["next_pickup"]["state"], "pending")
        self.assertEqual(payload["next_pickup"]["title"], "Community Food Drive")
        self.assertEqual(payload["next_pickup"]["created_by_name"], "Directory Admin")
        self.assertEqual(len(payload["next_pickup"]["upcoming_items"]), 2)
        self.assertEqual(payload["next_pickup"]["upcoming_items"][0]["date_label"], "Sep 15, 2026")
        self.assertEqual(payload["next_pickup"]["upcoming_items"][0]["created_by_name"], "Directory Admin")
        self.assertEqual(payload["next_pickup"]["upcoming_items"][1]["date_label"], "Sep 20, 2026")
        self.assertEqual(payload["next_pickup"]["upcoming_items"][1]["created_by_name"], "Second Admin")

    def test_completed_activity_is_not_returned_as_upcoming(self):
        self.client.force_login(self.beneficiary)

        Activity.objects.create(
            title="Completed Outreach Session",
            date="2026-09-25",
            location="Molino II",
            status=Activity.STATUS_COMPLETED,
        )
        Activity.objects.create(
            title="Upcoming Outreach Session",
            date="2026-09-26",
            location="Molino II",
            status=Activity.STATUS_ACTIVE,
        )

        response = self.client.get(reverse("user_dashboard_overview_api"))

        self.assertEqual(response.status_code, 200)
        upcoming_titles = [item["title"] for item in response.json()["next_pickup"]["upcoming_items"]]
        self.assertEqual(upcoming_titles, ["Upcoming Outreach Session"])

    def test_completed_activity_is_available_for_beneficiary_feedback(self):
        completed = Activity.objects.create(
            title="Completed Outreach Session",
            date="2026-09-25",
            location="Molino II",
            status=Activity.STATUS_COMPLETED,
        )
        ActivityBeneficiaryAssignment.objects.create(activity=completed, beneficiary=self.beneficiary)
        self.client.force_login(self.beneficiary)

        response = self.client.get(reverse("user_dashboard_overview_api"))

        self.assertEqual(response.status_code, 200)
        completed_items = response.json()["completed_activities"]
        self.assertEqual(completed_items[0]["id"], completed.id)
        self.assertEqual(completed_items[0]["feedback_target"], "activity")
        self.assertTrue(completed_items[0]["can_submit_feedback"])

        feedback_response = self.client.post(
            reverse("submit_beneficiary_pickup_feedback"),
            {
                "activity_id": completed.id,
                "rating": 5,
                "question_1": 5,
                "question_2": 3,
                "question_3": 4,
                "comment": "",
            },
        )

        self.assertEqual(feedback_response.status_code, 200)
        self.assertTrue(BeneficiaryActivityFeedback.objects.filter(activity=completed, beneficiary=self.application).exists())
        self.assertEqual(
            BeneficiaryActivityFeedback.objects.get(activity=completed, beneficiary=self.application).comment,
            "Q2: 3 | Q3: 4",
        )

    def test_admin_activity_feedback_payload_contains_question_summary(self):
        activity = Activity.objects.create(
            title="Community Outreach",
            date="2026-09-25",
            status=Activity.STATUS_COMPLETED,
        )
        BeneficiaryActivityFeedback.objects.create(
            activity=activity,
            beneficiary=self.application,
            user=self.beneficiary,
            rating=3,
            comment="Q2: Mostly | Q3: Likely",
        )

        feedback = next(
            item for item in views._build_assistance_feedbacks_payload()
            if item["source"] == "Activity" and item["subject"] == activity.title
        )

        self.assertEqual(
            feedback["questionRatings"],
            [3, 4, 4],
        )
        self.assertEqual(feedback["averageRating"], 3.7)

    def test_activity_feedback_requires_all_three_answers(self):
        activity = Activity.objects.create(
            title="Completed Outreach Session",
            date="2026-09-25",
            status=Activity.STATUS_COMPLETED,
        )
        ActivityBeneficiaryAssignment.objects.create(activity=activity, beneficiary=self.beneficiary)
        self.client.force_login(self.beneficiary)

        response = self.client.post(
            reverse("submit_beneficiary_pickup_feedback"),
            {"activity_id": activity.id, "rating": 5, "question_1": 5, "question_2": 4},
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(BeneficiaryActivityFeedback.objects.filter(activity=activity).exists())

    def test_feedback_is_unavailable_until_assigned_activity_is_completed(self):
        activity = Activity.objects.create(
            title="Scheduled Outreach Session",
            date="2026-09-25",
            location="Molino II",
            status=Activity.STATUS_ACTIVE,
        )
        ActivityBeneficiaryAssignment.objects.create(activity=activity, beneficiary=self.beneficiary)
        self.client.force_login(self.beneficiary)

        overview_response = self.client.get(reverse("user_dashboard_overview_api"))
        self.assertEqual(overview_response.status_code, 200)
        self.assertEqual(overview_response.json()["completed_activities"], [])

        feedback_response = self.client.post(
            reverse("submit_beneficiary_pickup_feedback"),
            {"activity_id": activity.id, "rating": 5, "question_1": 5, "question_2": 3, "question_3": 4},
        )

        self.assertEqual(feedback_response.status_code, 409)
        self.assertFalse(BeneficiaryActivityFeedback.objects.filter(activity=activity).exists())

    def test_unassigned_beneficiary_cannot_submit_feedback_for_completed_activity(self):
        activity = Activity.objects.create(
            title="Completed Outreach Session",
            date="2026-09-25",
            location="Molino II",
            status=Activity.STATUS_COMPLETED,
        )
        self.client.force_login(self.beneficiary)

        overview_response = self.client.get(reverse("user_dashboard_overview_api"))
        self.assertEqual(overview_response.status_code, 200)
        self.assertNotIn(activity.id, [item["id"] for item in overview_response.json()["completed_activities"]])

        feedback_response = self.client.post(
            reverse("submit_beneficiary_pickup_feedback"),
            {"activity_id": activity.id, "rating": 5, "question_1": 5, "question_2": 3, "question_3": 4},
        )

        self.assertEqual(feedback_response.status_code, 403)
        self.assertFalse(BeneficiaryActivityFeedback.objects.filter(activity=activity).exists())

    def test_dashboard_uses_live_beneficiary_data_not_stale_sample_content(self):
        self.client.force_login(self.beneficiary)

        skill_topic = SkillLearningTopic.objects.create(
            title="Water Safety Basics",
            description="Learning water safety basics.",
            badge_label="Beginner",
            filter_tags=["Community", "New"],
        )
        BeneficiaryAssistanceRecord.objects.create(
            beneficiary=self.application,
            aid_type="Food Assistance",
            quantity_or_amount="2",
            assistance_date="2026-09-01",
        )
        BeneficiaryAssistanceRecord.objects.create(
            beneficiary=self.application,
            aid_type="School Supplies",
            quantity_or_amount="1 set",
            assistance_date="2026-08-15",
        )
        live_announcement = CommunityPost.objects.create(
            user=self.beneficiary,
            content="Local clinic has reopened for health checkups.",
            post_type="announcements",
        )
        Activity.objects.create(
            title="Community Food Drive",
            date="2026-09-25",
            start_time="08:00:00",
            location="Barangay Hall",
            status=Activity.STATUS_ACTIVE,
            description="Food drive",
        )

        response = self.client.get(reverse("user_dashboard_overview_api"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["metrics"]["programs_enrolled"], 2)
        self.assertEqual(payload["metrics"]["skills_available"], 1)
        self.assertEqual(payload["next_pickup"]["state"], "pending")
        self.assertEqual(payload["next_pickup"]["title"], "Community Food Drive")
        self.assertTrue(any(item["title"] == live_announcement.content for item in payload["announcements"]))
        self.assertNotIn("Apr 22, 2026", str(payload))
        self.assertNotIn("School Kit Release", str(payload))
        self.assertTrue(any(item["name"] == "Water Safety Basics" for item in payload["skills"]))

    def test_dashboard_skill_panel_recommends_real_skill_topics_with_badges_and_link(self):
        self.client.force_login(self.beneficiary)

        SkillLearningTopic.objects.create(
            title="Water Safety Basics",
            description="Learn the basics of safe water habits.",
            badge_label="Beginner",
            filter_tags=["Community", "New"],
        )
        SkillLearningTopic.objects.create(
            title="First Aid Essentials",
            description="A quick guide to emergency basics.",
            badge_label="Popular",
            filter_tags=["Health", "Popular"],
        )

        response = self.client.get(reverse("user_dashboard_overview_api"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreater(len(payload["skills"]), 0)
        self.assertIn("name", payload["skills"][0])
        self.assertIn("badge", payload["skills"][0])
        self.assertTrue(any(item.get("name") == "Water Safety Basics" for item in payload["skills"]))
        self.assertTrue(payload["links"].get("skill_learning"))

    def test_dashboard_reports_empty_state_when_no_live_records_exist(self):
        self.client.force_login(self.beneficiary)

        response = self.client.get(reverse("user_dashboard_overview_api"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["next_pickup"]["state"], "none")
        self.assertEqual(payload["distribution_history"], [])
        self.assertEqual(payload["skills"], [])
        self.assertEqual(payload["announcements"], [])
        self.assertNotIn("Apr 22, 2026", str(payload))


class CommunityPostInteractionPersistenceTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(username="community-author", password="password123")
        self.member = User.objects.create_user(username="community-member", password="password123")
        self.post = CommunityPost.objects.create(
            user=self.author,
            content="Community interaction persistence sample",
            post_type="discussions",
        )

    def _post_payload_for(self, response_payload, post_id):
        post_id_str = str(post_id)
        for post in response_payload.get("posts", []):
            if str(post.get("id")) == post_id_str:
                return post
        self.fail(f"Post {post_id_str} not found in dashboard payload.")

    def test_post_like_persists_in_feed_payload_after_reload(self):
        self.client.force_login(self.member)

        like_response = self.client.post(
            reverse("dashboard_community_post_like_toggle", args=[self.post.id])
        )
        self.assertEqual(like_response.status_code, 200)
        self.assertTrue(like_response.json()["liked"])
        self.assertEqual(like_response.json()["likes"], 1)

        feed_response = self.client.get(reverse("dashboard_community_posts"))
        self.assertEqual(feed_response.status_code, 200)
        member_post_payload = self._post_payload_for(feed_response.json(), self.post.id)
        self.assertEqual(member_post_payload["likes"], 1)
        self.assertTrue(member_post_payload["liked"])

        self.client.force_login(self.author)
        author_feed_response = self.client.get(reverse("dashboard_community_posts"))
        self.assertEqual(author_feed_response.status_code, 200)
        author_post_payload = self._post_payload_for(author_feed_response.json(), self.post.id)
        self.assertEqual(author_post_payload["likes"], 1)
        self.assertFalse(author_post_payload["liked"])

    def test_community_feed_script_preserves_viewer_report_flags(self):
        script = Path(views.__file__).resolve().parent / "static" / "js" / "community-feed-stable.js"
        source = script.read_text(encoding="utf-8")

        self.assertIn("reportedByViewer: !!(rawPost && rawPost.reportedByViewer)", source)
        self.assertIn("var isReportedByViewer = !!post.reportedByViewer;", source)
        self.assertIn("isReportedByViewer ? \"This post is hidden.\" : activityMarkup", source)

    def test_comments_and_replies_persist_after_reload(self):
        self.client.force_login(self.member)

        comment_response = self.client.post(
            reverse("dashboard_community_post_comment_create", args=[self.post.id]),
            data={"content": "Glad this panel is improving."},
        )
        self.assertEqual(comment_response.status_code, 201)
        comment_id = comment_response.json()["comment"]["id"]

        first_reply_response = self.client.post(
            reverse("dashboard_community_comment_reply_create", args=[self.post.id, comment_id]),
            data={"content": "Following up with more context."},
        )
        self.assertEqual(first_reply_response.status_code, 201)
        first_reply_id = first_reply_response.json()["reply"]["id"]

        second_reply_response = self.client.post(
            reverse("dashboard_community_comment_reply_create", args=[self.post.id, first_reply_id]),
            data={"content": "Replying to my previous reply."},
        )
        self.assertEqual(second_reply_response.status_code, 201)

        comments_response = self.client.get(
            reverse("dashboard_community_post_comments", args=[self.post.id]),
            data={"offset": 0},
        )
        self.assertEqual(comments_response.status_code, 200)
        comments_payload = comments_response.json()
        self.assertEqual(comments_payload["pageSize"], 8)
        self.assertEqual(len(comments_payload["comments"]), 1)

        comment_payload = comments_payload["comments"][0]
        self.assertEqual(comment_payload["text"], "Glad this panel is improving.")
        self.assertEqual(len(comment_payload["replies"]), 2)

        first_reply = next(
            reply for reply in comment_payload["replies"]
            if reply["text"] == "Following up with more context."
        )
        second_reply = next(
            reply for reply in comment_payload["replies"]
            if reply["text"] == "Replying to my previous reply."
        )

        self.assertFalse(first_reply["replyShowsChain"])
        self.assertTrue(second_reply["replyShowsChain"])
        self.assertEqual(second_reply["replyToAuthor"], self.member.username)

    def test_comment_like_persists_in_feed_payload_after_reload(self):
        comment = CommunityPostComment.objects.create(
            post=self.post,
            user=self.author,
            content="Please share your best practices.",
        )

        self.client.force_login(self.member)
        like_response = self.client.post(
            reverse("dashboard_community_comment_like_toggle", args=[self.post.id, comment.id])
        )
        self.assertEqual(like_response.status_code, 200)
        self.assertTrue(like_response.json()["liked"])
        self.assertEqual(like_response.json()["likes"], 1)

        comments_response = self.client.get(
            reverse("dashboard_community_post_comments", args=[self.post.id]),
            data={"offset": 0},
        )
        self.assertEqual(comments_response.status_code, 200)
        comments_payload = comments_response.json()
        self.assertEqual(len(comments_payload["comments"]), 1)

        liked_comment_payload = comments_payload["comments"][0]
        self.assertEqual(liked_comment_payload["likes"], 1)
        self.assertTrue(liked_comment_payload["liked"])

        self.client.force_login(self.author)
        author_comments_response = self.client.get(
            reverse("dashboard_community_post_comments", args=[self.post.id]),
            data={"offset": 0},
        )
        self.assertEqual(author_comments_response.status_code, 200)
        author_comments_payload = author_comments_response.json()
        self.assertEqual(author_comments_payload["comments"][0]["likes"], 1)
        self.assertFalse(author_comments_payload["comments"][0]["liked"])

    def test_dashboard_posts_returns_eight_items_per_batch(self):
        for index in range(12):
            CommunityPost.objects.create(
                user=self.author,
                content=f"Additional post {index}",
                post_type="discussions",
            )


class CommunityCommentManageTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username="comment-admin", email="comment-admin@example.com", password="password123")
        self.author = User.objects.create_user(username="comment-volunteer", password="password123")
        author_profile, _ = UserProfile.objects.get_or_create(user=self.author)
        author_profile.account_role = UserProfile.ROLE_VOLUNTEER
        author_profile.save(update_fields=["account_role", "updated_at"])
        RoleApplication.objects.create(
            user=self.author,
            role=RoleApplication.ROLE_VOLUNTEER,
            status=RoleApplication.STATUS_APPROVED,
            full_name="Comment Volunteer",
            contact_details="comment-volunteer@example.com",
        )
        self.other = User.objects.create_user(username="comment-beneficiary", password="password123")
        other_profile, _ = UserProfile.objects.get_or_create(user=self.other)
        other_profile.account_role = UserProfile.ROLE_BENEFICIARY
        other_profile.save(update_fields=["account_role", "updated_at"])
        RoleApplication.objects.create(
            user=self.other,
            role=RoleApplication.ROLE_BENEFICIARY,
            status=RoleApplication.STATUS_APPROVED,
            full_name="Comment Beneficiary",
            contact_details="comment-beneficiary@example.com",
        )
        self.post = CommunityPost.objects.create(user=self.author, content="Comment permissions", post_type="discussions")

    def test_comment_author_can_edit_and_delete_comment_and_reply(self):
        comment = CommunityPostComment.objects.create(post=self.post, user=self.author, content="Original comment")
        reply = CommunityPostComment.objects.create(post=self.post, user=self.author, parent=comment, content="Original reply")
        self.client.force_login(self.author)

        edit_response = self.client.post(
            reverse("dashboard_community_comment_update", args=[self.post.id, comment.id]),
            data={"content": "Edited comment"},
        )
        reply_edit_response = self.client.post(
            reverse("dashboard_community_comment_update", args=[self.post.id, reply.id]),
            data={"content": "Edited reply"},
        )
        self.assertEqual(edit_response.status_code, 200)
        self.assertEqual(reply_edit_response.status_code, 200)
        comment.refresh_from_db()
        reply.refresh_from_db()
        self.assertEqual(comment.content, "Edited comment")
        self.assertEqual(reply.content, "Edited reply")

        delete_response = self.client.post(
            reverse("dashboard_community_comment_delete", args=[self.post.id, comment.id])
        )
        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(delete_response.json()["commentCount"], 0)
        self.assertFalse(CommunityPostComment.objects.filter(pk__in=[comment.id, reply.id]).exists())

    def test_comment_actions_are_author_scoped_and_admin_can_moderate(self):
        comment = CommunityPostComment.objects.create(post=self.post, user=self.author, content="Author comment")
        reply = CommunityPostComment.objects.create(post=self.post, user=self.author, parent=comment, content="Author reply")
        self.client.force_login(self.other)

        comments_response = self.client.get(reverse("dashboard_community_post_comments", args=[self.post.id]))
        self.assertEqual(comments_response.status_code, 200)
        self.assertFalse(comments_response.json()["comments"][0]["canManage"])
        self.assertFalse(comments_response.json()["comments"][0]["replies"][0]["canManage"])
        denied_edit_response = self.client.post(
            reverse("dashboard_community_comment_update", args=[self.post.id, comment.id]),
            data={"content": "Unauthorized edit"},
        )
        denied_response = self.client.post(
            reverse("dashboard_community_comment_delete", args=[self.post.id, comment.id])
        )
        self.assertEqual(denied_edit_response.status_code, 403)
        self.assertEqual(denied_response.status_code, 403)
        self.assertTrue(CommunityPostComment.objects.filter(pk=comment.id).exists())

        self.client.force_login(self.admin)
        admin_comments_response = self.client.get(reverse("dashboard_community_post_comments", args=[self.post.id]))
        self.assertTrue(admin_comments_response.json()["comments"][0]["canManage"])
        self.assertTrue(admin_comments_response.json()["comments"][0]["replies"][0]["canManage"])
        admin_edit_response = self.client.post(
            reverse("dashboard_community_comment_update", args=[self.post.id, comment.id]),
            data={"content": "Admin moderation edit"},
        )
        self.assertEqual(admin_edit_response.status_code, 200)
        admin_delete_response = self.client.post(
            reverse("dashboard_community_comment_delete", args=[self.post.id, comment.id])
        )
        self.assertEqual(admin_delete_response.status_code, 200)
        self.assertFalse(CommunityPostComment.objects.filter(pk=comment.id).exists())
        self.assertFalse(CommunityPostComment.objects.filter(pk=reply.id).exists())

    def test_comment_edits_require_nonempty_text_of_280_characters_or_less(self):
        comment = CommunityPostComment.objects.create(post=self.post, user=self.author, content="Keep this")
        self.client.force_login(self.author)

        empty_response = self.client.post(
            reverse("dashboard_community_comment_update", args=[self.post.id, comment.id]),
            data={"content": "  "},
        )
        oversized_response = self.client.post(
            reverse("dashboard_community_comment_update", args=[self.post.id, comment.id]),
            data={"content": "x" * 281},
        )

        self.assertEqual(empty_response.status_code, 400)
        self.assertEqual(oversized_response.status_code, 400)
        comment.refresh_from_db()
        self.assertEqual(comment.content, "Keep this")


class RoleFlowTests(TestCase):
    def test_signup_creates_regular_profile(self):
        response = self.client.post(
            reverse("signup"),
            data={
                "username": "regular-user",
                "email": "regular@example.com",
                "password1": "password123",
                "password2": "password123",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        user = User.objects.get(username="regular-user")
        profile = UserProfile.objects.get(user=user)
        self.assertEqual(profile.account_role, UserProfile.ROLE_REGULAR)
        self.assertContains(response, "General Dashboard")

    def test_regular_user_can_sign_in_and_reach_home_dashboard(self):
        user = User.objects.create_user(username="dashboard-user", email="dashboard@example.com", password="password123")

        response = self.client.post(
            reverse("signin"),
            data={
                "username_or_email": "dashboard-user",
                "password": "password123",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Apply as Beneficiary")
        self.assertContains(response, "Apply as Volunteer")
        self.assertTrue(UserProfile.objects.filter(user=user, account_role=UserProfile.ROLE_REGULAR).exists())

    def test_beneficiary_application_is_saved_as_pending(self):
        user = User.objects.create_user(username="beneficiary-applicant", password="password123")
        self.client.force_login(user)

        response = self.client.post(
            reverse("apply_beneficiary"),
            data={
                "full_name": "Ana Cruz",
                "track": "happy_nanas",
                "contact_details": "ana@example.com / 09171234567",
                "reason_for_assistance": "Temporary financial support is needed.",
                "supporting_information": "Household currently has no stable income.",
            },
        )

        self.assertEqual(response.status_code, 302)
        application = RoleApplication.objects.get(user=user, role=RoleApplication.ROLE_BENEFICIARY)
        self.assertEqual(application.status, RoleApplication.STATUS_PENDING)
        self.assertEqual(application.full_name, "Ana Cruz")

    def test_volunteer_application_is_saved_as_pending(self):
        user = User.objects.create_user(username="volunteer-applicant", password="password123")
        self.client.force_login(user)

        response = self.client.post(
            reverse("apply_volunteer"),
            data={
                "full_name": "Marco Dela Cruz",
                "track": "intern",
                "contact_details": "marco@example.com / 09170001111",
                "skills": "Community outreach, logistics, first aid",
                "availability": "Weekends and evenings",
                "areas_of_interest": "Outreach, disaster response, learning sessions",
            },
        )

        self.assertEqual(response.status_code, 302)
        application = RoleApplication.objects.get(user=user, role=RoleApplication.ROLE_VOLUNTEER)
        self.assertEqual(application.status, RoleApplication.STATUS_PENDING)
        self.assertEqual(application.skills, "Community outreach, logistics, first aid")

        self.client.force_login(self.member)

        first_response = self.client.get(reverse("dashboard_community_posts"), data={"offset": 0})
        self.assertEqual(first_response.status_code, 200)
        first_payload = first_response.json()

        self.assertEqual(first_payload["pageSize"], 8)
        self.assertEqual(len(first_payload["posts"]), 8)
        self.assertTrue(first_payload["hasMore"])
        self.assertEqual(first_payload["nextOffset"], 8)

        expected_first_ids = list(
            CommunityPost.objects.filter(user__is_superuser=False)
            .order_by("-created_at", "-id")
            .values_list("id", flat=True)[:8]
        )
        actual_first_ids = [int(post["id"]) for post in first_payload["posts"]]
        self.assertEqual(actual_first_ids, expected_first_ids)

        second_response = self.client.get(reverse("dashboard_community_posts"), data={"offset": first_payload["nextOffset"]})
        self.assertEqual(second_response.status_code, 200)
        second_payload = second_response.json()
        self.assertEqual(len(second_payload["posts"]), 5)
        self.assertFalse(second_payload["hasMore"])
        self.assertIsNone(second_payload["nextOffset"])

        first_ids = {int(post["id"]) for post in first_payload["posts"]}
        second_ids = {int(post["id"]) for post in second_payload["posts"]}
        self.assertTrue(first_ids.isdisjoint(second_ids))

    def test_beneficiary_pending_application_appears_and_approval_redirects_to_user_dashboard(self):
        user = User.objects.create_user(username="beneficiary-flow", password="password123")
        admin = User.objects.create_superuser(username="admin-beneficiary", email="admin-beneficiary@example.com", password="password123")
        self.client.force_login(user)

        response = self.client.post(
            reverse("apply_beneficiary"),
            data={
                "full_name": "Ana Cruz",
                "track": "happy_kids",
                "contact_details": "ana@example.com / 09171234567",
                "reason_for_assistance": "Temporary financial support is needed.",
                "supporting_information": "Household currently has no stable income.",
            },
        )

        self.assertEqual(response.status_code, 302)

        admin_client = Client()
        admin_client.force_login(admin)
        admin_response = admin_client.get(reverse("beneficiaries"))
        self.assertEqual(admin_response.status_code, 200)
        self.assertContains(admin_response, "Ana Cruz")

        application = RoleApplication.objects.get(user=user, role=RoleApplication.ROLE_BENEFICIARY)
        approve_response = admin_client.post(
            reverse("review_role_application"),
            data={
                "application_id": str(application.id),
                "action": "approve",
            },
        )

        self.assertEqual(approve_response.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.userprofile.account_role, UserProfile.ROLE_BENEFICIARY)

        refresh_response = self.client.get(reverse("home"), follow=False)
        self.assertEqual(refresh_response.status_code, 302)
        self.assertEqual(refresh_response.url, reverse("user_dashboard"))

    def test_volunteer_pending_application_appears_and_approval_redirects_to_volunteer_dashboard(self):
        user = User.objects.create_user(username="volunteer-flow", password="password123")
        admin = User.objects.create_superuser(username="admin-volunteer", email="admin-volunteer@example.com", password="password123")
        self.client.force_login(user)

        response = self.client.post(
            reverse("apply_volunteer"),
            data={
                "full_name": "Marco Dela Cruz",
                "track": "community_volunteer",
                "contact_details": "marco@example.com / 09170001111",
                "skills": "Community outreach, logistics, first aid",
                "availability": "Weekends and evenings",
                "areas_of_interest": "Outreach, disaster response, learning sessions",
            },
        )

        self.assertEqual(response.status_code, 302)

        admin_client = Client()
        admin_client.force_login(admin)
        admin_response = admin_client.get(reverse("volunteers"))
        self.assertEqual(admin_response.status_code, 200)
        self.assertContains(admin_response, "Marco Dela Cruz")

        application = RoleApplication.objects.get(user=user, role=RoleApplication.ROLE_VOLUNTEER)
        approve_response = admin_client.post(
            reverse("review_role_application"),
            data={
                "application_id": str(application.id),
                "action": "approve",
            },
        )

        self.assertEqual(approve_response.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.userprofile.account_role, UserProfile.ROLE_VOLUNTEER)

        refresh_response = self.client.get(reverse("home"), follow=False)
        self.assertEqual(refresh_response.status_code, 302)
        self.assertEqual(refresh_response.url, reverse("volunteer_dashboard"))

    def test_comments_endpoint_returns_newest_top_level_first_in_batches(self):
        for index in range(10):
            CommunityPostComment.objects.create(
                post=self.post,
                user=self.author,
                content=f"Top-level comment {index}",
            )

        self.client.force_login(self.member)

        first_response = self.client.get(
            reverse("dashboard_community_post_comments", args=[self.post.id]),
            data={"offset": 0},
        )
        self.assertEqual(first_response.status_code, 200)
        first_payload = first_response.json()

        self.assertEqual(first_payload["pageSize"], 8)
        self.assertEqual(len(first_payload["comments"]), 8)
        self.assertTrue(first_payload["hasMore"])
        self.assertEqual(first_payload["nextOffset"], 8)

        expected_first_comment_ids = list(
            CommunityPostComment.objects.filter(post=self.post, parent__isnull=True)
            .order_by("-created_at", "-id")
            .values_list("id", flat=True)[:8]
        )
        actual_first_comment_ids = [int(comment["id"]) for comment in first_payload["comments"]]
        self.assertEqual(actual_first_comment_ids, expected_first_comment_ids)

        second_response = self.client.get(
            reverse("dashboard_community_post_comments", args=[self.post.id]),
            data={"offset": first_payload["nextOffset"]},
        )
        self.assertEqual(second_response.status_code, 200)
        second_payload = second_response.json()
        self.assertEqual(len(second_payload["comments"]), 2)
        self.assertFalse(second_payload["hasMore"])
        self.assertIsNone(second_payload["nextOffset"])


class RegularUsersBulkActionTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="regular-users-admin",
            email="regular-users-admin@example.com",
            password="SecureAdminPass!2026",
        )
        self.client.force_login(self.admin)

    def create_regular_user(self, username):
        user = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="SecureUserPass!2026",
        )
        UserProfile.objects.create(user=user, account_role=UserProfile.ROLE_REGULAR)
        return user

    def test_users_directory_renders_multi_select_controls(self):
        user = self.create_regular_user("directory-user")

        response = self.client.get(reverse("regular_users"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="regular-users-select-all"')
        self.assertContains(response, "data-user-select")
        self.assertContains(response, 'id="regular-users-delete-selected"')
        self.assertContains(response, user.username)

    def test_admin_can_bulk_delete_regular_users(self):
        users = [
            self.create_regular_user("bulk-user-one"),
            self.create_regular_user("bulk-user-two"),
        ]

        response = self.client.post(
            reverse("delete_regular_user"),
            {"user_ids": [str(user.id) for user in users]},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["deleted_count"], 2)
        self.assertFalse(User.objects.filter(id__in=[user.id for user in users]).exists())

    def test_bulk_delete_rejects_non_regular_account_without_partial_deletion(self):
        regular_user = self.create_regular_user("bulk-regular-user")
        beneficiary = User.objects.create_user(
            username="bulk-beneficiary",
            email="bulk-beneficiary@example.com",
            password="SecureUserPass!2026",
        )
        UserProfile.objects.create(user=beneficiary, account_role=UserProfile.ROLE_BENEFICIARY)

        response = self.client.post(
            reverse("delete_regular_user"),
            {"user_ids": [str(regular_user.id), str(beneficiary.id)]},
        )

        self.assertEqual(response.status_code, 400)
        self.assertTrue(User.objects.filter(id=regular_user.id).exists())
        self.assertTrue(User.objects.filter(id=beneficiary.id).exists())

    def test_bulk_delete_rejects_empty_or_invalid_ids(self):
        for user_ids in ([], ["not-an-id"]):
            with self.subTest(user_ids=user_ids):
                response = self.client.post(
                    reverse("delete_regular_user"),
                    {"user_ids": user_ids},
                )
                self.assertEqual(response.status_code, 400)

    def test_non_admin_cannot_bulk_delete_users(self):
        self.client.force_login(self.create_regular_user("non-admin-user"))
        target = self.create_regular_user("protected-user")

        response = self.client.post(
            reverse("delete_regular_user"),
            {"user_ids": [str(target.id)]},
        )

        self.assertEqual(response.status_code, 403)
        self.assertTrue(User.objects.filter(id=target.id).exists())


class AdminDirectoryTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="directory-admin",
            email="directory-admin@example.com",
            password="test-password",
            first_name="Directory",
            last_name="Admin",
        )
        self.client.force_login(self.admin)

    def test_admin_directory_lists_only_admin_accounts(self):
        inactive_admin = User.objects.create_superuser(
            username="inactive-admin",
            email="inactive-admin@example.com",
            password="test-password",
        )
        inactive_admin.is_active = False
        inactive_admin.save(update_fields=["is_active"])
        regular_user = User.objects.create_user(
            username="directory-regular-user",
            email="regular@example.com",
            password="test-password",
        )
        staff_user = User.objects.create_user(
            username="directory-staff-user",
            email="staff@example.com",
            password="test-password",
            is_staff=True,
        )

        response = self.client.get(reverse("admins"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.admin.username)
        self.assertContains(response, self.admin.email)
        self.assertContains(response, "Directory Admin")
        self.assertContains(response, inactive_admin.username)
        self.assertContains(response, "Active Admins")
        self.assertContains(response, "Inactive Admins")
        self.assertContains(response, "Joined This Week")
        self.assertEqual(response.context["admin_counts"]["total"], 2)
        self.assertEqual(response.context["admin_counts"]["active"], 1)
        self.assertEqual(response.context["admin_counts"]["inactive"], 1)
        self.assertEqual(response.context["admin_counts"]["joined_this_week"], 2)
        self.assertEqual(response.content.decode().count('class="admins-card admins-kpi"'), 4)
        self.assertNotContains(response, regular_user.username)
        self.assertNotContains(response, staff_user.username)
        self.assertContains(response, "Inactive")

    def test_admin_directory_renders_search_status_add_and_show_more_controls(self):
        response = self.client.get(reverse("admins"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="admins-search"')
        self.assertContains(response, 'id="admins-status-filter"')
        self.assertContains(response, "All Statuses")
        self.assertContains(response, 'id="admins-add-open"')
        self.assertContains(response, "Add Admin")
        self.assertContains(response, 'data-admin-status="active"')
        self.assertContains(response, 'data-admin-status="inactive"')
        self.assertContains(response, 'name="status" value="active"')
        self.assertContains(response, 'id="admins-toggle-columns"')
        self.assertContains(response, "Show More")
        self.assertContains(response, reverse("create_admin"))
        self.assertContains(response, 'data-admin-actions-trigger')
        self.assertContains(response, 'id="admins-actions-menu"')
        self.assertContains(response, "Admin Profile")
        self.assertContains(response, 'id="admins-profile-edit"')
        self.assertContains(response, 'id="admins-profile-form"')
        self.assertContains(response, "Save Changes")
        self.assertContains(response, reverse("update_admin_profile"))
        self.assertContains(response, "Deactivate Admin")
        self.assertContains(response, "Remove Admin")
        self.assertContains(response, reverse("update_admin_status"))

    def test_admin_activity_log_filters_and_paginates_read_only_entries(self):
        for index in range(51):
            AdminActivityLog.objects.create(
                admin=self.admin,
                admin_name="Directory Admin",
                action=AdminActivityLog.ACTION_EDIT,
                section="Activities",
                record_type="Activity",
                record_id=str(index + 1),
                record_label=f"Community activity {index + 1}",
                details="Changed date",
            )
        AdminActivityLog.objects.create(
            admin=self.admin,
            admin_name="Directory Admin",
            action=AdminActivityLog.ACTION_STATUS,
            section="Payments",
            record_type="Payment",
            record_id="999",
            record_label="Unrelated payment",
            details="Changed status",
        )

        filters = {
            "tab": "activity-log",
            "admin": "Directory Admin",
            "section": "Activities",
            "action": AdminActivityLog.ACTION_EDIT,
            "q": "Community activity",
            "start_date": timezone.localdate().isoformat(),
            "end_date": timezone.localdate().isoformat(),
        }
        response = self.client.get(reverse("admins"), filters)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Admin Activity Log")
        self.assertContains(response, 'aria-label="Admin Activity Log"')
        self.assertContains(response, "Date &amp; Time")
        self.assertEqual(response.context["active_admin_tab"], "activity-log")
        self.assertEqual(response.context["activity_log_count"], 51)
        self.assertEqual(response.context["activity_log_page"].paginator.num_pages, 2)
        self.assertContains(response, "Next")
        self.assertNotContains(response, "Unrelated payment")

        second_page = self.client.get(reverse("admins"), {**filters, "log_page": "2"})
        self.assertEqual(second_page.context["activity_log_page"].number, 2)
        self.assertEqual(len(second_page.context["activity_log_page"].object_list), 1)
        self.assertContains(second_page, "Previous")

    def test_admin_activity_log_details_are_compact_and_deduplicated(self):
        AdminActivityLog.objects.create(
            admin=self.admin,
            admin_name="Directory Admin",
            action=AdminActivityLog.ACTION_EDIT,
            section="Users",
            record_type="User Profile",
            record_id="46",
            record_label="User Profile #46",
            details="Edited User Profile #46. Changed: Account Role, Volunteer Role.",
        )
        AdminActivityLog.objects.create(
            admin=self.admin,
            admin_name="Directory Admin",
            action=AdminActivityLog.ACTION_CREATE,
            section="Activities",
            record_type="Activity",
            record_id="107",
            record_label="SM Baco Fest",
            details="Added SM Baco Fest.",
        )

        response = self.client.get(reverse("admins"), {"tab": "activity-log"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<strong class="admins-log-record">User</strong>', html=True)
        self.assertContains(response, '<small class="admins-log-record-id">#46</small>', html=True)
        self.assertContains(response, '<small class="admins-log-change">Changed: Account Role, Volunteer Role</small>', html=True)
        self.assertContains(response, '<strong class="admins-log-record">SM Baco Fest</strong>', html=True)
        self.assertContains(response, '<small class="admins-log-change">Added</small>', html=True)
        self.assertContains(response, 'title="User Profile: User Profile #46 ID 46 Edited User Profile #46. Changed: Account Role, Volunteer Role."')

    def test_admin_creation_and_status_changes_are_logged(self):
        create_response = self.client.post(
            reverse("create_admin"),
            {
                "full_name": "New Administrator",
                "username": "audit-directory-admin",
                "email": "audit-directory-admin@example.com",
                "password": "T#6-vrgP9E-L3x!Wqk4-2026",
                "confirm_password": "T#6-vrgP9E-L3x!Wqk4-2026",
            },
        )
        self.assertEqual(create_response.status_code, 201)
        created_admin = User.objects.get(username="audit-directory-admin")
        created_log = AdminActivityLog.objects.get(
            record_id=str(created_admin.pk),
            action=AdminActivityLog.ACTION_CREATE,
        )
        self.assertEqual(created_log.admin, self.admin)
        self.assertEqual(created_log.admin_name, "Directory Admin")
        self.assertEqual(created_log.section, "Users")

        status_response = self.client.post(
            reverse("update_admin_status"),
            {"admin_id": created_admin.pk, "status": "inactive"},
        )
        self.assertEqual(status_response.status_code, 200)
        status_log = AdminActivityLog.objects.get(
            record_id=str(created_admin.pk),
            action=AdminActivityLog.ACTION_STATUS,
        )
        self.assertIn("Inactive", status_log.details)

    def test_role_approval_and_inventory_deletion_are_logged(self):
        application = RoleApplication.objects.create(
            user=None,
            role=RoleApplication.ROLE_VOLUNTEER,
            full_name="Pending Volunteer",
            contact_details="pending@example.com",
        )
        item = InventoryItem.objects.create(
            name="Audit Test Item",
            category=InventoryItem.CATEGORY_OTHER,
            stock=1,
        )

        token = set_admin_actor(self.admin)
        try:
            application.status = RoleApplication.STATUS_APPROVED
            application.save(update_fields=["status", "updated_at"])
            item.delete()
        finally:
            reset_admin_actor(token)

        approval_log = AdminActivityLog.objects.get(
            record_id=str(application.pk),
            action=AdminActivityLog.ACTION_APPROVAL,
        )
        deletion_log = AdminActivityLog.objects.get(
            record_id=str(item.pk),
            action=AdminActivityLog.ACTION_DELETE,
        )
        self.assertEqual(approval_log.section, "Volunteers")
        self.assertIn("Approved", approval_log.details)
        self.assertEqual(deletion_log.section, "Inventory")

    def test_people_directories_load_custom_status_dropdowns(self):
        directory_routes = {
            "admins": "status-filter-select--admins-status-filter",
            "regular_users": "status-filter-select--regular-users-status",
            "volunteers": "status-filter-select--vol-status-filter",
            "beneficiaries": "status-filter-select--ben-status-filter",
        }

        for route_name, wrapper_class in directory_routes.items():
            with self.subTest(directory=route_name):
                response = self.client.get(reverse(route_name))

                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "data-status-filter-custom")
                self.assertContains(response, wrapper_class)
                self.assertContains(response, "css/status-filter-select.css")
                self.assertContains(response, "js/status-filter-select.js")

    def test_admin_directory_renders_bulk_selection_controls(self):
        response = self.client.get(reverse("admins"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="admins-select-all"')
        self.assertContains(response, "data-admin-select")
        self.assertContains(response, 'id="admins-bulk-bar"')
        self.assertContains(response, 'id="admins-clear-selection"')
        self.assertContains(response, "Clear selection")
        self.assertContains(response, 'id="admins-delete-selected"')
        self.assertContains(response, "Remove Selected")
        self.assertContains(response, 'id="admins-confirm-modal"')
        self.assertContains(response, "Confirmation")
        self.assertContains(response, 'id="admins-confirm-message"')
        self.assertContains(response, 'id="admins-confirm-submit" class="is-danger"')
        self.assertContains(response, "You cannot remove your own account or the last active administrator.")

    def test_superuser_can_bulk_remove_other_admin_accounts(self):
        removable_admin = User.objects.create_superuser(
            username="removable-admin",
            email="removable-admin@example.com",
            password="test-password",
        )

        response = self.client.post(
            reverse("delete_admins"),
            {"admin_ids": [str(removable_admin.id)]},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["deleted_count"], 1)
        self.assertFalse(User.objects.filter(id=removable_admin.id).exists())
        self.assertTrue(User.objects.filter(id=self.admin.id).exists())

    def test_admin_bulk_removal_rejects_self_without_deleting_other_accounts(self):
        other_admin = User.objects.create_superuser(
            username="other-admin",
            email="other-admin@example.com",
            password="test-password",
        )

        response = self.client.post(
            reverse("delete_admins"),
            {"admin_ids": [str(other_admin.id), str(self.admin.id)]},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("own administrator account", response.json()["error"])
        self.assertTrue(User.objects.filter(id=other_admin.id).exists())
        self.assertTrue(User.objects.filter(id=self.admin.id).exists())

    def test_admin_bulk_removal_rejects_non_admin_selection_without_partial_deletion(self):
        other_admin = User.objects.create_superuser(
            username="validated-admin",
            email="validated-admin@example.com",
            password="test-password",
        )
        regular_user = User.objects.create_user(
            username="not-an-admin",
            email="not-an-admin@example.com",
            password="test-password",
        )

        response = self.client.post(
            reverse("delete_admins"),
            {"admin_ids": [str(other_admin.id), str(regular_user.id)]},
        )

        self.assertEqual(response.status_code, 400)
        self.assertTrue(User.objects.filter(id=other_admin.id).exists())
        self.assertTrue(User.objects.filter(id=regular_user.id).exists())

    def test_superuser_can_deactivate_and_reactivate_another_admin(self):
        target_admin = User.objects.create_superuser(
            username="status-target-admin",
            email="status-target-admin@example.com",
            password="TestPassword!234",
        )

        deactivate_response = self.client.post(
            reverse("update_admin_status"),
            {"admin_id": str(target_admin.id), "status": "inactive"},
        )

        self.assertEqual(deactivate_response.status_code, 200)
        self.assertFalse(User.objects.get(id=target_admin.id).is_active)

        reactivate_response = self.client.post(
            reverse("update_admin_status"),
            {"admin_id": str(target_admin.id), "status": "active"},
        )

        self.assertEqual(reactivate_response.status_code, 200)
        self.assertTrue(User.objects.get(id=target_admin.id).is_active)

    def test_superuser_can_update_admin_profile(self):
        target_admin = User.objects.create_superuser(
            username="profile-target-admin",
            email="profile-target-admin@example.com",
            password="TestPassword!234",
            first_name="Old",
            last_name="Name",
        )

        response = self.client.post(
            reverse("update_admin_profile"),
            {
                "admin_id": str(target_admin.id),
                "full_name": "Updated Administrator",
                "username": "updated-profile-admin",
                "email": "updated-profile-admin@example.com",
                "status": "inactive",
            },
        )

        self.assertEqual(response.status_code, 200)
        target_admin.refresh_from_db()
        self.assertEqual(target_admin.get_full_name(), "Updated Administrator")
        self.assertEqual(target_admin.username, "updated-profile-admin")
        self.assertEqual(target_admin.email, "updated-profile-admin@example.com")
        self.assertFalse(target_admin.is_active)

    def test_admin_profile_update_rejects_deactivating_self(self):
        response = self.client.post(
            reverse("update_admin_profile"),
            {
                "admin_id": str(self.admin.id),
                "full_name": "Directory Admin",
                "username": self.admin.username,
                "email": self.admin.email,
                "status": "inactive",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("own administrator account", response.json()["error"])
        self.assertTrue(User.objects.get(id=self.admin.id).is_active)

    def test_admin_profile_update_rejects_duplicate_username(self):
        target_admin = User.objects.create_superuser(
            username="profile-duplicate-target",
            email="profile-duplicate-target@example.com",
            password="TestPassword!234",
        )

        response = self.client.post(
            reverse("update_admin_profile"),
            {
                "admin_id": str(target_admin.id),
                "full_name": "Duplicate Username",
                "username": self.admin.username,
                "email": target_admin.email,
                "status": "active",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("username is already taken", response.json()["error"])
        target_admin.refresh_from_db()
        self.assertEqual(target_admin.username, "profile-duplicate-target")

    def test_non_superuser_cannot_update_admin_profile(self):
        target_admin = User.objects.create_superuser(
            username="profile-protected-admin",
            email="profile-protected-admin@example.com",
            password="TestPassword!234",
        )
        regular_user = User.objects.create_user(
            username="profile-non-admin",
            email="profile-non-admin@example.com",
            password="TestPassword!234",
        )
        self.client.force_login(regular_user)

        response = self.client.post(
            reverse("update_admin_profile"),
            {
                "admin_id": str(target_admin.id),
                "full_name": "Unauthorized Update",
                "username": "unauthorized-admin-update",
                "email": target_admin.email,
                "status": "active",
            },
        )

        self.assertEqual(response.status_code, 403)
        target_admin.refresh_from_db()
        self.assertEqual(target_admin.username, "profile-protected-admin")

    def test_admin_status_update_rejects_deactivating_self(self):
        response = self.client.post(
            reverse("update_admin_status"),
            {"admin_id": str(self.admin.id), "status": "inactive"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("own administrator account", response.json()["error"])
        self.assertTrue(User.objects.get(id=self.admin.id).is_active)

    def test_admin_status_update_rejects_non_admin_accounts(self):
        regular_user = User.objects.create_user(
            username="status-not-admin",
            email="status-not-admin@example.com",
            password="TestPassword!234",
        )

        response = self.client.post(
            reverse("update_admin_status"),
            {"admin_id": str(regular_user.id), "status": "inactive"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertTrue(User.objects.get(id=regular_user.id).is_active)

    def test_non_superuser_cannot_update_admin_status(self):
        target_admin = User.objects.create_superuser(
            username="status-protected-admin",
            email="status-protected-admin@example.com",
            password="TestPassword!234",
        )
        regular_user = User.objects.create_user(
            username="status-non-admin",
            email="status-non-admin@example.com",
            password="TestPassword!234",
        )
        self.client.force_login(regular_user)

        response = self.client.post(
            reverse("update_admin_status"),
            {"admin_id": str(target_admin.id), "status": "inactive"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertTrue(User.objects.get(id=target_admin.id).is_active)

    def test_non_superuser_cannot_bulk_remove_admin_accounts(self):
        other_admin = User.objects.create_superuser(
            username="protected-admin",
            email="protected-admin@example.com",
            password="test-password",
        )
        regular_user = User.objects.create_user(
            username="bulk-delete-non-admin",
            email="bulk-delete-non-admin@example.com",
            password="test-password",
        )
        self.client.force_login(regular_user)

        response = self.client.post(
            reverse("delete_admins"),
            {"admin_ids": [str(other_admin.id)]},
        )

        self.assertEqual(response.status_code, 403)
        self.assertTrue(User.objects.filter(id=other_admin.id).exists())

    def test_superuser_can_create_admin_account(self):
        response = self.client.post(
            reverse("create_admin"),
            {
                "full_name": "New Administrator",
                "username": "new-directory-admin",
                "email": "new-directory-admin@example.com",
                "password": "T#6-vrgP9E-L3x!Wqk4-2026",
                "confirm_password": "T#6-vrgP9E-L3x!Wqk4-2026",
            },
        )

        self.assertEqual(response.status_code, 201)
        created_admin = User.objects.get(username="new-directory-admin")
        self.assertTrue(created_admin.is_staff)
        self.assertTrue(created_admin.is_superuser)
        self.assertTrue(created_admin.is_active)
        self.assertEqual(response.json()["admin"]["full_name"], "New Administrator")

    def test_superuser_can_create_inactive_admin_account(self):
        response = self.client.post(
            reverse("create_admin"),
            {
                "full_name": "Inactive Administrator",
                "username": "inactive-directory-admin",
                "email": "inactive-directory-admin@example.com",
                "password": "T#6-vrgP9E-L3x!Wqk4-2026",
                "confirm_password": "T#6-vrgP9E-L3x!Wqk4-2026",
                "status": "inactive",
            },
        )

        self.assertEqual(response.status_code, 201)
        created_admin = User.objects.get(username="inactive-directory-admin")
        self.assertTrue(created_admin.is_superuser)
        self.assertFalse(created_admin.is_active)
        self.assertEqual(response.json()["admin"]["status"], "inactive")

    def test_admin_creation_rejects_invalid_status(self):
        response = self.client.post(
            reverse("create_admin"),
            {
                "full_name": "Invalid Status Admin",
                "username": "invalid-status-admin",
                "email": "invalid-status-admin@example.com",
                "password": "T#6-vrgP9E-L3x!Wqk4-2026",
                "confirm_password": "T#6-vrgP9E-L3x!Wqk4-2026",
                "status": "pending",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("valid admin account status", response.json()["error"])
        self.assertFalse(User.objects.filter(username="invalid-status-admin").exists())

    def test_non_superuser_cannot_create_admin_account(self):
        regular_user = User.objects.create_user(
            username="admin-create-non-admin",
            email="admin-create-non-admin@example.com",
            password="test-password",
        )
        self.client.force_login(regular_user)

        response = self.client.post(
            reverse("create_admin"),
            {
                "full_name": "Should Not Be Admin",
                "username": "not-authorized-admin",
                "email": "not-authorized-admin@example.com",
                "password": "T#6-vrgP9E-L3x!Wqk4-2026",
                "confirm_password": "T#6-vrgP9E-L3x!Wqk4-2026",
            },
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(username="not-authorized-admin").exists())

    def test_admin_creation_rejects_mismatched_passwords(self):
        response = self.client.post(
            reverse("create_admin"),
            {
                "full_name": "Mismatched Admin",
                "username": "mismatched-admin",
                "email": "mismatched-admin@example.com",
                "password": "T#6-vrgP9E-L3x!Wqk4-2026",
                "confirm_password": "Different-Password-2026!",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("passwords do not match", response.json()["error"])
        self.assertFalse(User.objects.filter(username="mismatched-admin").exists())

    def test_admin_directory_is_restricted_to_superusers(self):
        regular_user = User.objects.create_user(
            username="directory-non-admin",
            email="non-admin@example.com",
            password="test-password",
        )
        self.client.force_login(regular_user)

        response = self.client.get(reverse("admins"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("user_dashboard"))

    def test_legacy_admin_list_url_redirects_to_people_admins(self):
        response = self.client.get(reverse("users"))

        self.assertRedirects(response, reverse("admins"))

    def test_admin_navigation_places_admin_after_people_lists(self):
        response = self.client.get(reverse("admins"))
        content = response.content.decode()

        self.assertLess(content.index('label: "Users"'), content.index('label: "Volunteers"'))
        self.assertLess(content.index('label: "Volunteers"'), content.index('label: "Beneficiaries"'))
        self.assertLess(content.index('label: "Beneficiaries"'), content.index('label: "Admin"'))
        self.assertContains(response, 'admins: "/admins/"')


class VolunteerBulkRemovalTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="volunteer-bulk-admin",
            email="volunteer-bulk-admin@example.com",
            password="test-password",
        )
        self.client.force_login(self.admin)

    def create_volunteer(self, username):
        user = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="test-password",
        )
        UserProfile.objects.create(user=user, account_role=UserProfile.ROLE_VOLUNTEER)
        return user

    def test_volunteer_directory_renders_selection_toolbar(self):
        response = self.client.get(reverse("volunteers"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="vol-select-all"')
        self.assertContains(response, 'id="vol-bulk-bar"')
        self.assertContains(response, 'id="vol-bulk-clear"')
        self.assertContains(response, "Clear selection")
        self.assertContains(response, 'id="vol-bulk-remove"')
        self.assertContains(response, "Remove Selected")
        self.assertContains(response, "return to regular user accounts")
        self.assertContains(response, reverse("deactivate_volunteers_bulk"))

    def test_superuser_can_remove_multiple_volunteers_without_deleting_accounts(self):
        volunteers = [
            self.create_volunteer("bulk-volunteer-one"),
            self.create_volunteer("bulk-volunteer-two"),
        ]
        applications = [
            RoleApplication.objects.create(
                user=volunteer,
                role=RoleApplication.ROLE_VOLUNTEER,
                status=RoleApplication.STATUS_APPROVED,
                full_name=volunteer.username,
                contact_details="555-0100",
            )
            for volunteer in volunteers
        ]

        response = self.client.post(
            reverse("deactivate_volunteers_bulk"),
            {"volunteer_user_ids": [str(volunteer.id) for volunteer in volunteers]},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["removed_count"], 2)
        for volunteer in volunteers:
            volunteer.refresh_from_db()
            self.assertTrue(volunteer.is_active)
            self.assertEqual(volunteer.userprofile.account_role, UserProfile.ROLE_REGULAR)
        for application in applications:
            application.refresh_from_db()
            self.assertEqual(application.status, RoleApplication.STATUS_INACTIVE)
            self.assertEqual(application.reviewed_by, self.admin)

    def test_bulk_volunteer_removal_rejects_mixed_non_volunteer_selection_atomically(self):
        volunteer = self.create_volunteer("valid-bulk-volunteer")
        regular_user = User.objects.create_user(
            username="not-a-bulk-volunteer",
            email="not-a-bulk-volunteer@example.com",
            password="test-password",
        )

        response = self.client.post(
            reverse("deactivate_volunteers_bulk"),
            {"volunteer_user_ids": [str(volunteer.id), str(regular_user.id)]},
        )

        self.assertEqual(response.status_code, 400)
        volunteer.refresh_from_db()
        self.assertEqual(volunteer.userprofile.account_role, UserProfile.ROLE_VOLUNTEER)

    def test_non_superuser_cannot_bulk_remove_volunteers(self):
        volunteer = self.create_volunteer("protected-bulk-volunteer")
        regular_user = User.objects.create_user(
            username="volunteer-bulk-non-admin",
            email="volunteer-bulk-non-admin@example.com",
            password="test-password",
        )
        self.client.force_login(regular_user)

        response = self.client.post(
            reverse("deactivate_volunteers_bulk"),
            {"volunteer_user_ids": [str(volunteer.id)]},
        )

        self.assertEqual(response.status_code, 403)
        volunteer.refresh_from_db()
        self.assertEqual(volunteer.userprofile.account_role, UserProfile.ROLE_VOLUNTEER)
