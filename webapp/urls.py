from django.urls import path
from . import views

urlpatterns = [
	path("", views.index, name="home"),
	path("about/", views.about, name="about"),
	path("products/", views.products, name="products"),
	path("contact/", views.contact, name="contact"),
	path("signin/", views.signin, name="signin"),
	path("signup/", views.signup, name="signup"),
	path("dashboard/", views.dashboard, name="dashboard"),
	path("users/", views.users, name="users"),
	path("donations/", views.donations, name="donations"),
	path("payment/", views.payment, name="payment"),
	path("inventory/", views.inventory, name="inventory"),
	path("reports/", views.reports, name="reports"),
	path("settings/", views.settings, name="settings"),
	path("logout/", views.logout_view, name="logout"),
]