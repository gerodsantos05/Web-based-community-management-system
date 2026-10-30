import json

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import ProductInquiry


class ProductOrderStatusTests(TestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(
            username="order-status-buyer",
            email="order-status-buyer@example.com",
            password="test-password-123",
        )
        self.admin = User.objects.create_superuser(
            username="order-status-admin",
            email="order-status-admin@example.com",
            password="test-password-123",
        )
        self.order = ProductInquiry.objects.create(
            user=self.buyer,
            full_name="Order Status Buyer",
            email="order-status-buyer@example.com",
            phone="09123456789",
            payment_method=ProductInquiry.PAYMENT_COD,
            order_items=[{"name": "Tote Bag", "quantity": 1, "unit_price": 500}],
            order_total=500,
            admin_notification="Test order",
        )

    def test_completed_order_has_a_refund_action_in_the_customer_tracker(self):
        self.order.status = ProductInquiry.STATUS_COMPLETED
        self.order.payment_status = ProductInquiry.PAYMENT_STATUS_PAID
        self.order.save(update_fields=["status", "payment_status", "updated_at"])
        self.client.force_login(self.buyer)

        response = self.client.get(reverse("products"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Request refund")
        self.assertContains(response, f'data-receipt-order-id="{self.order.id}"')
        self.assertContains(response, 'class="order-tracker-refund-inline"')
        self.assertContains(response, "Reason for refund")
        self.assertNotContains(response, 'id="orderRefundModal"')

    def test_refunded_order_does_not_repeat_the_payment_status_badge(self):
        self.order.status = ProductInquiry.STATUS_REFUNDED
        self.order.payment_status = ProductInquiry.PAYMENT_STATUS_REFUNDED
        self.order.save(update_fields=["status", "payment_status", "updated_at"])
        self.client.force_login(self.buyer)

        response = self.client.get(reverse("products"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Refunded")
        self.assertNotContains(response, 'class="order-tracker-payment-status"')
        self.assertContains(response, f'data-receipt-order-id="{self.order.id}"')

    def test_receipt_is_only_available_for_cancelled_orders_with_captured_payment(self):
        self.order.status = ProductInquiry.STATUS_CANCELLED
        self.order.payment_status = ProductInquiry.PAYMENT_STATUS_PENDING
        self.order.save(update_fields=["status", "payment_status", "updated_at"])
        self.client.force_login(self.buyer)

        unpaid_response = self.client.get(reverse("products"))
        self.assertNotContains(unpaid_response, f'data-receipt-order-id="{self.order.id}"')

        self.order.status = ProductInquiry.STATUS_VERIFIED
        self.order.payment_status = ProductInquiry.PAYMENT_STATUS_PAID
        self.order.save(update_fields=["status", "payment_status", "updated_at"])
        paid_response = self.client.get(reverse("products"))
        self.assertContains(paid_response, f'data-receipt-order-id="{self.order.id}"')
        self.assertNotContains(paid_response, 'class="order-tracker-card-actions-stack"')
        paid_html = paid_response.content.decode()
        receipt_row = paid_html.index(f'data-receipt-order-id="{self.order.id}"')
        cancel_button = paid_html.index(f'data-cancel-order-id="{self.order.id}"')
        self.assertLess(receipt_row, cancel_button)

    def test_failed_payment_on_pending_order_explains_issue_and_keeps_cancel_action(self):
        self.order.status = ProductInquiry.STATUS_PENDING
        self.order.payment_status = ProductInquiry.PAYMENT_STATUS_FAILED
        self.order.save(update_fields=["status", "payment_status", "updated_at"])
        self.client.force_login(self.buyer)

        response = self.client.get(reverse("products"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Payment failed. This order is still pending")
        self.assertContains(response, f'data-cancel-order-id="{self.order.id}"')

    def test_admin_updates_order_and_payment_status_independently(self):
        self.client.force_login(self.admin)

        confirmed = self.client.post(reverse("payment_verify", args=[self.order.id]))
        self.assertEqual(confirmed.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, ProductInquiry.STATUS_VERIFIED)
        self.assertEqual(self.order.payment_status, ProductInquiry.PAYMENT_STATUS_PENDING)

        delivered = self.client.post(
            reverse("payment_mark_in_delivery", args=[self.order.id]),
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(delivered.status_code, 200)
        completed = self.client.post(reverse("payment_mark_completed", args=[self.order.id]))
        self.assertEqual(completed.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, ProductInquiry.STATUS_COMPLETED)
        self.assertEqual(self.order.payment_status, ProductInquiry.PAYMENT_STATUS_PENDING)

        paid = self.client.post(reverse("payment_mark_paid", args=[self.order.id]))
        self.assertEqual(paid.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, ProductInquiry.STATUS_COMPLETED)
        self.assertEqual(self.order.payment_status, ProductInquiry.PAYMENT_STATUS_PAID)

        dashboard = self.client.get(reverse("payment"))
        payment_row = dashboard.context["payments_json"][0]
        self.assertEqual(payment_row["orderStatus"], "Completed")
        self.assertEqual(payment_row["paymentStatus"], "Paid")
        self.assertEqual(payment_row["subtotal"], 500)
        self.assertTrue(payment_row["orderItems"])
        self.assertContains(dashboard, 'id="receiptOrderStatus"')
        self.assertContains(dashboard, 'class="receipt-brand-logo"')
        self.assertContains(dashboard, "order-receipt.js")

        self.client.force_login(self.buyer)
        tracked_order = self.client.get(reverse("product_order_tracker")).json()["orders"][0]
        self.assertEqual(tracked_order["status_label"], "Completed")
        self.assertEqual(tracked_order["payment_status"], "Paid")

    def test_refund_request_is_visible_and_admin_can_decline_it(self):
        self.order.status = ProductInquiry.STATUS_COMPLETED
        self.order.payment_status = ProductInquiry.PAYMENT_STATUS_PAID
        self.order.save(update_fields=["status", "payment_status", "updated_at"])
        self.client.force_login(self.buyer)

        requested = self.client.post(
            reverse("request_product_order_return", args=[self.order.id]),
            {"request_type": "refund", "reason": "Damaged item"},
        )
        self.assertEqual(requested.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, ProductInquiry.STATUS_REFUND_REQUESTED)
        self.assertEqual(self.order.payment_status, ProductInquiry.PAYMENT_STATUS_PAID)

        self.client.force_login(self.admin)
        declined = self.client.post(reverse("payment_reject_refund_request", args=[self.order.id]))
        self.assertEqual(declined.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, ProductInquiry.STATUS_COMPLETED)
        self.assertEqual(self.order.payment_status, ProductInquiry.PAYMENT_STATUS_PAID)

    def test_refund_request_requires_a_reason_and_exposes_it_to_admin(self):
        self.order.status = ProductInquiry.STATUS_COMPLETED
        self.order.payment_status = ProductInquiry.PAYMENT_STATUS_PAID
        self.order.save(update_fields=["status", "payment_status", "updated_at"])
        self.client.force_login(self.buyer)

        missing_reason = self.client.post(
            reverse("request_product_order_return", args=[self.order.id]),
            {"request_type": "refund", "reason": "   "},
        )
        self.assertEqual(missing_reason.status_code, 400)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, ProductInquiry.STATUS_COMPLETED)
        self.assertEqual(self.order.return_reason, "")

        invalid_type = self.client.post(
            reverse("request_product_order_return", args=[self.order.id]),
            {"request_type": "exchange", "reason": "The item arrived damaged."},
        )
        self.assertEqual(invalid_type.status_code, 400)

        overlong_reason = self.client.post(
            reverse("request_product_order_return", args=[self.order.id]),
            {"request_type": "refund", "reason": "x" * 2001},
        )
        self.assertEqual(overlong_reason.status_code, 400)

        submitted = self.client.post(
            reverse("request_product_order_return", args=[self.order.id]),
            {"request_type": "refund", "reason": "The item arrived damaged."},
        )
        self.assertEqual(submitted.status_code, 200)
        self.client.force_login(self.admin)
        dashboard = self.client.get(reverse("payment"))
        self.assertEqual(dashboard.context["payments_json"][0]["returnReason"], "The item arrived damaged.")

    def test_approved_refund_updates_payment_and_order_status(self):
        self.order.status = ProductInquiry.STATUS_REFUND_REQUESTED
        self.order.payment_status = ProductInquiry.PAYMENT_STATUS_PAID
        self.order.save(update_fields=["status", "payment_status", "updated_at"])
        self.client.force_login(self.admin)

        response = self.client.post(reverse("payment_refund", args=[self.order.id]))

        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, ProductInquiry.STATUS_REFUNDED)
        self.assertEqual(self.order.payment_status, ProductInquiry.PAYMENT_STATUS_REFUNDED)
        payment_row = self.client.get(reverse("payment")).context["payments_json"][0]
        self.assertTrue(payment_row["refundProcessedAt"])
