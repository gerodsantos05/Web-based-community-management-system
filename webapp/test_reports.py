from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    AdminSystemSettings,
    Donation,
    InventoryItem,
    ItemPledge,
    ProductInquiry,
    StockMovement,
    UserProfile,
    VolunteerActivityAssignment,
    VolunteerAttendanceRecord,
)


class ReportsPageTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="reports-test-admin",
            email="reports-test-admin@example.com",
            password="test-password",
        )
        self.client.force_login(self.admin)

    def _create_item_pledge(self, status, name="Rice", category=ItemPledge.CATEGORY_FOOD, quantity=10):
        return ItemPledge.objects.create(
            item_name=name,
            category=category,
            quantity=quantity,
            condition=ItemPledge.CONDITION_NEW,
            delivery_method=ItemPledge.DELIVERY_DROP_OFF,
            donor_name="Report donor",
            donor_phone="09170000000",
            donor_email="report-donor@example.com",
            status=status,
        )

    def test_overview_and_all_detail_pages_render(self):
        response = self.client.get(reverse("reports"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Finalized donations")
        self.assertContains(response, 'href="/reports/donations/"')
        self.assertContains(response, "View donations")
        self.assertContains(response, "View all records")
        self.assertContains(
            response,
            "Every record type in one list: donations, activities, volunteer hours, assistance and product sales",
        )
        self.assertEqual(len(response.context["overview_cards"]), 7)
        self.assertTrue(response.context["overview_cards"][-1]["is_all_records"])

        for slug in (
            "donations",
            "volunteer-hours",
            "activities",
            "assistance",
            "product-sales",
            "accounts",
            "all-records",
        ):
            detail = self.client.get(reverse("reports_detail", kwargs={"report": slug}))
            self.assertEqual(detail.status_code, 200)
            self.assertContains(detail, "Back to Reports")
            self.assertRegex(
                detail.content.decode(),
                r'<h1 class="truncate text-lg font-semibold text-ink-900">\s*Reports\s*</h1>',
            )
            self.assertContains(detail, "Analyze activity and outcomes")

    def test_donations_report_counts_only_completed_cash_and_received_in_kind(self):
        Donation.objects.create(
            donor_name="Cash donor",
            campaign="Spring",
            amount=500,
            payment_method=Donation.PAYMENT_CASH,
            reference_number="REPORT-CASH-1",
            status=Donation.STATUS_COMPLETED,
            created_at=timezone.now() - timedelta(days=5),
        )
        self._create_item_pledge(ItemPledge.STATUS_RECEIVED, quantity=20)
        self._create_item_pledge(ItemPledge.STATUS_PLEDGED, name="Pending rice", quantity=80)

        response = self.client.get(reverse("reports_data_api"), {
            "report": "donations",
            "range": "30d",
            "donation_type": "in_kind",
        })
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["totals"]["cash_amount"], 0)
        self.assertEqual(payload["totals"]["in_kind_count"], 1)
        self.assertEqual(payload["totals"]["items_received"], 20)
        self.assertEqual(payload["rows"][0][3], "Rice · Report donor")
        self.assertNotIn("₱", payload["rows"][0][4])

    def test_donation_type_filters_separate_cash_gcash_bank_and_in_kind(self):
        Donation.objects.create(
            donor_name="Cash donor",
            amount=100,
            payment_method=Donation.PAYMENT_CASH,
            reference_number="REPORT-TYPE-CASH",
            status=Donation.STATUS_COMPLETED,
        )
        Donation.objects.bulk_create([
            Donation(
                donor_name="GCash donor",
                amount=200,
                payment_method=Donation.PAYMENT_GCASH,
                reference_number="REPORT-TYPE-GCASH",
                status=Donation.STATUS_COMPLETED,
            ),
            Donation(
                donor_name="Bank donor",
                amount=300,
                payment_method=Donation.PAYMENT_BANK_TRANSFER,
                reference_number="REPORT-TYPE-BANK",
                status=Donation.STATUS_COMPLETED,
            ),
        ])
        self._create_item_pledge(ItemPledge.STATUS_RECEIVED, name="Rice", quantity=12)

        options = self.client.get(reverse("reports_data_api"), {
            "report": "donations",
            "range": "all",
        }).json()["options"]["donation_types"]
        self.assertEqual(
            [(option["value"], option["label"]) for option in options],
            [("all", "All"), ("cash", "Cash"), ("gcash", "GCash"), ("bank", "Bank"), ("in_kind", "In-kind")],
        )
        all_types = self.client.get(reverse("reports_data_api"), {
            "report": "donations",
            "range": "all",
            "donation_type": "all",
        }).json()
        self.assertEqual(all_types["totals"]["cash_amount"], 600)
        self.assertEqual(all_types["totals"]["cash_count"], 3)
        self.assertEqual(all_types["totals"]["in_kind_count"], 1)
        self.assertEqual(all_types["totals"]["items_received"], 12)
        self.assertEqual(
            {row[1] for row in all_types["rows"]},
            {"Cash", "GCash", "Bank", "In-kind"},
        )
        self.assertEqual(
            all_types["distribution"]["labels"],
            ["Cash", "GCash", "Bank", "Other methods", "In-kind"],
        )
        self.assertEqual(all_types["distribution"]["values"], [1, 1, 1, 0, 1])

        for donation_type, amount, label in (
            ("cash", 100, "Cash"),
            ("gcash", 200, "GCash"),
            ("bank", 300, "Bank"),
        ):
            with self.subTest(donation_type=donation_type):
                payload = self.client.get(reverse("reports_data_api"), {
                    "report": "donations",
                    "range": "all",
                    "donation_type": donation_type,
                }).json()
                self.assertEqual(payload["totals"]["cash_amount"], amount)
                self.assertEqual(payload["rows"][0][1], label)
                self.assertEqual(payload["totals"]["in_kind_count"], 0)

        in_kind = self.client.get(reverse("reports_data_api"), {
            "report": "donations",
            "range": "all",
            "donation_type": "in_kind",
        }).json()
        self.assertEqual(in_kind["totals"]["cash_amount"], 0)
        self.assertEqual(in_kind["totals"]["in_kind_count"], 1)
        self.assertEqual(in_kind["rows"][0][1], "In-kind")

    def test_volunteer_report_lists_attendance_hours_for_ojt_and_community(self):
        ojt = User.objects.create_user(
            username="reports-ojt-volunteer",
            first_name="OJT",
            last_name="Volunteer",
            email="reports-ojt@example.com",
            password="test-password",
        )
        community = User.objects.create_user(
            username="reports-community-volunteer",
            first_name="Community",
            last_name="Volunteer",
            email="reports-community@example.com",
            password="test-password",
        )
        UserProfile.objects.create(
            user=ojt,
            account_role=UserProfile.ROLE_VOLUNTEER,
            volunteer_type=UserProfile.VOLUNTEER_TYPE_OJT,
            ojt_hours=18,
            required_ojt_hours=100,
        )
        UserProfile.objects.create(
            user=community,
            account_role=UserProfile.ROLE_VOLUNTEER,
            volunteer_type=UserProfile.VOLUNTEER_TYPE_COMMUNITY,
            ojt_hours=0,
            required_ojt_hours=80,
        )
        now = timezone.now()
        for volunteer, activity_name, minutes in (
            (ojt, "OJT assignment", 60),
            (community, "Community assignment", 90),
        ):
            assignment = VolunteerActivityAssignment.objects.create(
                volunteer=volunteer,
                activity_name=activity_name,
                scheduled_date=timezone.localdate(),
                status=VolunteerActivityAssignment.STATUS_COMPLETED,
            )
            VolunteerAttendanceRecord.objects.create(
                volunteer=volunteer,
                assignment=assignment,
                time_out=now,
                duration_minutes=minutes,
                status=VolunteerAttendanceRecord.STATUS_CONFIRMED,
            )

        payload = self.client.get(reverse("reports_data_api"), {
            "report": "volunteer-hours",
            "range": "all",
        }).json()

        self.assertEqual(payload["distribution"]["type"], "bar")
        self.assertEqual(payload["distribution"]["title"], "Volunteer hours by volunteer")
        self.assertEqual(
            [(option["value"], option["label"]) for option in payload["options"]["volunteer_types"]],
            [("all", "All"), ("ojt", "OJT Volunteer"), ("community", "Community Volunteer")],
        )
        self.assertEqual(
            payload["distribution"]["labels"],
            ["Community Volunteer (Community)", "OJT Volunteer (OJT)"],
        )
        self.assertEqual(payload["distribution"]["values"], [1.5, 1.0])
        self.assertEqual(payload["totals"]["hours"], 2.5)
        self.assertEqual(payload["totals"]["ojt_completed_hours"], 18)
        self.assertEqual(payload["totals"]["ojt_required_hours"], 100)
        self.assertEqual(payload["totals"]["ojt_volunteers"], 1)
        ojt_stat = next(stat for stat in payload["stats"] if stat["label"] == "OJT progress")
        self.assertEqual(ojt_stat["value"], "18.0h")
        self.assertIn("1 active OJT volunteers", ojt_stat["note"])

        ojt_payload = self.client.get(reverse("reports_data_api"), {
            "report": "volunteer-hours",
            "range": "all",
            "volunteer_type": "ojt",
        }).json()
        self.assertEqual(ojt_payload["totals"]["hours"], 1.0)
        self.assertEqual(ojt_payload["totals"]["volunteers"], 1)
        self.assertEqual(ojt_payload["distribution"]["labels"], ["OJT Volunteer (OJT)"])
        self.assertTrue(any(stat["label"] == "OJT progress" for stat in ojt_payload["stats"]))

        community_payload = self.client.get(reverse("reports_data_api"), {
            "report": "volunteer-hours",
            "range": "all",
            "volunteer_type": "community",
        }).json()
        self.assertEqual(community_payload["totals"]["hours"], 1.5)
        self.assertEqual(community_payload["totals"]["volunteers"], 1)
        self.assertEqual(community_payload["distribution"]["labels"], ["Community Volunteer (Community)"])
        self.assertFalse(any(stat["label"] == "OJT progress" for stat in community_payload["stats"]))

        pdf_response = self.client.post(reverse("reports_export"), {
            "report": "volunteer-hours",
            "range": "all",
            "volunteer_type": "community",
            "format": "pdf",
        })
        self.assertEqual(pdf_response.status_code, 200)
        self.assertTrue(pdf_response.content.startswith(b"%PDF"))

    def test_completed_product_orders_are_ranked_and_filterable(self):
        buyer = User.objects.create_user(username="reports-test-buyer", password="test-password")
        common = {
            "user": buyer,
            "full_name": "Buyer",
            "email": "buyer@example.com",
            "phone": "09170000001",
            "payment_method": ProductInquiry.PAYMENT_CARD,
            "admin_notification": "Test report order",
        }
        ProductInquiry.objects.create(
            **common,
            order_items=[
                {"name": "Tote Bag", "category": "Tote Bags", "quantity": 4, "unit_price": 100},
                {"name": "Doormat", "category": "Doormats", "quantity": 2, "unit_price": 100},
            ],
            order_total=600,
            status=ProductInquiry.STATUS_COMPLETED,
        )
        ProductInquiry.objects.create(
            **common,
            order_items=[{"name": "Tote Bag", "category": "Tote Bags", "quantity": 20, "unit_price": 100}],
            order_total=2000,
            status=ProductInquiry.STATUS_PENDING,
        )

        response = self.client.get(reverse("reports_data_api"), {
            "report": "product-sales",
            "range": "30d",
            "category": "Tote Bags",
        })
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["totals"]["quantity_sold"], 4)
        self.assertEqual(payload["totals"]["revenue"], "₱400.00")
        self.assertEqual(payload["rows"][0], ["1", "Tote Bag", "Tote Bags", "₱100.00", "4"])
        self.assertEqual(payload["distribution"]["values"], [4])

    def test_all_records_uses_transaction_dates_for_product_sale_rows(self):
        buyer = User.objects.create_user(username="reports-all-record-buyer", password="test-password")
        ProductInquiry.objects.create(
            user=buyer,
            full_name="Buyer",
            email="buyer@example.com",
            phone="09170000002",
            payment_method=ProductInquiry.PAYMENT_CARD,
            order_items=[{"name": "Tote Bag", "category": "Tote Bags", "quantity": 2, "unit_price": 100}],
            order_total=200,
            status=ProductInquiry.STATUS_COMPLETED,
            admin_notification="Test report order",
        )
        payload = self.client.get(reverse("reports_data_api"), {
            "report": "all-records",
            "range": "30d",
            "record_type": "product_sale",
        }).json()

        self.assertEqual(payload["row_count"], 1)
        self.assertEqual(payload["rows"][0][0], timezone.localdate().isoformat())
        self.assertEqual(payload["rows"][0][1], "Product sales")
        self.assertEqual(payload["distribution"]["values"], [0, 0, 0, 0, 1])
        self.assertEqual(sum(payload["trend"]["values"]), 1)

    def test_empty_assistance_keeps_both_charts_and_table_empty_message(self):
        payload = self.client.get(reverse("reports_data_api"), {
            "report": "assistance",
            "range": "30d",
        }).json()

        self.assertEqual(payload["trend"]["values"], [0, 0, 0, 0, 0])
        self.assertEqual(payload["distribution"]["values"], [])
        self.assertEqual(payload["trend"]["note"], "Records per day")
        self.assertEqual(payload["distribution"]["note"], "Quantity or amount given")
        self.assertEqual(payload["empty_message"], "No assistance records in this period.")
        self.assertEqual(payload["row_count"], 0)

    def test_all_time_period_includes_older_completed_donations(self):
        Donation.objects.create(
            donor_name="Longtime donor",
            campaign="Community",
            amount=750,
            payment_method=Donation.PAYMENT_CASH,
            reference_number="REPORT-ALL-TIME-1",
            status=Donation.STATUS_COMPLETED,
            created_at=timezone.now() - timedelta(days=180),
        )

        response = self.client.get(reverse("reports_data_api"), {
            "report": "donations",
            "range": "all",
            "donation_type": "cash",
        })

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["period"], "All time")
        self.assertEqual(payload["totals"]["cash_count"], 1)
        self.assertEqual(payload["totals"]["cash_amount"], 750)

    def test_accounts_filters_personal_data_and_ignores_period(self):
        today = timezone.localdate()
        female = User.objects.create_user(
            username="reports-test-female",
            first_name="Female",
            password="test-password",
        )
        UserProfile.objects.create(
            user=female,
            account_role=UserProfile.ROLE_REGULAR,
            gender="female",
            birthdate=today.replace(year=today.year - 22),
        )
        male = User.objects.create_user(username="reports-test-male", password="test-password")
        UserProfile.objects.create(
            user=male,
            account_role=UserProfile.ROLE_VOLUNTEER,
            gender="male",
            birthdate=today.replace(year=today.year - 22),
        )

        response = self.client.get(reverse("reports_data_api"), {
            "report": "accounts",
            "range": "custom",
            "gender": "female",
            "age_group": "18_24",
        })
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["period"], "Not affected by the reporting period")
        self.assertEqual(payload["row_count"], 1)
        self.assertEqual(payload["totals"]["female"], 1)
        self.assertEqual(payload["rows"][0][0], "Female")

    def test_custom_date_validation_and_filtered_exports(self):
        invalid = self.client.get(reverse("reports_data_api"), {
            "report": "assistance",
            "range": "custom",
            "start": "2026-10-20",
            "end": "2026-10-10",
        })
        self.assertEqual(invalid.status_code, 400)

        Donation.objects.create(
            donor_name="Selected donor",
            campaign="Spring",
            amount=250,
            payment_method=Donation.PAYMENT_CASH,
            reference_number="REPORT-EXPORT-1",
            status=Donation.STATUS_COMPLETED,
        )
        response = self.client.post(reverse("reports_export"), {
            "report": "donations",
            "range": "30d",
            "donation_type": "cash",
            "campaign": "Spring",
            "format": "csv",
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("₱250", response.content.decode("utf-8-sig"))

        pdf_response = self.client.post(reverse("reports_export"), {
            "report": "all-records",
            "range": "30d",
            "record_type": "all",
            "format": "pdf",
        })
        self.assertEqual(pdf_response.status_code, 200)
        self.assertTrue(pdf_response.content.startswith(b"%PDF"))

    def test_pdf_exports_include_branded_chart_report_for_every_tab(self):
        AdminSystemSettings.objects.create(
            key="global",
            settings={"system_name": "HappYness Community"},
        )
        for report in (
            "donations",
            "volunteer-hours",
            "activities",
            "assistance",
            "product-sales",
            "accounts",
            "all-records",
        ):
            with self.subTest(report=report):
                response = self.client.post(reverse("reports_export"), {
                    "report": report,
                    "range": "all",
                    "format": "pdf",
                })

                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.content.startswith(b"%PDF"))
                self.assertIn(b"/Subtype /Image", response.content)
                self.assertIn(b"/Title", response.content)
                self.assertIn(b"/MediaBox [ 0 0 612 792 ]", response.content)

    def test_operations_pdf_exports_are_branded_portrait_and_include_csv_controls_removed(self):
        AdminSystemSettings.objects.create(
            key="global",
            settings={"system_name": "HappYness Community"},
        )
        Donation.objects.create(
            donor_name="Operations donor",
            campaign="Community",
            amount=300,
            payment_method=Donation.PAYMENT_CASH,
            reference_number="OPS-DONATION-1",
            status=Donation.STATUS_COMPLETED,
        )
        ProductInquiry.objects.create(
            full_name="Operations buyer",
            email="operations-buyer@example.com",
            phone="09170000005",
            payment_method=ProductInquiry.PAYMENT_COD,
            order_items=[{"name": "Tote Bag", "quantity": 2, "unit_price": 150}],
            order_total=300,
            status=ProductInquiry.STATUS_COMPLETED,
            admin_notification="Operations PDF test order",
        )
        self._create_item_pledge(ItemPledge.STATUS_RECEIVED, quantity=5)
        item = InventoryItem.objects.create(
            name="Rice",
            category=InventoryItem.CATEGORY_RELIEF_GOODS,
            stock=20,
            low_stock_threshold=5,
        )
        StockMovement.objects.create(
            item=item,
            action=StockMovement.ACTION_RESTOCK,
            quantity=10,
            reason="Initial stock",
        )

        donation_page = self.client.get(reverse("donations"))
        payment_page = self.client.get(reverse("payment"))
        inventory_page = self.client.get(reverse("inventory"))
        self.assertEqual(donation_page.status_code, 200)
        self.assertNotContains(donation_page, "Export CSV")
        self.assertEqual(payment_page.status_code, 200)
        self.assertContains(payment_page, "Export PDF")
        self.assertEqual(inventory_page.status_code, 200)
        self.assertNotContains(inventory_page, "Export CSV")

        for route_name in ("export_donations_pdf", "export_payments_pdf", "inventory_export_pdf"):
            with self.subTest(route=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.content.startswith(b"%PDF"))
                self.assertIn(b"/Subtype /Image", response.content)
                self.assertIn(b"/Title", response.content)
                self.assertIn(b"/MediaBox [ 0 0 612 792 ]", response.content)
