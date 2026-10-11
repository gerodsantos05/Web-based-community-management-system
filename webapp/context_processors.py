from datetime import timedelta

from django.utils import timezone

from .avatar_utils import avatar_url_for_user, default_avatar_url
from .models import AdminSystemSettings, CommunityNotification, ProductInquiry, UserProfile

try:
    from allauth.socialaccount.models import SocialAccount
except Exception:
    SocialAccount = None


def _notification_time_ago(value):
    if not value:
        return "Just now"

    now = timezone.now()
    delta = max(now - value, timedelta(0))
    seconds = int(delta.total_seconds())

    if seconds < 60:
        return "Just now"

    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"

    hours = minutes // 60
    if hours < 24:
        return f"{hours} hour{'s' if hours != 1 else ''} ago"

    days = hours // 24
    if days < 7:
        return f"{days} day{'s' if days != 1 else ''} ago"

    return timezone.localtime(value).strftime("%b %d, %Y")


def dashboard_profile_context(request):
    fallback_avatar_url = default_avatar_url()
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {
            "default_avatar_url": fallback_avatar_url,
            "user_avatar_url": fallback_avatar_url,
        }

    profile = None
    try:
        profile = user.userprofile
    except UserProfile.DoesNotExist:
        profile = None

    full_name = (f"{user.first_name} {user.last_name}").strip()
    display_name = full_name or user.first_name or user.username
    initials = "".join([part[:1].upper() for part in display_name.split() if part])[:2] or "U"
    avatar_url = avatar_url_for_user(user)
    admin_system_name = "HappYness Project"
    if user.is_superuser:
        admin_settings = AdminSystemSettings.objects.filter(pk="global").only("settings").first()
        saved_settings = admin_settings.settings if admin_settings and isinstance(admin_settings.settings, dict) else {}
        admin_system_name = str(saved_settings.get("system_name") or admin_system_name).strip() or admin_system_name

    # Prefer provider-supplied email (e.g. Google) when available
    provider_email = None
    if SocialAccount is not None:
        try:
            sa = SocialAccount.objects.filter(user=user).first()
            if sa and getattr(sa, 'extra_data', None):
                provider_email = sa.extra_data.get('email') or None
        except Exception:
            provider_email = None

    display_email = provider_email or (user.email or user.username)

    notifications_qs = (
        CommunityNotification.objects
        .filter(recipient=user)
        .select_related("actor")
        .order_by("-created_at", "-id")[:10]
    )
    notifications = [
        {
            "id": item.id,
            "title": item.message,
            "time_ago": _notification_time_ago(item.created_at),
            "is_read": bool(item.is_read),
            "url": item.target_url or "/user-dashboard/community/",
            "type": item.notification_type,
        }
        for item in notifications_qs
    ]
    unread_count = CommunityNotification.objects.filter(recipient=user, is_read=False).count()

    product_image_map = {
        "Handwoven Doormat": "/static/media/hand woven doormat.jpg",
        "Braided Doormat": "/static/media/braided doormat.jpg",
        "Pot Holder Rag": "/static/media/pot holder rag.png",
        "Tote Bag": "/static/media/tote bag.jpg",
        "Champion of Kindness Bag": "/static/media/champion of kindness bag.png",
        "Handknit Sweater": "/static/media/handkit sweater.png",
        "HappYness T-shirt": "/static/media/Happyness T-shirt.png",
        "Homemade Candle": "/static/media/Homemade Candle.jpg",
        "Handcrafted Perfume": "/static/media/Handcrafted Perfume.jpg",
    }
    status_labels = {
        ProductInquiry.STATUS_PENDING: "Pending",
        ProductInquiry.STATUS_VERIFIED: "Confirmed",
        ProductInquiry.STATUS_IN_DELIVERY: "In Delivery",
        ProductInquiry.STATUS_COMPLETED: "Completed",
        ProductInquiry.STATUS_RETURN_REQUESTED: "Return Requested",
        ProductInquiry.STATUS_REFUND_REQUESTED: "Refund Requested",
        ProductInquiry.STATUS_RETURNED: "Returned",
        ProductInquiry.STATUS_CANCELLED: "Cancelled",
        ProductInquiry.STATUS_FAILED: "Cancelled",
        ProductInquiry.STATUS_REFUNDED: "Refunded",
    }

    def delivery_status_tooltip(order):
        if order.status != ProductInquiry.STATUS_IN_DELIVERY:
            return ""

        details = []
        if order.delivery_window_start and order.delivery_window_end:
            start = timezone.localtime(order.delivery_window_start).strftime('%b %d, %Y')
            end = timezone.localtime(order.delivery_window_end).strftime('%b %d, %Y')
            details.append(f"Delivery window: {start}–{end}")
        elif order.delivery_window_start:
            start = timezone.localtime(order.delivery_window_start).strftime('%b %d, %Y')
            details.append(f"Delivery window: {start}")
        elif order.delivery_window_end:
            end = timezone.localtime(order.delivery_window_end).strftime('%b %d, %Y')
            details.append(f"Delivery window: {end}")
        return " | ".join(details) if details else ""

    def delivery_status_label(order):
        return status_labels.get(order.status, "Pending")

    orders = []
    for order in ProductInquiry.objects.filter(user=user).prefetch_related("product_reviews").order_by("-created_at", "-id"):
        item = (order.order_items or [{}])[0]
        product_name = str(item.get("name", "Product")).strip()
        variation = str(item.get("variation", "")).strip()
        review = next((record for record in order.product_reviews.all() if record.product_name == product_name and record.variation == variation), None)
        status_label = delivery_status_label(order)
        delivery_window_start = order.delivery_window_start.isoformat() if order.delivery_window_start else ""
        delivery_window_end = order.delivery_window_end.isoformat() if order.delivery_window_end else ""
        delivery_window_text = ""
        if order.status == ProductInquiry.STATUS_IN_DELIVERY:
            if order.delivery_window_start and order.delivery_window_end:
                start = timezone.localtime(order.delivery_window_start).strftime('%b %d, %Y')
                end = timezone.localtime(order.delivery_window_end).strftime('%b %d, %Y')
                delivery_window_text = f"Expected delivery: {start} – {end}"
            elif order.delivery_window_start:
                start = timezone.localtime(order.delivery_window_start).strftime('%b %d, %Y')
                delivery_window_text = f"Expected delivery: {start}"
            elif order.delivery_window_end:
                end = timezone.localtime(order.delivery_window_end).strftime('%b %d, %Y')
                delivery_window_text = f"Expected delivery: {end}"
        orders.append({
            "id": str(order.id),
            "name": product_name,
            "image": product_image_map.get(product_name, "/static/media/hand woven doormat.jpg"),
            "variation": variation,
            "reviewed": review is not None,
            "review_rating": review.rating if review else None,
            "review_message": review.message if review else "",
            "quantity": item.get("quantity", 1),
            "total": order.order_total,
            "date": order.created_at,
            "status": order.status,
            "status_label": status_label,
            "status_tooltip": delivery_status_tooltip(order),
            "delivery_window_start": delivery_window_start,
            "delivery_window_end": delivery_window_end,
            "delivery_window_text": delivery_window_text,
        })

    return {
        "current_user_profile": profile,
        "user_display_name": display_name,
        "user_initials": initials,
        "user_avatar_url": avatar_url,
        "default_avatar_url": fallback_avatar_url,
        "admin_system_name": admin_system_name,
        "user_provider_email": display_email,
        "community_notifications": notifications,
        "community_notification_unread_count": unread_count,
        "dashboard_notifications_feed_url": "/dashboard/notifications/feed/",
        "dashboard_notification_mark_read_url": "/dashboard/notifications/mark-read/",
        "dashboard_notification_mark_all_read_url": "/dashboard/notifications/mark-all-read/",
        "product_tracker_orders": orders,
        "product_tracker_active_count": sum(
            1 for order in orders
            if order["status"] not in {
                ProductInquiry.STATUS_COMPLETED,
                ProductInquiry.STATUS_CANCELLED,
                ProductInquiry.STATUS_REFUNDED,
                ProductInquiry.STATUS_RETURNED,
            }
        ),
    }
