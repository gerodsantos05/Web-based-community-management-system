from datetime import timedelta

from django.utils import timezone

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
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}

    profile = None
    try:
        profile = user.userprofile
    except UserProfile.DoesNotExist:
        profile = None

    full_name = (f"{user.first_name} {user.last_name}").strip()
    display_name = full_name or user.first_name or user.username
    initials = "".join([part[:1].upper() for part in display_name.split() if part])[:2] or "U"
    avatar_url = profile.avatar.url if profile and profile.avatar else ""
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
        ProductInquiry.STATUS_COMPLETED: "Completed",
        ProductInquiry.STATUS_CANCELLED: "Cancelled",
        ProductInquiry.STATUS_FAILED: "Cancelled",
        ProductInquiry.STATUS_REFUNDED: "Cancelled",
    }
    orders = []
    for order in ProductInquiry.objects.filter(user=user).order_by("-created_at", "-id"):
        item = (order.order_items or [{}])[0]
        product_name = str(item.get("name", "Product")).strip()
        orders.append({
            "id": str(order.id),
            "name": product_name,
            "image": product_image_map.get(product_name, "/static/media/hand woven doormat.jpg"),
            "variation": str(item.get("variation", "")).strip(),
            "quantity": item.get("quantity", 1),
            "total": order.order_total,
            "date": order.created_at,
            "status": order.status,
            "status_label": status_labels.get(order.status, "Pending"),
        })

    return {
        "current_user_profile": profile,
        "user_display_name": display_name,
        "user_initials": initials,
        "user_avatar_url": avatar_url,
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
            if order["status"] not in {ProductInquiry.STATUS_COMPLETED, ProductInquiry.STATUS_CANCELLED}
        ),
    }
