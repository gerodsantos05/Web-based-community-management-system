from datetime import date

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings

from .email_utils import HAPPYNESS_LOGO_CID
from .views import _send_volunteer_assignment_email


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="HappYness Project <no-reply@example.com>",
)
class VolunteerAssignmentEmailTests(TestCase):
    def test_assignment_email_contains_branded_html_and_inline_logo(self):
        volunteer = User.objects.create_user(
            username="volunteer-email-test",
            email="volunteer@example.com",
            first_name="Casey",
            last_name="Volunteer",
        )

        sent = _send_volunteer_assignment_email(
            volunteer,
            "Community Garden Day",
            date(2026, 8, 14),
        )

        self.assertTrue(sent)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.subject, "New task assignment: Community Garden Day")
        self.assertIn("Community Garden Day", message.body)
        self.assertIn("Aug 14, 2026", message.body)
        self.assertEqual(len(message.alternatives), 1)
        html_email = message.alternatives[0][0]
        self.assertIn(f'src="cid:{HAPPYNESS_LOGO_CID}"', html_email)
        self.assertIn("HAPPYNESS PROJECT", html_email)
        self.assertIn("Casey Volunteer", html_email)
        self.assertEqual(len(message.attachments), 1)
        self.assertEqual(message.attachments[0].get("Content-ID"), f"<{HAPPYNESS_LOGO_CID}>")
