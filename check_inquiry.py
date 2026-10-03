#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'HappynessProject.settings')
django.setup()

from webapp.models import ProductInquiry

inquiries = ProductInquiry.objects.all().order_by('-created_at')[:3]
for inquiry in inquiries:
    print(f"\n{'='*50}")
    print(f"ID: {inquiry.id}")
    print(f"Full Name: {inquiry.full_name}")
    print(f"Email: {inquiry.email}")
    print(f"Phone: {inquiry.phone}")
    print(f"Country Code: {inquiry.country_code}")
    print(f"Payment Method: {inquiry.payment_method}")
    print(f"Payment Screenshot: {inquiry.payment_screenshot.name if inquiry.payment_screenshot else 'No screenshot'}")
    print(f"Screenshot Size: {inquiry.payment_screenshot.size if inquiry.payment_screenshot else 'N/A'} bytes")
    print(f"Order Items: {inquiry.order_items}")
    print(f"Order Total: ₱{inquiry.order_total}")
    print(f"Created: {inquiry.created_at}")
