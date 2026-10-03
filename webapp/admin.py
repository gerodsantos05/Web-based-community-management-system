from django.contrib import admin

from .models import Donation, InventoryItem, ProductInquiry, RoleApplication, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
	list_display = ("user", "account_role", "updated_at")
	list_filter = ("account_role",)
	search_fields = ("user__username", "user__first_name", "user__last_name", "user__email")


@admin.register(RoleApplication)
class RoleApplicationAdmin(admin.ModelAdmin):
	list_display = ("user", "role", "status", "created_at", "updated_at")
	list_filter = ("role", "status", "created_at")
	search_fields = ("user__username", "full_name", "contact_details")


@admin.register(ProductInquiry)
class ProductInquiryAdmin(admin.ModelAdmin):
	list_display = ("full_name", "payment_method", "order_total", "created_at")
	list_filter = ("payment_method", "created_at")
	search_fields = ("full_name", "email", "phone", "admin_notification")
	readonly_fields = ("created_at", "updated_at", "admin_notification", "order_items", "order_total")


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
	list_display = ("reference_number", "donor_name", "amount", "payment_method", "status", "created_at")
	list_filter = ("status", "payment_method", "created_at")
	search_fields = ("reference_number", "donor_name", "donor_message", "campaign")
	readonly_fields = ("created_at", "updated_at", "reference_number")


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
	list_display = ("name", "category", "stock", "price", "status", "updated_at")
	list_filter = ("category", "created_at", "updated_at")
	search_fields = ("name", "sub_category", "description")
	readonly_fields = ("created_at", "updated_at", "status")
