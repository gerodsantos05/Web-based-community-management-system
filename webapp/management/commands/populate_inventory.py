from django.core.management.base import BaseCommand
from webapp.models import InventoryItem


class Command(BaseCommand):
	help = 'Populate initial store products in inventory'

	def handle(self, *args, **options):
		products = [
			{
				'name': 'Handwoven Doormat',
				'category': InventoryItem.CATEGORY_STORE_PRODUCT,
				'unit': 'pcs',
				'price': 100,
				'stock': 0,
				'low_stock_threshold': 10,
			},
			{
				'name': 'Braided Doormat',
				'category': InventoryItem.CATEGORY_STORE_PRODUCT,
				'unit': 'pcs',
				'price': 100,
				'stock': 0,
				'low_stock_threshold': 10,
			},
			{
				'name': 'Pot Holder Rag',
				'category': InventoryItem.CATEGORY_STORE_PRODUCT,
				'unit': 'pcs',
				'price': 50,
				'stock': 0,
				'low_stock_threshold': 10,
			},
			{
				'name': 'Tote Bag',
				'category': InventoryItem.CATEGORY_STORE_PRODUCT,
				'unit': 'pcs',
				'price': 100,
				'stock': 0,
				'low_stock_threshold': 10,
			},
			{
				'name': 'Champion of Kindness Bag',
				'category': InventoryItem.CATEGORY_STORE_PRODUCT,
				'unit': 'pcs',
				'price': 100,
				'stock': 0,
				'low_stock_threshold': 10,
			},
			{
				'name': 'Handknit Sweater',
				'category': InventoryItem.CATEGORY_STORE_PRODUCT,
				'unit': 'pcs',
				'price': 150,
				'stock': 0,
				'low_stock_threshold': 10,
			},
			{
				'name': 'HappYness T-shirt',
				'category': InventoryItem.CATEGORY_STORE_PRODUCT,
				'unit': 'pcs',
				'price': 150,
				'stock': 0,
				'low_stock_threshold': 10,
			},
			{
				'name': 'Homemade Candle',
				'category': InventoryItem.CATEGORY_STORE_PRODUCT,
				'unit': 'pcs',
				'price': 50,
				'stock': 0,
				'low_stock_threshold': 10,
			},
			{
				'name': 'Handcrafted Perfume',
				'category': InventoryItem.CATEGORY_STORE_PRODUCT,
				'unit': 'pcs',
				'price': 120,
				'stock': 0,
				'low_stock_threshold': 10,
			},
		]

		created_count = 0
		for product_data in products:
			item, created = InventoryItem.objects.get_or_create(
				name=product_data['name'],
				defaults=product_data
			)
			if created:
				created_count += 1
				self.stdout.write(self.style.SUCCESS(f"Created: {item.name}"))
			else:
				self.stdout.write(f"Already exists: {item.name}")

		self.stdout.write(self.style.SUCCESS(f"\nTotal created: {created_count}"))
