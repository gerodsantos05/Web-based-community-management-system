from django.test import SimpleTestCase
from django.template.loader import render_to_string
from django.urls import reverse


class PublicInformationPagesTests(SimpleTestCase):
    def test_privacy_policy_page_displays_policy_content(self):
        response = self.client.get(reverse("privacy_policy"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "PRIVACY POLICY")
        self.assertContains(response, "Last updated: January 2026")
        self.assertContains(response, "National Privacy Commission")
        self.assertContains(response, "HappynessProjectPhilippines@gmail.com")

    def test_public_footer_opens_policy_in_the_same_tab(self):
        footer = render_to_string("partials/_public_footer.html")

        self.assertIn(
            f'<a href="{reverse("privacy_policy")}">Privacy Policy</a>',
            footer,
        )

    def test_faq_page_displays_questions_with_shared_header(self):
        response = self.client.get(reverse("faq"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Frequently Asked Questions")
        self.assertContains(response, "What is HappYness Project Organization Inc.?")
        self.assertContains(response, "Programs &amp; Beneficiaries")
        self.assertContains(response, "← Back to home")

    def test_public_footer_links_to_faq_page_in_the_same_tab(self):
        footer = render_to_string("partials/_public_footer.html")

        self.assertIn(f'<a href="{reverse("faq")}">FAQ</a>', footer)
