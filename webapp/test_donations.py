from django.contrib.auth.models import User
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import Sum
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Activity, ActivityFundAllocation, Donation, ItemPledge


@override_settings(
    DONATION_RECEIPT_MAX_SIZE_BYTES=5 * 1024 * 1024,
    DONATION_RECEIPT_MIME_TYPES={"image/jpeg", "application/pdf", "image/png", "image/webp"},
)
class DonationFunnelTests(TestCase):
    def receipt(self, name="receipt.jpg", content=b"\xff\xd8\xff\xe0receipt", content_type="image/jpeg"):
        return SimpleUploadedFile(name, content, content_type=content_type)

    def test_donate_page_uses_standalone_template(self):
        response = self.client.get(reverse("donate"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your kindness, in action.")
        self.assertContains(response, 'id="give"')
        self.assertContains(response, "Give any amount that feels right for you.")
        self.assertContains(response, "School supply set")
        self.assertContains(response, 'aria-label="Program categories"')
        self.assertContains(response, 'background:#5c8d68')
        self.assertContains(response, 'background:#d28757')
        self.assertContains(response, 'background:#6885a0')
        self.assertNotContains(response, "Out of every")
        self.assertNotContains(response, "₱40")
        self.assertNotContains(response, "₱300")
        self.assertNotContains(response, "₱1000")
        self.assertContains(response, "Cash (GCash / Bank)")
        self.assertContains(response, "Item / In-kind")
        self.assertContains(response, "Sample address:")
        self.assertContains(response, "Submit your transfer receipt so the team can review your gift.")
        self.assertContains(response, "Add a note or photo (optional)")
        self.assertContains(response, "Check accepted item guidelines")
        self.assertContains(response, "Review your details")
        self.assertContains(response, "Name (optional)")
        self.assertContains(response, "Thank you for sharing with our community.")
        self.assertContains(response, "Our team will be in touch soon to coordinate the next steps.")
        self.assertContains(response, 'id="donationTrackerTrigger"')
        self.assertContains(response, 'id="donationTrackerModal"')
        self.assertContains(response, "Needs attention")
        self.assertContains(response, 'data-donation-filter="pending" class="active" aria-pressed="true"')
        self.assertContains(response, 'id="pledgeThankYouItem"')
        self.assertNotContains(response, "donateStartOver")
        self.assertNotContains(response, "pledgeStartOver")
        self.assertNotContains(response, "pledgeReference")
        self.assertNotContains(response, "Your item is not yet marked as received.")

    def test_anonymous_donation_without_name_is_pending_and_stores_no_name(self):
        response = self.client.post(
            reverse("submit_donation"),
            {
                "amount": "300",
                "payment_method": Donation.PAYMENT_GCASH,
                "donor_name": "",
                "donor_message": "Please help.",
                "receipt": self.receipt(),
            },
        )
        self.assertEqual(response.status_code, 201)
        donation = Donation.objects.get()
        self.assertIsNone(donation.user)
        self.assertEqual(donation.donor_name, "")
        self.assertEqual(donation.status, Donation.STATUS_PENDING)
        self.assertEqual(donation.tracking_token, self.client.cookies["donation_tracker_id"].value)
        self.assertTrue(donation.receipt.name.startswith("donations/user_anonymous/"))
        self.assertNotIn(".", donation.receipt.name.rsplit("/", 1)[-1])

    def test_anonymous_donor_name_is_saved_for_receipt(self):
        response = self.client.post(
            reverse("submit_donation"),
            {
                "amount": "300",
                "payment_method": Donation.PAYMENT_GCASH,
                "donor_name": "Kind Anonymous Donor",
                "receipt": self.receipt(),
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Donation.objects.get().donor_name, "Kind Anonymous Donor")

    def test_invalid_receipt_is_rejected(self):
        response = self.client.post(
            reverse("submit_donation"),
            {
                "amount": "100",
                "payment_method": Donation.PAYMENT_BANK_TRANSFER,
                "receipt": self.receipt(content=b"not an image"),
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Donation.objects.count(), 0)

    @override_settings(
        DONATION_PLEDGE_NOTIFICATION_EMAIL="team@example.com",
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    )
    def test_item_pledge_is_saved_separately_as_pledged_and_notifies_team(self):
        response = self.client.post(
            reverse("submit_item_pledge"),
            {
                "item_name": "School notebooks",
                "category": ItemPledge.CATEGORY_SCHOOL_SUPPLIES,
                "quantity": "12",
                "condition": ItemPledge.CONDITION_NEW,
                "description": "Unused notebooks",
                "delivery_method": ItemPledge.DELIVERY_DROP_OFF,
                "donor_name": "Helpful Donor",
                "donor_phone": "09171234567",
                "donor_email": "donor@example.com",
            },
        )

        self.assertEqual(response.status_code, 201)
        pledge = ItemPledge.objects.get()
        self.assertTrue(pledge.reference_number.startswith("IP-"))
        self.assertEqual(pledge.status, ItemPledge.STATUS_PLEDGED)
        self.assertEqual(pledge.donor_name, "Helpful Donor")
        self.assertEqual(Donation.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["team@example.com"])
        self.assertIn(pledge.reference_number, mail.outbox[0].body)

    def test_anonymous_pickup_pledge_requires_and_saves_delivery_details(self):
        response = self.client.post(
            reverse("submit_item_pledge"),
            {
                "item_name": "Warm jackets",
                "category": ItemPledge.CATEGORY_CLOTHING,
                "quantity": "2",
                "condition": ItemPledge.CONDITION_USED,
                "delivery_method": ItemPledge.DELIVERY_PICKUP,
                "delivery_address": "12 Sample Street",
                "preferred_date": "2026-11-10",
                "preferred_time": "10:30",
                "is_anonymous": "true",
                "donor_name": "",
                "donor_phone": "09171234567",
                "donor_email": "anonymous@example.com",
            },
        )

        self.assertEqual(response.status_code, 201)
        pledge = ItemPledge.objects.get()
        self.assertTrue(pledge.is_anonymous)
        self.assertEqual(pledge.donor_name, "")
        self.assertEqual(pledge.delivery_address, "12 Sample Street")
        self.assertEqual(pledge.preferred_date.isoformat(), "2026-11-10")
        self.assertEqual(pledge.preferred_time.strftime("%H:%M"), "10:30")

    def test_invalid_item_pledge_delivery_is_rejected(self):
        response = self.client.post(
            reverse("submit_item_pledge"),
            {
                "item_name": "Rice",
                "category": ItemPledge.CATEGORY_FOOD,
                "quantity": "1",
                "condition": ItemPledge.CONDITION_NEW,
                "delivery_method": ItemPledge.DELIVERY_PICKUP,
                "donor_name": "Donor",
                "donor_phone": "09171234567",
                "donor_email": "donor@example.com",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(ItemPledge.objects.count(), 0)

    def test_item_pledge_name_is_optional_without_anonymous_checkbox(self):
        response = self.client.post(
            reverse("submit_item_pledge"),
            {
                "item_name": "Canned goods",
                "category": ItemPledge.CATEGORY_FOOD,
                "quantity": "3",
                "condition": ItemPledge.CONDITION_NEW,
                "delivery_method": ItemPledge.DELIVERY_DROP_OFF,
                "donor_name": "",
                "donor_phone": "09171234567",
                "donor_email": "donor@example.com",
            },
        )

        self.assertEqual(response.status_code, 201)
        pledge = ItemPledge.objects.get()
        self.assertEqual(pledge.donor_name, "")
        self.assertTrue(pledge.is_anonymous)

    def test_admin_can_review_and_update_item_pledge_status_separately(self):
        pledge = ItemPledge.objects.create(
            item_name="Rice",
            category=ItemPledge.CATEGORY_FOOD,
            quantity=2,
            condition=ItemPledge.CONDITION_NEW,
            delivery_method=ItemPledge.DELIVERY_DROP_OFF,
            donor_phone="09171234567",
            donor_email="donor@example.com",
        )
        admin = User.objects.create_superuser(
            username="item-pledge-admin",
            email="item-pledge-admin@example.com",
            password="test-password",
        )
        self.client.force_login(admin)

        dashboard = self.client.get(reverse("donations"))
        self.assertContains(dashboard, "Item / In-kind Pledges")
        self.assertContains(dashboard, "Pending")
        self.assertNotContains(dashboard, "Mark as Pledged")
        self.assertContains(dashboard, pledge.reference_number)
        for column in ("Item name", "Type", "Quantity", "Condition", "Donor name", "Phone", "Email"):
            self.assertContains(dashboard, f"<th scope=\"col\">{column}</th>", html=True)
        self.assertContains(dashboard, 'data-open-pledge-actions="1"')
        self.assertContains(dashboard, 'data-pledge-status-url="/donations/items/1/status/"')
        self.assertNotContains(dashboard, "Save status")
        self.assertNotContains(dashboard, "Donor contact")

        response = self.client.post(
            reverse("update_item_pledge_status", args=[pledge.id]),
            {"status": ItemPledge.STATUS_SCHEDULED},
        )
        self.assertEqual(response.status_code, 302)
        pledge.refresh_from_db()
        self.assertEqual(pledge.status, ItemPledge.STATUS_SCHEDULED)

    def test_logged_in_donor_name_is_saved_only_when_provided(self):
        user = User.objects.create_user(username="donor", password="password123")
        self.client.force_login(user)
        response = self.client.post(
            reverse("submit_donation"),
            {
                "amount": "500",
                "payment_method": Donation.PAYMENT_GCASH,
                "donor_name": "Kind Donor",
                "receipt": self.receipt("receipt.png", b"\x89PNG\r\n\x1a\nreceipt", "image/png"),
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Donation.objects.get().donor_name, "Kind Donor")

    def test_activity_fund_reservations_use_completed_donations_only(self):
        admin = User.objects.create_superuser(username="admin-fund-check", email="admin-fund-check@example.com", password="password123")
        self.client.force_login(admin)

        Donation.objects.create(
            user=admin,
            donor_name="Kind Donor",
            amount=1500,
            payment_method=Donation.PAYMENT_GCASH,
            receipt=self.receipt("donation-1.png", b"\x89PNG\r\n\x1a\nreceipt", "image/png"),
            status=Donation.STATUS_COMPLETED,
        )
        donation_two = Donation.objects.create(
            user=admin,
            donor_name="Another Donor",
            amount=800,
            payment_method=Donation.PAYMENT_GCASH,
            receipt=self.receipt("donation-2.png", b"\x89PNG\r\n\x1a\nreceipt", "image/png"),
            status=Donation.STATUS_COMPLETED,
        )

        response = self.client.post(
            reverse("add_activity"),
            {
                "title": "Community Meal Drive",
                "date": "2026-11-20",
                "time": "09:00",
                "location": "Maliksi II",
                "category": "outreach",
                "status": Activity.STATUS_ACTIVE,
                "description": "Meal drive for beneficiaries",
                "use_funds_held": "1",
                "funds_held_amount": "1500",
            },
        )
        self.assertEqual(response.status_code, 302)
        activity = Activity.objects.get(title="Community Meal Drive")
        self.assertTrue(ActivityFundAllocation.objects.filter(activity=activity, amount=1500).exists())

        response = self.client.post(
            reverse("add_activity"),
            {
                "title": "Community Skills Workshop",
                "date": "2026-11-21",
                "time": "10:00",
                "location": "Maliksi II",
                "category": "outreach",
                "status": Activity.STATUS_ACTIVE,
                "description": "Skills workshop",
                "use_funds_held": "1",
                "funds_held_amount": "1000",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Activity.objects.filter(title="Community Skills Workshop").exists())
        self.assertEqual(ActivityFundAllocation.objects.filter(activity=activity).aggregate(total=Sum("amount"))["total"] or 0, 1500)

    def test_donation_tracker_lists_both_kinds_only_for_matching_browser(self):
        browser_token = "a" * 43
        Donation.objects.create(
            tracking_token=browser_token,
            donor_name="Private donor",
            amount=750,
            payment_method=Donation.PAYMENT_CASH,
            status=Donation.STATUS_PENDING,
        )
        ItemPledge.objects.create(
            tracking_token=browser_token,
            item_name="School notebooks",
            category=ItemPledge.CATEGORY_SCHOOL_SUPPLIES,
            quantity=3,
            condition=ItemPledge.CONDITION_NEW,
            delivery_method=ItemPledge.DELIVERY_DROP_OFF,
            donor_phone="09171234567",
            donor_email="private@example.com",
            status=ItemPledge.STATUS_SCHEDULED,
        )
        Donation.objects.create(
            tracking_token="b" * 43,
            amount=100,
            payment_method=Donation.PAYMENT_CASH,
        )
        self.client.cookies["donation_tracker_id"] = browser_token

        response = self.client.post(reverse("donation_tracker"))

        self.assertEqual(response.status_code, 200)
        records = response.json()["donations"]
        self.assertEqual({record["kind"] for record in records}, {"cash", "item"})
        self.assertEqual(
            {record["status"] for record in records},
            {Donation.STATUS_PENDING, ItemPledge.STATUS_SCHEDULED},
        )
        item_record = next(record for record in records if record["kind"] == "item")
        self.assertEqual(item_record["image"], "/static/media/default-donation-receipt.svg")
        self.assertEqual(item_record["imageAlt"], "No item photo provided")
        self.assertNotIn("private@example.com", str(records))

    def test_donation_tracker_includes_signed_in_user_history(self):
        donor = User.objects.create_user(username="tracker-donor", password="test-password")
        other_donor = User.objects.create_user(username="other-tracker-donor", password="test-password")
        Donation.objects.create(
            user=donor,
            amount=300,
            payment_method=Donation.PAYMENT_CASH,
            status=Donation.STATUS_COMPLETED,
        )
        ItemPledge.objects.create(
            user=donor,
            item_name="Rice",
            category=ItemPledge.CATEGORY_FOOD,
            quantity=1,
            condition=ItemPledge.CONDITION_NEW,
            delivery_method=ItemPledge.DELIVERY_DROP_OFF,
            donor_phone="09171234567",
            donor_email="donor@example.com",
            status=ItemPledge.STATUS_RECEIVED,
        )
        Donation.objects.create(
            user=other_donor,
            amount=900,
            payment_method=Donation.PAYMENT_CASH,
        )
        self.client.force_login(donor)

        response = self.client.post(reverse("donation_tracker"))

        self.assertEqual(response.status_code, 200)
        records = response.json()["donations"]
        self.assertEqual(len(records), 2)
        self.assertEqual({record["status"] for record in records}, {"completed", "received"})
