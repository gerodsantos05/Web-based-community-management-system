from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Donation


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

    def test_anonymous_donation_is_pending_and_stores_no_name(self):
        response = self.client.post(
            reverse("submit_donation"),
            {
                "amount": "300",
                "payment_method": Donation.PAYMENT_GCASH,
                "donor_name": "Anonymous",
                "donor_message": "Please help.",
                "receipt": self.receipt(),
            },
        )
        self.assertEqual(response.status_code, 201)
        donation = Donation.objects.get()
        self.assertIsNone(donation.user)
        self.assertEqual(donation.donor_name, "")
        self.assertEqual(donation.status, Donation.STATUS_PENDING)
        self.assertTrue(donation.receipt.name.startswith("donations/user_anonymous/"))
        self.assertNotIn(".", donation.receipt.name.rsplit("/", 1)[-1])

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
