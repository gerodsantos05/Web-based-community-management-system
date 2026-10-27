import io
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import InventoryItem, ProductInquiry, UserProfile


class InventoryProductPublishingTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="inventory-product-admin",
            email="inventory-product-admin@example.com",
            password="Test-password-123!",
        )
        self.client.force_login(self.admin)

    def product_image(self, name="slippers.png"):
        image_bytes = io.BytesIO()
        Image.new("RGB", (2, 2), color="teal").save(image_bytes, format="PNG")
        return SimpleUploadedFile(name, image_bytes.getvalue(), content_type="image/png")

    def test_inventory_upload_publishes_only_store_products_with_uploaded_image(self):
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            relief_item = InventoryItem.objects.create(
                name="Relief Slippers",
                category=InventoryItem.CATEGORY_RELIEF_GOODS,
                stock=4,
            )
            response = self.client.post(
                reverse("inventory_add"),
                {
                    "name": "Woven Slippers",
                    "category": InventoryItem.CATEGORY_STORE_PRODUCT,
                    "sub_category": "Slippers",
                    "stock": "6",
                    "unit": "pairs",
                    "low_stock_threshold": "2",
                    "price": "125.50",
                    "description": "Handmade woven slippers.",
                    "image": self.product_image(),
                },
            )

            self.assertEqual(response.status_code, 201)
            item = InventoryItem.objects.get(name="Woven Slippers")
            self.assertEqual(str(item.price), "125.50")
            self.assertTrue(item.image)
            self.assertTrue(item.image.storage.exists(item.image.name))

            product_page = self.client.get(reverse("products"))
            self.assertContains(product_page, "Woven Slippers")
            self.assertContains(product_page, "Slippers")
            self.assertContains(product_page, item.image.url)
            self.assertNotContains(product_page, relief_item.name)

    def test_changing_inventory_category_to_store_product_publishes_item(self):
        item = InventoryItem.objects.create(
            name="Canvas Slippers",
            category=InventoryItem.CATEGORY_OTHER,
            stock=3,
        )

        unpublished_page = self.client.get(reverse("products"))
        self.assertNotContains(unpublished_page, item.name)

        response = self.client.post(
            reverse("inventory_edit", kwargs={"item_id": item.pk}),
            {
                "name": item.name,
                "category": InventoryItem.CATEGORY_STORE_PRODUCT,
                "sub_category": "Slippers",
                "stock": "3",
                "unit": "pairs",
                "low_stock_threshold": "1",
                "price": "90",
                "description": "",
                "image": self.product_image("canvas-slippers.png"),
            },
        )

        self.assertEqual(response.status_code, 200)
        item.refresh_from_db()
        self.assertEqual(item.category, InventoryItem.CATEGORY_STORE_PRODUCT)
        self.assertTrue(item.image)
        self.assertContains(self.client.get(reverse("products")), item.name)

        self.client.post(
            reverse("inventory_edit", kwargs={"item_id": item.pk}),
            {
                "name": item.name,
                "category": InventoryItem.CATEGORY_OTHER,
                "sub_category": "",
                "stock": "3",
                "unit": "pairs",
                "low_stock_threshold": "1",
                "price": "",
                "description": "",
            },
        )
        self.assertNotContains(self.client.get(reverse("products")), item.name)

    def test_order_uses_the_inventory_price_for_a_store_product(self):
        customer = User.objects.create_user(
            username="inventory-product-customer",
            email="inventory-product-customer@example.com",
            password="Test-password-123!",
        )
        UserProfile.objects.create(user=customer, account_role=UserProfile.ROLE_REGULAR)
        item = InventoryItem.objects.create(
            name="Priced Slippers",
            category=InventoryItem.CATEGORY_STORE_PRODUCT,
            sub_category="Slippers",
            stock=3,
            price=75,
        )
        self.client.force_login(customer)

        response = self.client.post(
            reverse("submit_product_inquiry"),
            {
                "full_name": "Inventory Customer",
                "email": customer.email,
                "phone": "09171234567",
                "payment_method": ProductInquiry.PAYMENT_COD,
                "order_items": '[{"name":"Priced Slippers","category":"Slippers","quantity":1}]',
            },
        )

        self.assertEqual(response.status_code, 201)
        inquiry = ProductInquiry.objects.get()
        self.assertEqual(inquiry.order_items[0]["unit_price"], 75)
        item.refresh_from_db()
        self.assertEqual(item.stock, 2)
