import os

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.conf import settings as django_settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.files.base import ContentFile
from django.core.mail import EmailMultiAlternatives
from django.core.validators import validate_email
from django.http import FileResponse, Http404, JsonResponse
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.text import slugify
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.utils import timezone
import secrets
from django.db import connection, transaction
from django.db.models import Count, Sum, Avg, F, OuterRef, Subquery, Q
import uuid
import calendar
import json
import csv
import io
from pathlib import Path
from datetime import datetime, timedelta, date, time
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from .forms import (
    BeneficiaryApplicationForm,
    ResourceLibraryMaterialForm,
    SignInForm,
    SignUpForm,
    SkillLearningMaterialForm,
    SkillLearningTopicForm,
    VolunteerApplicationForm,
)
from .models import (
    AdminSystemSettings,
    AdminUserPreferences,
    ALLOWED_UPLOAD_EXTENSIONS,
    MAX_UPLOAD_FILE_SIZE_BYTES,
    MaterialSubmission,
    MaterialSubmissionFile,
    CommunityPost,
    CommunityPostAttachment,
    CommunityPostLike,
    CommunityPostComment,
    CommunityPostCommentLike,
    CommunityNotification,
    BeneficiaryAssistanceRecord,
    BeneficiaryAssistanceFeedback,
    BeneficiaryActivityFeedback,
    BeneficiaryActivityAttendance,
    Activity,
    Donation,
    InventoryItem,
    ProductInquiry,
    RoleApplication,
    ResourceLibraryMaterial,
    StockMovement,
    SkillLearningMaterial,
    SkillLearningMaterialEngagement,
    SkillLearningTopic,
    SkillLearningTopicEngagement,
    UserProfile,
    VolunteerActivityAssignment,
    VolunteerOjtSchedule,
    ActivityBeneficiaryAssignment,
    VolunteerAdminMessage,
    VolunteerAdminMessageAttachment,
    VolunteerAttendanceRecord,
    VolunteerCertificate,
    CommunityPostReport,
)
from .two_factor import (
    clear_two_factor_state,
    get_pending_two_factor_challenge,
    is_two_factor_challenge_expired,
    is_two_factor_code_valid,
    is_two_factor_confirmed,
    is_two_factor_enabled,
    mark_two_factor_session_verified,
    start_two_factor_challenge,
    touch_two_factor_challenge_attempt,
)


PROFILE_AVATAR_MAX_SIZE = 5 * 1024 * 1024
COMMUNITY_POST_PAGE_SIZE = 8
COMMUNITY_COMMENT_PAGE_SIZE = 8
ADMIN_SYSTEM_SETTINGS_DEFAULTS = {
    "system_name": "HappYness Admin Suite",
    "system_code": "HAP-SYS-01",
    "deployment_env": "Production",
    "support_email": "admin@happyness.org",
    "timezone": "Asia/Manila (UTC+8)",
    "language": "English",
    "date_format": "MM/DD/YYYY",
    "number_format": "1,234.56",
    "default_role": "Viewer",
    "invite_policy": "Admin approval required",
    "max_admins": 12,
    "session_limit": "2",
    "permission_change_approval": "Dual approval required",
    "custom_roles_policy": "Enabled for super admins",
    "require_role_change_reason": True,
    "allow_manager_password_reset": True,
    "notify_email": True,
    "notify_inapp": True,
    "digest_frequency": "Hourly digest",
    "escalation_window": "30 minutes",
    "quiet_hours_start": "22:00",
    "quiet_hours_end": "06:00",
    "password_length": 12,
    "password_complexity": "Upper, lower, number, symbol",
    "mfa_policy": "Required for admins",
    "session_timeout": "30 minutes",
    "ip_allowlist": "192.168.20.0/24\n203.177.14.19",
    "failed_login_limit": "5 attempts",
    "account_lockout": "30 minutes",
    "enable_audit_logs": True,
    "geo_restrictions": False,
    "maintenance_window": "Sunday 01:00 - 03:00",
    "backup_frequency": "Daily",
    "retention_period": "30 days",
    "update_channel": "Stable",
    "maintenance_mode": False,
    "auto_patch": True,
}
ADMIN_SYSTEM_SETTINGS_CHOICES = {
    "deployment_env": {"Production", "Staging", "Development"},
    "timezone": {"Asia/Manila (UTC+8)", "Asia/Singapore (UTC+8)", "America/New_York (UTC-5)"},
    "language": {"English", "Filipino"},
    "date_format": {"MM/DD/YYYY", "DD/MM/YYYY", "YYYY-MM-DD"},
    "number_format": {"1,234.56", "1 234,56"},
    "default_role": {"Viewer", "Moderator", "Administrator"},
    "invite_policy": {"Admin approval required", "Open invite by managers", "Invite disabled"},
    "session_limit": {"1", "2", "3"},
    "permission_change_approval": {"Dual approval required", "Single admin approval", "No approval"},
    "custom_roles_policy": {"Enabled for super admins", "Enabled for admins", "Disabled"},
    "digest_frequency": {"Instant", "Hourly digest", "Daily digest"},
    "escalation_window": {"15 minutes", "30 minutes", "60 minutes"},
    "password_complexity": {"Upper, lower, number, symbol", "Upper, lower, number", "Passphrase only"},
    "mfa_policy": {"Required for admins", "Required for all users", "Optional"},
    "session_timeout": {"15 minutes", "30 minutes", "60 minutes"},
    "failed_login_limit": {"3 attempts", "5 attempts", "8 attempts"},
    "account_lockout": {"10 minutes", "30 minutes", "60 minutes"},
    "maintenance_window": {"Sunday 01:00 - 03:00", "Sunday 03:00 - 05:00", "Saturday 23:00 - 01:00"},
    "backup_frequency": {"Every 6 hours", "Daily", "Weekly"},
    "retention_period": {"14 days", "30 days", "90 days"},
    "update_channel": {"Stable", "Release candidate"},
}
ADMIN_SYSTEM_SETTINGS_BOOLEAN_KEYS = {
    "require_role_change_reason",
    "allow_manager_password_reset", "notify_email", "notify_inapp",
    "enable_audit_logs", "geo_restrictions", "maintenance_mode", "auto_patch",
}
ADMIN_SYSTEM_SETTINGS_INTEGER_LIMITS = {"max_admins": (1, 10000), "password_length": (8, 128)}
ADMIN_USER_PREFERENCE_DEFAULTS = {
    "pref_dark_mode": False,
    "pref_animations": True,
    "font_size": "Medium",
    "font_type": "System Default",
}
ADMIN_USER_PREFERENCE_BOOLEAN_KEYS = {"pref_dark_mode", "pref_animations"}
ADMIN_USER_PREFERENCE_CHOICES = {
    "font_size": {"Small", "Medium", "Large"},
    "font_type": {"System Default", "Serif", "Sans-serif", "Monospace"},
}
PRODUCT_CATEGORY_PRICES = {
    "Doormats": 100,
    "Pot Holder Rags": 50,
    "Tote Bags": 100,
    "Sweaters": 150,
    "T-shirt": 150,
    "Homemade Candles": 50,
    "Perfume": 120,
}

SKILL_LEARNING_DEFAULT_TOPICS = [
    {
        "title": "Planting and Gardening",
        "description": "Build healthy planting beds and learn low-cost planting routines.",
        "badge_label": "Outdoors",
        "filter_tags": ["Community", "Popular"],
        "cover_image_url": "https://images.unsplash.com/photo-1466692476868-aef1dfb1e735?auto=format&fit=crop&w=900&q=80",
        "is_recommended": True,
        "popularity_score": 92,
        "materials": [
            {
                "title": "Soil and Bed Prep",
                "description": "Understand soil texture, composting, and bed shaping.",
                "material_type": SkillLearningMaterial.TYPE_DOCUMENT,
                "external_url": "https://drive.google.com/file/d/1ZUATmwz5XSHJabA0qnFPbn6tIIeB6WUm/preview?usp=embed",
            },
            {
                "title": "Water Smart Routines",
                "description": "Set up a simple watering plan that saves time and water.",
                "material_type": SkillLearningMaterial.TYPE_VIDEO,
                "external_url": "https://drive.google.com/file/d/1lhoyxiTt25SScLMfJUZOmGZFkpdalsWr/preview?usp=embed",
            },
            {
                "title": "Planting Calendar Guide",
                "description": "Filipino seasonal planting guide for year-round harvests.",
                "material_type": SkillLearningMaterial.TYPE_REFERENCE_GUIDE,
                "external_url": "https://drive.google.com/file/d/1lhoyxiTt25SScLMfJUZOmGZFkpdalsWr/preview?usp=embed",
            },
        ],
    },
    {
        "title": "Rag Making and Upcycling",
        "description": "Turn everyday textiles into durable products with practical steps.",
        "badge_label": "Craft",
        "filter_tags": ["Community", "New"],
        "cover_image_url": "https://images.unsplash.com/photo-1473186578172-c141e6798cf4?auto=format&fit=crop&w=900&q=80",
        "is_recommended": True,
        "popularity_score": 70,
        "materials": [
            {
                "title": "Material Selection",
                "description": "Choose durable cloth and sort reusable fabric by type.",
                "material_type": SkillLearningMaterial.TYPE_DOCUMENT,
                "external_url": "https://drive.google.com/file/d/1lEF6EhQ7N6QrTPnWUoJamFPAKZtp7CsX/view?usp=drive_link",
            },
            {
                "title": "Cutting and Layering",
                "description": "Practice the first shaping steps for a finished product.",
                "material_type": SkillLearningMaterial.TYPE_VIDEO,
                "external_url": "https://drive.google.com/file/d/1lEF6EhQ7N6QrTPnWUoJamFPAKZtp7CsX/view?usp=drive_link",
            },
            {
                "title": "Weaving Patterns Guide",
                "description": "Traditional Philippine weaving patterns for ragmaking.",
                "material_type": SkillLearningMaterial.TYPE_REFERENCE_GUIDE,
                "external_url": "https://drive.google.com/file/d/1lEF6EhQ7N6QrTPnWUoJamFPAKZtp7CsX/view?usp=drive_link",
            },
        ],
    },
    {
        "title": "Livelihood Starter Skills",
        "description": "Build practical skills for small livelihood and support projects.",
        "badge_label": "Planning",
        "filter_tags": ["Community", "Popular"],
        "cover_image_url": "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?auto=format&fit=crop&w=900&q=80",
        "is_recommended": False,
        "popularity_score": 88,
        "materials": [
            {
                "title": "Starter Planning",
                "description": "Map out a simple workflow for project readiness.",
                "material_type": SkillLearningMaterial.TYPE_DOCUMENT,
                "external_url": "https://example.com/starter-planning.pdf",
            },
            {
                "title": "Budget Basics",
                "description": "Estimate low-risk costs for first runs.",
                "material_type": SkillLearningMaterial.TYPE_REFERENCE_GUIDE,
                "external_url": "https://example.com/budget-basics",
            },
            {
                "title": "Pricing Your Products",
                "description": "Calculate fair prices that cover costs and generate profit.",
                "material_type": SkillLearningMaterial.TYPE_VIDEO,
                "external_url": "https://example.com/pricing-products.mp4",
            },
        ],
    },
    {
        "title": "Reading and Phonics",
        "description": "Build strong reading foundations with sounds, stories, and practice.",
        "badge_label": "Literacy",
        "filter_tags": ["Children", "Popular"],
        "cover_image_url": "https://images.unsplash.com/photo-1509062522246-3755977927d7?auto=format&fit=crop&w=900&q=80",
        "is_recommended": True,
        "popularity_score": 95,
        "materials": [
            {
                "title": "Letter Sounds Warmup",
                "description": "Quick activities for sound recognition.",
                "material_type": SkillLearningMaterial.TYPE_REFERENCE_GUIDE,
                "external_url": "https://example.com/letter-sounds",
            },
            {
                "title": "Story Time Session",
                "description": "Read along with a short story and prompts.",
                "material_type": SkillLearningMaterial.TYPE_VIDEO,
                "external_url": "https://example.com/story-time.mp4",
            },
            {
                "title": "Practice Sheets",
                "description": "Printable sheets for at-home practice.",
                "material_type": SkillLearningMaterial.TYPE_DOCUMENT,
                "external_url": "https://example.com/practice-sheets.pdf",
            },
        ],
    },
    {
        "title": "Math Basics",
        "description": "Explore counting, shapes, and everyday math skills.",
        "badge_label": "Numbers",
        "filter_tags": ["Children"],
        "cover_image_url": "https://images.unsplash.com/photo-1509228468518-180dd4864904?auto=format&fit=crop&w=900&q=80",
        "is_recommended": False,
        "popularity_score": 84,
        "materials": [
            {
                "title": "Counting in Daily Life",
                "description": "Use real objects to practice counting.",
                "material_type": SkillLearningMaterial.TYPE_DOCUMENT,
                "external_url": "https://example.com/counting-daily-life.pdf",
            },
            {
                "title": "Money Skills Workshop",
                "description": "Count and manage money in real-world situations.",
                "material_type": SkillLearningMaterial.TYPE_VIDEO,
                "external_url": "https://example.com/money-skills.mp4",
            },
            {
                "title": "Number Practice Cards",
                "description": "Printable cards for quick drills.",
                "material_type": SkillLearningMaterial.TYPE_REFERENCE_GUIDE,
                "external_url": "https://example.com/number-cards",
            },
        ],
    },
    {
        "title": "Creative Activities",
        "description": "Encourage imagination with crafts, drawing, and storytelling.",
        "badge_label": "Art",
        "filter_tags": ["Children", "New"],
        "cover_image_url": "https://images.unsplash.com/photo-1451665809-1e687f2d5ce7?auto=format&fit=crop&w=900&q=80",
        "is_recommended": False,
        "popularity_score": 68,
        "materials": [
            {
                "title": "Story Seeds",
                "description": "Prompts to spark new stories.",
                "material_type": SkillLearningMaterial.TYPE_REFERENCE_GUIDE,
                "external_url": "https://example.com/story-seeds",
            },
            {
                "title": "Drawing Techniques",
                "description": "Learn basic shapes and shading methods.",
                "material_type": SkillLearningMaterial.TYPE_VIDEO,
                "external_url": "https://example.com/drawing-techniques.mp4",
            },
            {
                "title": "Creative Journal",
                "description": "A template for weekly creative moments.",
                "material_type": SkillLearningMaterial.TYPE_DOCUMENT,
                "external_url": "https://example.com/creative-journal.pdf",
            },
        ],
    },
]


def _skill_learning_filter_tags(topic):
    tags = topic.filter_tags if isinstance(topic.filter_tags, list) else []
    ordered_tags = []
    for tag in tags:
        normalized = str(tag or "").strip()
        if normalized and normalized not in ordered_tags:
            ordered_tags.append(normalized)
    return ordered_tags


def _skill_learning_topic_payload(topic, material_engagements=None, recommended_ids=None):
    material_engagements = material_engagements or {}
    recommended_ids = recommended_ids or set()
    materials = list(topic.materials.all())
    completed_count = sum(1 for material in materials if material_engagements.get(material.id) and material_engagements[material.id].completed_at)
    return {
        "id": str(topic.id),
        "title": topic.title,
        "description": topic.description,
        "badgeLabel": topic.badge_label,
        "filterTags": _skill_learning_filter_tags(topic),
        "coverImageUrl": topic.cover_image_src,
        "isRecommended": topic.id in recommended_ids,
        "popularityScore": int(getattr(topic, "live_popularity_score", 0)),
        "primaryFilterTag": topic.primary_filter_tag,
        "completedMaterials": completed_count,
        "totalMaterials": len(materials),
        "progressPercent": round((completed_count / len(materials)) * 100) if materials else 0,
        "materials": [_skill_learning_material_payload(material, material_engagements.get(material.id)) for material in materials],
    }


def _skill_learning_material_payload(material, engagement=None):
    material_type_label = dict(SkillLearningMaterial.TYPE_CHOICES).get(material.material_type, material.material_type)
    return {
        "id": str(material.id),
        "topicId": str(material.topic_id),
        "materialType": material.material_type,
        "materialTypeLabel": material_type_label,
        "title": material.title,
        "description": material.description,
        "fileUrl": material.file_upload.url if material.file_upload else "",
        "externalUrl": material.external_url or "",
        "sourceUrl": material.source_url,
        "sourceName": material.source_name,
        "uploadedAt": timezone.localtime(material.created_at).isoformat() if material.created_at else "",
        "viewed": bool(engagement and engagement.view_count),
        "completed": bool(engagement and engagement.completed_at),
        "lastAccessedAt": timezone.localtime(engagement.last_accessed_at).isoformat() if engagement and engagement.last_accessed_at else "",
    }


def _skill_learning_activity_summary():
    material_scores = {}
    for engagement in SkillLearningMaterialEngagement.objects.select_related("material"):
        topic_id = engagement.material.topic_id
        score = material_scores.setdefault(topic_id, {"views": 0, "completions": 0})
        score["views"] += engagement.view_count
        if engagement.completed_at:
            score["completions"] += 1
    topic_opens = dict(SkillLearningTopicEngagement.objects.values_list("topic_id").annotate(total=Sum("page_open_count")))
    return {
        topic_id: (values["completions"] * 5) + (values["views"] * 2) + topic_opens.get(topic_id, 0)
        for topic_id, values in material_scores.items()
    } | {topic_id: topic_opens.get(topic_id, 0) for topic_id in topic_opens if topic_id not in material_scores}


def _skill_learning_recommended_ids(topics, popularity_scores, user):
    if not user or not user.is_authenticated:
        return set()
    material_engagements = SkillLearningMaterialEngagement.objects.filter(user=user).select_related("material")
    progress_by_topic = {}
    for engagement in material_engagements:
        progress = progress_by_topic.setdefault(engagement.material.topic_id, {"total": 0, "completed": 0})
        progress["completed"] += bool(engagement.completed_at)
    for topic in topics:
        if topic.id in progress_by_topic:
            progress_by_topic[topic.id]["total"] = topic.materials.count()
    activity_exists = bool(progress_by_topic) or SkillLearningTopicEngagement.objects.filter(user=user).exists()
    completed_topic_ids = {
        topic_id for topic_id, progress in progress_by_topic.items()
        if progress["total"] and progress["completed"] >= progress["total"]
    }
    if not activity_exists:
        return {topic.id for topic in sorted(topics, key=lambda topic: popularity_scores.get(topic.id, 0), reverse=True)[:3]}

    interest_tags = set()
    for topic in topics:
        progress = progress_by_topic.get(topic.id)
        if progress and progress["completed"] / max(progress["total"], 1) >= 0.5:
            interest_tags.update(_skill_learning_filter_tags(topic))
    matching = [
        topic for topic in topics
        if topic.id not in completed_topic_ids and interest_tags.intersection(_skill_learning_filter_tags(topic))
    ]
    return {topic.id for topic in sorted(matching, key=lambda topic: popularity_scores.get(topic.id, 0), reverse=True)[:3]}


def _skill_learning_payload(user=None):
    _ensure_skill_learning_content()
    topics = SkillLearningTopic.objects.prefetch_related("materials").all()
    popularity_scores = _skill_learning_activity_summary()
    for topic in topics:
        topic.live_popularity_score = popularity_scores.get(topic.id, 0)
    material_engagements = {}
    if user and user.is_authenticated:
        material_engagements = {
            engagement.material_id: engagement
            for engagement in SkillLearningMaterialEngagement.objects.filter(user=user)
        }
    recommended_ids = _skill_learning_recommended_ids(topics, popularity_scores, user)
    return {
        "topics": [_skill_learning_topic_payload(topic, material_engagements, recommended_ids) for topic in topics],
    }


def _ensure_skill_learning_content():
    if SkillLearningTopic.objects.exists():
        return

    for topic_data in SKILL_LEARNING_DEFAULT_TOPICS:
        materials_data = topic_data.pop("materials")
        topic = SkillLearningTopic.objects.create(**topic_data)
        for material_data in materials_data:
            SkillLearningMaterial.objects.create(topic=topic, **material_data)


def _notification_time_ago(value):
    if not value:
        return "Just now"

    delta = max(timezone.now() - value, timedelta(0))
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


NOTIFICATION_SETTING_KEYS = {
    CommunityNotification.TYPE_ROLE_APPLICATION: "notify_admin_applications",
    CommunityNotification.TYPE_BENEFICIARY_APPLICATION_DECISION: "notify_beneficiary_application_decisions",
    CommunityNotification.TYPE_VOLUNTEER_APPLICATION_DECISION: "notify_volunteer_application_decisions",
    CommunityNotification.TYPE_VOLUNTEER_ASSIGNMENT: "notify_volunteer_assignments",
    CommunityNotification.TYPE_ACTIVITY_END_REMINDER: "notify_volunteer_assignments",
    CommunityNotification.TYPE_DONATION_IMPACT: "notify_donation_impact",
}

EMAIL_NOTIFICATION_SETTING_KEY = "notify_email"


def _normalize_notification_setting_value(value, default=True):
    if value is None:
        return default

    if isinstance(value, list):
        return bool(value)

    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"0", "false", "off", "no", ""}:
            return False
        if lowered in {"1", "true", "on", "yes"}:
            return True

    return bool(value)


def _notification_enabled_for_user(user, notification_type):
    if not user or not user.is_authenticated:
        return False

    setting_name = NOTIFICATION_SETTING_KEYS.get(notification_type)
    if not setting_name:
        return True

    try:
        profile = user.userprofile
        state = profile.settings_state if isinstance(profile.settings_state, dict) else {}
    except UserProfile.DoesNotExist:
        state = {}

    return _normalize_notification_setting_value(state.get(setting_name), default=True)


def _email_notifications_enabled_for_user(user):
    if not user or not user.is_authenticated:
        return False

    try:
        profile = user.userprofile
        state = profile.settings_state if isinstance(profile.settings_state, dict) else {}
    except UserProfile.DoesNotExist:
        state = {}

    return _normalize_notification_setting_value(state.get(EMAIL_NOTIFICATION_SETTING_KEY), default=True)


def _send_plain_text_email(recipient_email, subject, body):
    recipient_email = str(recipient_email or "").strip()
    if not recipient_email:
        return False

    try:
        from django.conf import settings as _conf
        message = EmailMultiAlternatives(
            subject=subject,
            body=body,
            from_email=_conf.DEFAULT_FROM_EMAIL,
            to=[recipient_email],
        )
        message.send()
        return True
    except Exception as exc:
        print(f"[notifications] Email send failed for {recipient_email}: {exc}")
        return False


def _send_notification_email(recipient, subject, body):
    if not recipient or not getattr(recipient, "email", ""):
        return False

    if not _email_notifications_enabled_for_user(recipient):
        return False

    return _send_plain_text_email(recipient.email, subject, body)


def _create_in_app_notification(recipient, actor, notification_type, message, target_url="/user-dashboard/community/", post=None, comment=None):
    if not recipient or not actor:
        return None

    if recipient.id == actor.id:
        return None

    if not _notification_enabled_for_user(recipient, notification_type):
        return None

    return CommunityNotification.objects.create(
        recipient=recipient,
        actor=actor,
        notification_type=notification_type,
        post=post,
        comment=comment,
        message=message,
        target_url=target_url,
    )


def _send_donation_impact_update(donation, impact_update, actor=None):
    impact_text = (impact_update or "").strip()
    if not impact_text:
        return False

    donation.impact_update = impact_text
    donation.impact_update_sent_at = timezone.now()
    donation.save(update_fields=["impact_update", "impact_update_sent_at", "updated_at"])

    actor_user = actor or donation.user or None
    if donation.user_id and actor_user and donation.user_id != actor_user.id:
        actor_name = _display_name_for_user(actor_user)
        _create_in_app_notification(
            recipient=donation.user,
            actor=actor_user,
            notification_type=CommunityNotification.TYPE_DONATION_IMPACT,
            message=f"{actor_name} shared an impact update for your donation.",
            target_url=reverse("download_donation_receipt", args=[donation.reference_number]),
        )

    if donation.donor_email:
        donor_name = (donation.donor_name or "").strip() or (donation.user.get_full_name() if donation.user_id else "Donor") or "Donor"
        email_body = (
            f"Hi {donor_name},\n\n"
            f"Here is an update on the impact of your support:\n\n"
            f"{impact_text}\n\n"
            f"Thank you for helping make a difference in the HappYness Project community."
        )
        _send_plain_text_email(donation.donor_email, "Update on your donation impact", email_body)

    return True


def _send_application_decision_email(application, status):
    if not application.user_id:
        return

    status_label = "approved" if status == RoleApplication.STATUS_APPROVED else "rejected"
    subject = f"Your {application.role} application was {status_label}"
    body = (
        f"Hi {application.full_name},\n\n"
        f"Your {application.role} application was {status_label}. "
        f"Please check your dashboard for the latest details."
    )
    _send_notification_email(application.user, subject, body)


def _send_volunteer_assignment_email(volunteer, activity_name, scheduled_date):
    subject = f"New task assignment: {activity_name}"
    body = (
        f"Hi {volunteer.get_full_name() or volunteer.username},\n\n"
        f"You have been assigned to {activity_name} on {scheduled_date.strftime('%b %d, %Y')}. "
        f"Please check your dashboard for the full details."
    )
    _send_notification_email(volunteer, subject, body)


def _send_admin_application_email(admin_user, application):
    role_label = "beneficiary" if application.role == RoleApplication.ROLE_BENEFICIARY else "volunteer"
    subject = f"New {role_label} application waiting for review"
    body = (
        f"Hi {admin_user.get_full_name() or admin_user.username},\n\n"
        f"A new {role_label} application from {application.full_name} is waiting for approval. "
        f"Please open the admin dashboard to review it."
    )
    _send_notification_email(admin_user, subject, body)


def _create_community_notification(recipient, actor, notification_type, post=None, comment=None):
    if not recipient or not actor:
        return

    if recipient.id == actor.id:
        return

    actor_name = _display_name_for_user(actor)
    if notification_type == CommunityNotification.TYPE_POST_LIKE:
        message = f"{actor_name} liked your post."
    elif notification_type == CommunityNotification.TYPE_POST_COMMENT:
        message = f"{actor_name} commented on your post."
    elif notification_type == CommunityNotification.TYPE_COMMENT_REPLY:
        message = f"{actor_name} replied to your comment."
    else:
        return

    CommunityNotification.objects.create(
        recipient=recipient,
        actor=actor,
        notification_type=notification_type,
        post=post,
        comment=comment,
        message=message,
        target_url=reverse("user_dashboard_community"),
    )


def _serialize_community_notification(notification):
    target_url = notification.target_url or reverse("user_dashboard_community")
    if notification.notification_type == CommunityNotification.TYPE_ACTIVITY_ANNOUNCEMENT:
        target_url = reverse("user_dashboard") + "#distribution-outreach"
    elif notification.notification_type == CommunityNotification.TYPE_VOLUNTEER_ASSIGNMENT:
        target_url = reverse("volunteer_dashboard_tasks_ojt")

    return {
        "id": int(notification.id),
        "title": notification.message,
        "time_ago": _notification_time_ago(notification.created_at),
        "is_read": bool(notification.is_read),
        "url": target_url,
        "type": notification.notification_type,
    }


def _parse_non_negative_int(value, default=0):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default

    return parsed if parsed >= 0 else default


def _get_or_create_user_profile(user):
    profile, _created = UserProfile.objects.get_or_create(user=user)
    return profile


def _display_name_for_user(user):
    full_name = f"{user.first_name} {user.last_name}".strip()
    return full_name or user.first_name or user.username


def _split_contact_details(contact_details):
    email = ""
    phone = ""
    raw = str(contact_details or "").strip()
    if not raw:
        return email, phone

    parts = [part.strip() for part in raw.split("/") if part.strip()]
    for part in parts:
        if "@" in part and not email:
            email = part
        elif not phone:
            phone = part
        elif not email:
            email = part

    if not email and "@" in raw:
        email = raw
    elif not phone:
        phone = raw

    return email, phone


def _split_full_name(full_name):
    value = str(full_name or "").strip()
    if not value:
        return "", ""

    parts = value.split(None, 1)
    first_name = parts[0] if parts else ""
    last_name = parts[1] if len(parts) > 1 else ""
    return first_name, last_name


def _donation_payment_method_label(payment_method):
    return dict(Donation.PAYMENT_METHOD_CHOICES).get(payment_method, str(payment_method).replace("_", " ").title())


def _donation_status_label(status):
    return dict(Donation.STATUS_CHOICES).get(status, str(status).replace("_", " ").title())


def _serialize_donation(donation):
    created_at = timezone.localtime(donation.created_at)
    donor_name = (donation.donor_name or "").strip()
    if not donor_name and donation.user_id:
        donor_name = _display_name_for_user(donation.user)
    if not donor_name:
        donor_name = "Anonymous"

    status_label = _donation_status_label(donation.status)
    history = [f"Submitted - {created_at.strftime('%b %d, %Y')}"]
    if donation.status == Donation.STATUS_PENDING:
        history.append("Pending verification")
    elif donation.status == Donation.STATUS_VERIFIED:
        history.append("Verified")
    elif donation.status == Donation.STATUS_COMPLETED:
        history.append("Completed")
    elif donation.status == Donation.STATUS_REJECTED:
        history.append("Rejected")
    else:
        history.append("Cancelled")

    donor_info = [f"Method: {_donation_payment_method_label(donation.payment_method)}", f"Status: {status_label}"]
    if donation.campaign:
        donor_info.append(f"Campaign: {donation.campaign}")
    if donation.user_id:
        donor_info.append(f"User: {donation.user.username}")

    return {
        "id": int(donation.id),
        "date": created_at.strftime("%Y-%m-%d"),
        "donor": donor_name,
        "amount": int(donation.amount or 0),
        "method": _donation_payment_method_label(donation.payment_method),
        "methodLabel": _donation_payment_method_label(donation.payment_method),
        "status": donation.status,
        "statusLabel": status_label,
        "ref": donation.reference_number,
        "campaign": donation.campaign or "General Donation",
        "notes": donation.donor_message or donation.review_notes or "No notes provided.",
        "donorInfo": donor_info,
        "receipt": donation.receipt.url if donation.receipt else "",
        "receipt_url": donation.receipt.url if donation.receipt else "",
        "official_receipt_url": donation.official_receipt_file.url if donation.official_receipt_file else "",
        "official_receipt_number": donation.official_receipt_number or "",
        "official_receipt_generated_at": donation.official_receipt_generated_at.isoformat() if donation.official_receipt_generated_at else "",
        "history": history,
    }


def _serialize_volunteer_activity_assignment(assignment):
    scheduled_time = assignment.scheduled_time
    activity = assignment.activity
    status = assignment.status
    status_label = dict(VolunteerActivityAssignment.STATUS_CHOICES).get(status, status or "Pending")

    beneficiary_records = {}
    if activity_id := getattr(activity, "id", None):
        attendance_rows = BeneficiaryActivityAttendance.objects.filter(activity_id=activity_id, volunteer=assignment.volunteer).select_related("beneficiary")
        for row in attendance_rows:
            beneficiary_records[row.beneficiary_id] = _serialize_beneficiary_activity_attendance(row)

    beneficiaries = []
    if activity is not None:
        for beneficiary_assignment in activity.beneficiary_assignments.select_related("beneficiary").all():
            beneficiary = beneficiary_assignment.beneficiary
            payload = {
                "id": int(beneficiary.id),
                "name": beneficiary.get_full_name() or beneficiary.username,
                "avatar_url": beneficiary.userprofile.avatar.url if getattr(getattr(beneficiary, "userprofile", None), "avatar", None) else "",
                "status": beneficiary_records.get(beneficiary.id, {}).get("status", BeneficiaryActivityAttendance.STATUS_PENDING),
                "status_label": beneficiary_records.get(beneficiary.id, {}).get("status_label", "Pending"),
                "confirmed_at": beneficiary_records.get(beneficiary.id, {}).get("confirmed_at", ""),
            }
            beneficiaries.append(payload)

    return {
        "id": int(assignment.id),
        "activity_id": int(activity.id) if activity else int(assignment.id),
        "activity_name": assignment.activity_name,
        "activity_type": assignment.activity_type or "",
        "activity_description": activity.description if activity else "",
        "image_url": _activity_image_url(activity) if activity else "",
        "date": assignment.scheduled_date.strftime("%Y-%m-%d"),
        "time": scheduled_time.strftime("%H:%M") if scheduled_time else "",
        "end_time": activity.end_time.strftime("%H:%M") if activity and activity.end_time else "",
        "location": assignment.location or "",
        "status": status,
        "status_label": status_label,
        "attendance_started_at": assignment.attendance_started_at.isoformat() if assignment.attendance_started_at else "",
        "attendance_ended_at": assignment.attendance_ended_at.isoformat() if assignment.attendance_ended_at else "",
        "notes": assignment.notes or "",
        "beneficiaries": beneficiaries,
        "attendance_pending": assignment.attendance_records.filter(status=VolunteerAttendanceRecord.STATUS_PENDING).exists(),
        "attendance": [
            _serialize_volunteer_attendance(record)
            for record in assignment.attendance_records.select_related("reviewed_by").all()
        ],
    }


def _calculate_duration_minutes(time_in, time_out):
    if not time_in or not time_out:
        return 0
    delta = time_out - time_in
    if delta.total_seconds() <= 0:
        return 0
    duration_minutes = int(delta.total_seconds() // 60)
    if duration_minutes >= 9 * 60:
        duration_minutes -= 60
    return duration_minutes


def _sync_volunteer_attendance_hours(profile, *, add_minutes=0, remove_minutes=0):
    if profile is None:
        return
    total_minutes = float(profile.ojt_hours or 0) * 60
    total_minutes += float(add_minutes or 0)
    total_minutes -= float(remove_minutes or 0)
    total_minutes = max(0, total_minutes)
    profile.ojt_hours = round(total_minutes / 60, 2)
    profile.save(update_fields=["ojt_hours", "updated_at"])


def _serialize_volunteer_attendance(attendance):
    return {
        "id": int(attendance.id),
        "assignment_id": int(attendance.assignment_id) if attendance.assignment_id else None,
        "volunteer_id": int(attendance.volunteer_id),
        "time_in": attendance.time_in.isoformat() if attendance.time_in else "",
        "time_out": attendance.time_out.isoformat() if attendance.time_out else "",
        "duration_minutes": int(attendance.duration_minutes or 0),
        "status": attendance.status,
        "status_label": dict(VolunteerAttendanceRecord.STATUS_CHOICES).get(attendance.status, attendance.status),
        "duty_date": attendance.duty_date.isoformat() if attendance.duty_date else "",
        "auto_closed": bool(attendance.auto_closed),
        "reviewed_by": _display_name_for_user(attendance.reviewed_by) if attendance.reviewed_by else "",
        "reviewed_at": attendance.reviewed_at.isoformat() if attendance.reviewed_at else "",
        "notes": attendance.notes or "",
    }


def _ojt_schedule_for_date(volunteer, duty_date):
    return VolunteerOjtSchedule.objects.filter(
        volunteer=volunteer,
        effective_from__lte=duty_date,
    ).filter(
        Q(effective_until__isnull=True) | Q(effective_until__gte=duty_date),
    ).order_by("-effective_from", "-id").first()


def _ojt_schedule_day_times(schedule, duty_date):
    if not schedule:
        return None, None
    weekdays = {int(day) for day in (schedule.weekdays or []) if str(day).isdigit()}
    if duty_date.weekday() not in weekdays:
        return None, None
    day_times = (schedule.daily_times or {}).get(str(duty_date.weekday()), {})
    try:
        start_time = time.fromisoformat(day_times["start"]) if day_times.get("start") else time(8, 0)
        end_time = time.fromisoformat(day_times["end"]) if day_times.get("end") else None
    except (TypeError, ValueError):
        return None, None
    return start_time, end_time


def _ojt_is_duty_date(schedule, duty_date):
    if not schedule:
        return False
    return duty_date.weekday() in {int(day) for day in (schedule.weekdays or []) if str(day).isdigit()}


def _ojt_duty_window(schedule, duty_date):
    if not _ojt_is_duty_date(schedule, duty_date):
        return None, None
    start_time, end_time = _ojt_schedule_day_times(schedule, duty_date)
    local_timezone = timezone.get_current_timezone()
    start_at = timezone.make_aware(datetime.combine(duty_date, start_time or time(8, 0)), local_timezone)
    end_at = timezone.make_aware(datetime.combine(duty_date, end_time or time.max), local_timezone)
    return start_at, end_at


def _ojt_duty_day_payload(duty_date, schedule, records, assignments, now):
    if not _ojt_is_duty_date(schedule, duty_date):
        return None

    start_time, end_time = _ojt_schedule_day_times(schedule, duty_date)
    _, window_end = _ojt_duty_window(schedule, duty_date)
    latest_record = records[-1] if records else None
    status = "upcoming"
    if latest_record:
        if latest_record.status == VolunteerAttendanceRecord.STATUS_ACTIVE:
            status = "active"
        elif latest_record.status == VolunteerAttendanceRecord.STATUS_PENDING:
            status = "pending"
        elif latest_record.status == VolunteerAttendanceRecord.STATUS_CONFIRMED:
            status = "done"
        elif latest_record.status == VolunteerAttendanceRecord.STATUS_REJECTED:
            status = "missed"
    elif any(item.status in {VolunteerActivityAssignment.STATUS_TIME_IN, VolunteerActivityAssignment.STATUS_IN_PROGRESS} for item in assignments):
        status = "active"
    elif any(item.status == VolunteerActivityAssignment.STATUS_AWAITING_CONFIRMATION for item in assignments):
        status = "pending"
    elif any(item.status == VolunteerActivityAssignment.STATUS_COMPLETED for item in assignments):
        status = "done"
    elif any(item.status == VolunteerActivityAssignment.STATUS_MISSED for item in assignments):
        status = "missed"
    elif duty_date < now.date() or (duty_date == now.date() and window_end and now >= timezone.localtime(window_end)):
        status = "missed"

    credited_minutes = sum(
        int(record.duration_minutes or 0)
        for record in records
        if record.status == VolunteerAttendanceRecord.STATUS_CONFIRMED
    )
    duration_minutes = sum(int(record.duration_minutes or 0) for record in records)
    return {
        "date": duty_date.isoformat(),
        "status": status,
        "start_time": start_time.strftime("%H:%M") if start_time else "",
        "end_time": end_time.strftime("%H:%M") if end_time else "",
        "assignment_id": int(assignments[0].id) if assignments else None,
        "attendance_record_id": int(latest_record.id) if latest_record else None,
        "auto_closed": bool(latest_record.auto_closed) if latest_record else False,
        "credited_hours": round(credited_minutes / 60, 2),
        "hours": round(duration_minutes / 60, 2),
        "time_in": latest_record.time_in.isoformat() if latest_record and latest_record.time_in else "",
    }


def _attendance_exists_for_day(volunteer, duty_date):
    return VolunteerAttendanceRecord.objects.filter(volunteer=volunteer).filter(
        Q(duty_date=duty_date) | Q(assignment__scheduled_date=duty_date),
    ).exists()


def _auto_close_expired_duty_sessions(volunteer=None, now=None):
    now = timezone.localtime(now or timezone.now())
    active_records = VolunteerAttendanceRecord.objects.filter(
        status=VolunteerAttendanceRecord.STATUS_ACTIVE,
        duty_date__isnull=False,
    ).select_related("volunteer", "duty_schedule")
    if volunteer is not None:
        active_records = active_records.filter(volunteer=volunteer)
    for attendance in active_records:
        schedule = attendance.duty_schedule or _ojt_schedule_for_date(attendance.volunteer, attendance.duty_date)
        _, end_at = _ojt_duty_window(schedule, attendance.duty_date)
        if end_at and now >= end_at and attendance.time_in:
            time_out = max(end_at, attendance.time_in + timedelta(minutes=1))
            attendance.time_out = time_out
            attendance.duration_minutes = _calculate_duration_minutes(attendance.time_in, time_out) or 1
            attendance.status = VolunteerAttendanceRecord.STATUS_PENDING
            attendance.auto_closed = True
            attendance.notes = attendance.notes or "Automatically timed out at the end of the OJT duty window; review required."
            attendance.save(update_fields=["time_out", "duration_minutes", "status", "auto_closed", "notes", "updated_at"])

    active_assignments = VolunteerActivityAssignment.objects.filter(
        status__in=[VolunteerActivityAssignment.STATUS_TIME_IN, VolunteerActivityAssignment.STATUS_IN_PROGRESS],
    ).select_related("volunteer")
    if volunteer is not None:
        active_assignments = active_assignments.filter(volunteer=volunteer)
    for assignment in active_assignments:
        schedule = _ojt_schedule_for_date(assignment.volunteer, assignment.scheduled_date)
        _, end_at = _ojt_duty_window(schedule, assignment.scheduled_date)
        if not end_at or now < end_at or not assignment.attendance_started_at:
            continue
        active_record = assignment.attendance_records.filter(status=VolunteerAttendanceRecord.STATUS_ACTIVE).order_by("-id").first()
        if not active_record and (assignment.attendance_records.exists() or _attendance_exists_for_day(assignment.volunteer, assignment.scheduled_date)):
            continue
        time_out = max(end_at, assignment.attendance_started_at + timedelta(minutes=1))
        duration_minutes = _calculate_duration_minutes(assignment.attendance_started_at, time_out) or 1
        assignment.attendance_ended_at = time_out
        assignment.status = VolunteerActivityAssignment.STATUS_AWAITING_CONFIRMATION
        assignment.save(update_fields=["attendance_ended_at", "status", "updated_at"])
        if active_record:
            active_record.time_out = time_out
            active_record.duration_minutes = duration_minutes
            active_record.status = VolunteerAttendanceRecord.STATUS_PENDING
            active_record.auto_closed = True
            active_record.notes = active_record.notes or "Automatically timed out at the end of the OJT duty window; review required."
            active_record.save(update_fields=["time_out", "duration_minutes", "status", "auto_closed", "notes", "updated_at"])
        else:
            VolunteerAttendanceRecord.objects.create(
                assignment=assignment,
                volunteer=assignment.volunteer,
                duty_schedule=schedule,
                duty_date=assignment.scheduled_date,
                time_in=assignment.attendance_started_at,
                time_out=time_out,
                duration_minutes=duration_minutes,
                auto_closed=True,
                notes="Automatically timed out at the end of the OJT duty window; review required.",
            )


def _serialize_beneficiary_activity_attendance(attendance):
    if attendance.status == BeneficiaryActivityAttendance.STATUS_PENDING and attendance.confirmed_at:
        status_label = "Awaiting approval"
    else:
        status_label = dict(BeneficiaryActivityAttendance.STATUS_CHOICES).get(attendance.status, attendance.status)
    return {
        "id": int(attendance.id),
        "activity_id": int(attendance.activity_id),
        "beneficiary_id": int(attendance.beneficiary_id),
        "volunteer_id": int(attendance.volunteer_id),
        "status": attendance.status,
        "status_label": status_label,
        "confirmed_at": attendance.confirmed_at.isoformat() if attendance.confirmed_at else "",
        "reviewed_at": attendance.reviewed_at.isoformat() if attendance.reviewed_at else "",
        "notes": attendance.notes or "",
    }


@login_required(login_url="signin")
@require_POST
def volunteer_activity_attendance(request):
    if request.user.is_superuser:
        return JsonResponse({"error": "Only volunteers can access this endpoint."}, status=403)

    profile = _get_or_create_user_profile(request.user)
    if profile.account_role != UserProfile.ROLE_VOLUNTEER:
        return JsonResponse({"error": "Only active volunteers can update attendance."}, status=403)

    assignment_id = str(request.POST.get("assignment_id") or request.POST.get("assignmentId") or "").strip()
    duty_date_raw = str(request.POST.get("duty_date") or "").strip()
    action = str(request.POST.get("action") or "").strip().lower()
    now = timezone.now()
    local_now = timezone.localtime(now)

    if not assignment_id and not duty_date_raw:
        return JsonResponse({"error": "An assignment_id or duty_date is required."}, status=400)

    if duty_date_raw and not assignment_id:
        try:
            duty_date = date.fromisoformat(duty_date_raw)
        except ValueError:
            return JsonResponse({"error": "duty_date must be a valid date."}, status=400)
        if action == "time_in":
            if duty_date != timezone.localdate(now):
                return JsonResponse({"error": "OJT time in is only available on the scheduled duty day."}, status=400)
            schedule = _ojt_schedule_for_date(request.user, duty_date)
            if not _ojt_is_duty_date(schedule, duty_date):
                return JsonResponse({"error": "No OJT duty schedule is active for this date."}, status=400)
            start_at, end_at = _ojt_duty_window(schedule, duty_date)
            if now < start_at or now >= end_at:
                return JsonResponse({"error": "OJT time in is only available during the scheduled duty window."}, status=400)
            if VolunteerActivityAssignment.objects.filter(
                volunteer=request.user,
                scheduled_date=duty_date,
            ).exclude(status=VolunteerActivityAssignment.STATUS_CANCELLED).exists():
                return JsonResponse({"error": "Use the assigned activity to time in for this duty day."}, status=400)

            with transaction.atomic():
                User.objects.select_for_update().get(pk=request.user.pk)
                if _attendance_exists_for_day(request.user, duty_date) or VolunteerActivityAssignment.objects.filter(
                    volunteer=request.user,
                    scheduled_date=duty_date,
                    status__in=[VolunteerActivityAssignment.STATUS_TIME_IN, VolunteerActivityAssignment.STATUS_IN_PROGRESS],
                ).exists():
                    return JsonResponse({"error": "An attendance session already exists for this day."}, status=409)
                attendance = VolunteerAttendanceRecord.objects.create(
                    volunteer=request.user,
                    duty_schedule=schedule,
                    duty_date=duty_date,
                    time_in=now,
                    status=VolunteerAttendanceRecord.STATUS_ACTIVE,
                )
            return JsonResponse({"message": "OJT duty time in recorded.", "status": attendance.status, "attendance": _serialize_volunteer_attendance(attendance)})

        if action == "time_out":
            _auto_close_expired_duty_sessions(request.user, now=now)
            with transaction.atomic():
                attendance = VolunteerAttendanceRecord.objects.select_for_update().filter(
                    volunteer=request.user,
                    duty_date=duty_date,
                    assignment__isnull=True,
                    status=VolunteerAttendanceRecord.STATUS_ACTIVE,
                ).first()
                if not attendance:
                    existing = VolunteerAttendanceRecord.objects.filter(
                        volunteer=request.user,
                        duty_date=duty_date,
                        assignment__isnull=True,
                    ).order_by("-id").first()
                    if existing and existing.status == VolunteerAttendanceRecord.STATUS_PENDING and existing.auto_closed:
                        return JsonResponse({"message": "Session was auto-closed and is awaiting admin review.", "status": existing.status, "attendance": _serialize_volunteer_attendance(existing)})
                    return JsonResponse({"error": "No active OJT duty session was found."}, status=400)
                attendance.time_out = now
                attendance.duration_minutes = _calculate_duration_minutes(attendance.time_in, now) or 1
                attendance.status = VolunteerAttendanceRecord.STATUS_PENDING
                attendance.save(update_fields=["time_out", "duration_minutes", "status", "updated_at"])
            return JsonResponse({"message": "Time out recorded. Awaiting admin confirmation.", "status": attendance.status, "attendance": _serialize_volunteer_attendance(attendance)})

        return JsonResponse({"error": "Unsupported attendance action."}, status=400)

    assignment = get_object_or_404(VolunteerActivityAssignment, id=assignment_id, volunteer=request.user)

    if action == "time_in":
        if assignment.scheduled_date != timezone.localdate(now):
            return JsonResponse({"error": "Activity time in is only available on its scheduled date."}, status=400)
        if assignment.status in {VolunteerActivityAssignment.STATUS_COMPLETED, VolunteerActivityAssignment.STATUS_CANCELLED, VolunteerActivityAssignment.STATUS_MISSED, VolunteerActivityAssignment.STATUS_AWAITING_CONFIRMATION}:
            return JsonResponse({"error": "This assignment cannot be re-opened."}, status=400)
        if assignment.status in {VolunteerActivityAssignment.STATUS_TIME_IN, VolunteerActivityAssignment.STATUS_IN_PROGRESS}:
            return JsonResponse({"error": "This assignment already has an active session."}, status=409)
        schedule = _ojt_schedule_for_date(request.user, assignment.scheduled_date)
        is_duty_date = _ojt_is_duty_date(schedule, assignment.scheduled_date)
        if is_duty_date:
            start_at, end_at = _ojt_duty_window(schedule, assignment.scheduled_date)
            if now < start_at or now >= end_at:
                return JsonResponse({"error": "Time in is only available during the scheduled duty window."}, status=400)
        with transaction.atomic():
            User.objects.select_for_update().get(pk=request.user.pk)
            assignment = VolunteerActivityAssignment.objects.select_for_update().get(pk=assignment.pk, volunteer=request.user)
            if _attendance_exists_for_day(request.user, assignment.scheduled_date) or VolunteerActivityAssignment.objects.filter(
                volunteer=request.user,
                scheduled_date=assignment.scheduled_date,
                status__in=[VolunteerActivityAssignment.STATUS_TIME_IN, VolunteerActivityAssignment.STATUS_IN_PROGRESS],
            ).exclude(pk=assignment.pk).exists():
                return JsonResponse({"error": "An attendance session already exists for this day."}, status=409)
            assignment.status = VolunteerActivityAssignment.STATUS_TIME_IN
            assignment.attendance_started_at = now
            assignment.attendance_ended_at = None
            assignment.save(update_fields=["status", "attendance_started_at", "attendance_ended_at", "updated_at"])
            if is_duty_date:
                VolunteerAttendanceRecord.objects.create(
                    assignment=assignment,
                    volunteer=request.user,
                    duty_schedule=schedule,
                    duty_date=assignment.scheduled_date,
                    time_in=now,
                    status=VolunteerAttendanceRecord.STATUS_ACTIVE,
                )
        return JsonResponse({"message": "Time in recorded.", "status": assignment.status})

    if action == "time_out":
        _auto_close_expired_duty_sessions(request.user, now=now)
        assignment.refresh_from_db()
        if assignment.status == VolunteerActivityAssignment.STATUS_AWAITING_CONFIRMATION:
            record = assignment.attendance_records.order_by("-created_at", "-id").first()
            if record and record.auto_closed:
                return JsonResponse({"message": "Session was auto-closed and is awaiting admin review.", "status": assignment.status, "attendance": _serialize_volunteer_attendance(record)})
        if assignment.status not in {VolunteerActivityAssignment.STATUS_TIME_IN, VolunteerActivityAssignment.STATUS_IN_PROGRESS}:
            return JsonResponse({"error": "You must time in before timing out."}, status=400)
        schedule = _ojt_schedule_for_date(request.user, assignment.scheduled_date)
        is_duty_date = _ojt_is_duty_date(schedule, assignment.scheduled_date)
        _, duty_end_at = _ojt_duty_window(schedule, assignment.scheduled_date) if is_duty_date else (None, None)
        auto_closed = bool(duty_end_at and now >= duty_end_at)
        time_out = duty_end_at if auto_closed else now
        assignment.attendance_ended_at = time_out
        assignment.status = VolunteerActivityAssignment.STATUS_AWAITING_CONFIRMATION
        assignment.save(update_fields=["status", "attendance_ended_at", "updated_at"])

        time_in = assignment.attendance_started_at or now.replace(second=0, microsecond=0)
        duration_minutes = _calculate_duration_minutes(time_in, time_out)
        if duration_minutes <= 0:
            duration_minutes = 1

        record = assignment.attendance_records.filter(status=VolunteerAttendanceRecord.STATUS_ACTIVE).order_by("-id").first()
        if record:
            record.time_out = time_out
            record.duration_minutes = duration_minutes
            record.status = VolunteerAttendanceRecord.STATUS_PENDING
            record.auto_closed = auto_closed
            if auto_closed:
                record.notes = "Automatically timed out at the end of the OJT duty window; review required."
            record.save(update_fields=["time_out", "duration_minutes", "status", "auto_closed", "notes", "updated_at"])
        else:
            record = VolunteerAttendanceRecord.objects.create(
                assignment=assignment,
                volunteer=request.user,
                duty_schedule=schedule if is_duty_date else None,
                duty_date=assignment.scheduled_date if is_duty_date else None,
                time_in=time_in,
                time_out=time_out,
                duration_minutes=duration_minutes,
                auto_closed=auto_closed,
                notes="Automatically timed out at the end of the OJT duty window; review required." if auto_closed else "",
            )
        return JsonResponse({
            "message": "Time out recorded. Awaiting admin confirmation.",
            "status": assignment.status,
            "attendance": _serialize_volunteer_attendance(record),
        })

    if action == "mark_in_progress":
        if assignment.scheduled_date != timezone.localdate(now):
            return JsonResponse({"error": "Activity time in is only available on its scheduled date."}, status=400)
        with transaction.atomic():
            User.objects.select_for_update().get(pk=request.user.pk)
            assignment = VolunteerActivityAssignment.objects.select_for_update().get(pk=assignment.pk, volunteer=request.user)
            if _attendance_exists_for_day(request.user, assignment.scheduled_date):
                return JsonResponse({"error": "An attendance session already exists for this day."}, status=409)
            assignment.status = VolunteerActivityAssignment.STATUS_IN_PROGRESS
            assignment.attendance_started_at = now
            assignment.attendance_ended_at = None
            assignment.save(update_fields=["status", "attendance_started_at", "attendance_ended_at", "updated_at"])
        return JsonResponse({"message": "Marked as in progress.", "status": assignment.status})

    return JsonResponse({"error": "Unsupported attendance action."}, status=400)


@login_required(login_url="signin")
@require_POST
def volunteer_beneficiary_attendance(request):
    if request.user.is_superuser:
        return JsonResponse({"error": "Only volunteers can access this endpoint."}, status=403)

    profile = _get_or_create_user_profile(request.user)
    if profile.account_role != UserProfile.ROLE_VOLUNTEER:
        return JsonResponse({"error": "Only active volunteers can confirm beneficiary attendance."}, status=403)

    activity_id = str(request.POST.get("activity_id") or request.POST.get("activityId") or "").strip()
    beneficiary_id = str(request.POST.get("beneficiary_id") or request.POST.get("beneficiaryId") or "").strip()
    action = str(request.POST.get("action") or "").strip().lower()

    if not activity_id or not beneficiary_id:
        return JsonResponse({"error": "activity_id and beneficiary_id are required."}, status=400)

    if action not in {"confirm", "reject"}:
        return JsonResponse({"error": "Unsupported beneficiary attendance action."}, status=400)

    assignment = VolunteerActivityAssignment.objects.filter(activity_id=activity_id, volunteer=request.user).first()
    if assignment is None:
        return JsonResponse({"error": "Only the assigned volunteer can confirm this beneficiary attendance."}, status=403)
    if assignment.status not in {VolunteerActivityAssignment.STATUS_TIME_IN, VolunteerActivityAssignment.STATUS_IN_PROGRESS}:
        return JsonResponse({"error": "Time in before managing beneficiary attendance."}, status=400)

    beneficiary_assignment = ActivityBeneficiaryAssignment.objects.filter(activity_id=activity_id, beneficiary_id=beneficiary_id).first()
    if beneficiary_assignment is None:
        return JsonResponse({"error": "This beneficiary is not assigned to the selected activity."}, status=404)

    record, created = BeneficiaryActivityAttendance.objects.get_or_create(
        activity_id=activity_id,
        beneficiary_id=beneficiary_id,
        volunteer=request.user,
    )
    if action == "confirm":
        record.status = BeneficiaryActivityAttendance.STATUS_CONFIRMED
        record.confirmed_at = timezone.now()
        record.reviewed_by = None
        record.reviewed_at = None
        record.notes = str(request.POST.get("notes") or "").strip() or record.notes or "Confirmed by assigned volunteer."
        record.save(update_fields=["status", "confirmed_at", "reviewed_by", "reviewed_at", "notes", "updated_at"])
        return JsonResponse({"message": "Beneficiary attendance confirmed.", "record": _serialize_beneficiary_activity_attendance(record)})

    record.status = BeneficiaryActivityAttendance.STATUS_REJECTED
    record.confirmed_at = None
    record.reviewed_by = None
    record.reviewed_at = None
    record.notes = str(request.POST.get("notes") or "").strip() or "Rejected by assigned volunteer."
    record.save(update_fields=["status", "confirmed_at", "reviewed_by", "reviewed_at", "notes", "updated_at"])
    return JsonResponse({"message": "Beneficiary attendance marked as rejected.", "record": _serialize_beneficiary_activity_attendance(record)})


@login_required(login_url="signin")
@require_POST
def review_beneficiary_attendance(request):
    if not request.user.is_superuser:
        return JsonResponse({"error": "Only administrators can review beneficiary attendance."}, status=403)

    attendance_id = str(request.POST.get("attendance_id") or request.POST.get("attendanceId") or "").strip()
    action = str(request.POST.get("action") or "").strip().lower()
    if not attendance_id:
        return JsonResponse({"error": "attendance_id is required."}, status=400)
    if action not in {"confirm", "reject"}:
        return JsonResponse({"error": "Unsupported beneficiary attendance review action."}, status=400)

    attendance = get_object_or_404(BeneficiaryActivityAttendance, id=attendance_id)
    if action == "confirm":
        attendance.status = BeneficiaryActivityAttendance.STATUS_CONFIRMED
        attendance.reviewed_by = request.user
        attendance.reviewed_at = timezone.now()
        attendance.notes = attendance.notes or "Approved by admin."
        message = "Beneficiary attendance approved."
    else:
        attendance.status = BeneficiaryActivityAttendance.STATUS_REJECTED
        attendance.reviewed_by = request.user
        attendance.reviewed_at = timezone.now()
        attendance.notes = str(request.POST.get("notes") or "").strip() or "Rejected by admin review."
        message = "Beneficiary attendance rejected."
    attendance.save(update_fields=["status", "reviewed_by", "reviewed_at", "notes", "updated_at"])
    return JsonResponse({"message": message, "record": _serialize_beneficiary_activity_attendance(attendance)})


@login_required(login_url="signin")
@require_POST
def review_volunteer_attendance(request):
    if not request.user.is_superuser:
        return JsonResponse({"error": "Only administrators can review attendance."}, status=403)

    attendance_id = str(request.POST.get("attendance_id") or request.POST.get("attendanceId") or "").strip()
    action = str(request.POST.get("action") or "").strip().lower()
    if not attendance_id:
        return JsonResponse({"error": "attendance_id is required."}, status=400)

    with transaction.atomic():
        attendance = get_object_or_404(VolunteerAttendanceRecord.objects.select_for_update().select_related("assignment"), id=attendance_id)
        if attendance.status != VolunteerAttendanceRecord.STATUS_PENDING:
            return JsonResponse({"error": "Only pending attendance can be reviewed."}, status=409)
        assignment = attendance.assignment
        if action == "confirm":
            attendance.status = VolunteerAttendanceRecord.STATUS_CONFIRMED
            attendance.reviewed_by = request.user
            attendance.reviewed_at = timezone.now()
            attendance.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])
            if assignment:
                assignment.status = VolunteerActivityAssignment.STATUS_COMPLETED
                assignment.attendance_ended_at = attendance.time_out or assignment.attendance_ended_at
                assignment.save(update_fields=["status", "attendance_ended_at", "updated_at"])
            _sync_volunteer_attendance_hours(_get_or_create_user_profile(attendance.volunteer), add_minutes=attendance.duration_minutes)
            return JsonResponse({
                "message": "Attendance confirmed and hours credited.",
                "status": assignment.status if assignment else attendance.status,
                "attendance": _serialize_volunteer_attendance(attendance),
            })

        if action == "reject":
            attendance.status = VolunteerAttendanceRecord.STATUS_REJECTED
            attendance.reviewed_by = request.user
            attendance.reviewed_at = timezone.now()
            attendance.notes = str(request.POST.get("notes") or "").strip() or attendance.notes or "Rejected by admin review."
            attendance.save(update_fields=["status", "reviewed_by", "reviewed_at", "notes", "updated_at"])
            if assignment:
                assignment.status = VolunteerActivityAssignment.STATUS_MISSED
                assignment.save(update_fields=["status", "updated_at"])
            return JsonResponse({
                "message": "Attendance rejected.",
                "status": assignment.status if assignment else attendance.status,
                "attendance": _serialize_volunteer_attendance(attendance),
            })

    return JsonResponse({"error": "Unsupported review action."}, status=400)


@login_required(login_url="signin")
@require_POST
def force_timeout_volunteer_attendance(request):
    if not request.user.is_superuser:
        return JsonResponse({"error": "Only administrators can force time out attendance."}, status=403)

    attendance_id = str(request.POST.get("attendance_id") or request.POST.get("attendanceId") or "").strip()
    assignment_id = str(request.POST.get("assignment_id") or request.POST.get("assignmentId") or "").strip()
    if not attendance_id and not assignment_id:
        return JsonResponse({"error": "An assignment_id or attendance_id is required."}, status=400)

    now = timezone.now()
    if attendance_id:
        with transaction.atomic():
            record = get_object_or_404(VolunteerAttendanceRecord.objects.select_for_update(), id=attendance_id)
            if record.status != VolunteerAttendanceRecord.STATUS_ACTIVE or record.assignment_id:
                return JsonResponse({"error": "This attendance session is no longer in progress."}, status=400)
            record.time_out = now
            record.duration_minutes = _calculate_duration_minutes(record.time_in, now) or 1
            record.status = VolunteerAttendanceRecord.STATUS_PENDING
            record.save(update_fields=["time_out", "duration_minutes", "status", "updated_at"])
    else:
        assignment = get_object_or_404(VolunteerActivityAssignment, id=assignment_id)
        if assignment.status not in {VolunteerActivityAssignment.STATUS_TIME_IN, VolunteerActivityAssignment.STATUS_IN_PROGRESS}:
            return JsonResponse({"error": "This attendance session is no longer in progress."}, status=400)

        time_in = assignment.attendance_started_at or now.replace(second=0, microsecond=0)
        schedule = _ojt_schedule_for_date(assignment.volunteer, assignment.scheduled_date)
        is_duty_date = _ojt_is_duty_date(schedule, assignment.scheduled_date)
        _, end_at = _ojt_duty_window(schedule, assignment.scheduled_date) if is_duty_date else (None, None)
        auto_closed = bool(end_at and now >= end_at)
        time_out = end_at if auto_closed else now
        duration_minutes = _calculate_duration_minutes(time_in, time_out) or 1

        with transaction.atomic():
            assignment = VolunteerActivityAssignment.objects.select_for_update().get(pk=assignment.pk)
            assignment.attendance_ended_at = time_out
            assignment.status = VolunteerActivityAssignment.STATUS_AWAITING_CONFIRMATION
            assignment.save(update_fields=["status", "attendance_ended_at", "updated_at"])
            record = assignment.attendance_records.filter(status=VolunteerAttendanceRecord.STATUS_ACTIVE).order_by("-id").first()
            if record:
                record.time_out = time_out
                record.duration_minutes = duration_minutes
                record.status = VolunteerAttendanceRecord.STATUS_PENDING
                record.auto_closed = auto_closed
                if auto_closed:
                    record.notes = "Automatically timed out at the end of the OJT duty window; review required."
                record.save(update_fields=["time_out", "duration_minutes", "status", "auto_closed", "notes", "updated_at"])
            else:
                record = VolunteerAttendanceRecord.objects.create(
                    assignment=assignment,
                    volunteer=assignment.volunteer,
                    duty_schedule=schedule if is_duty_date else None,
                    duty_date=assignment.scheduled_date if is_duty_date else None,
                    time_in=time_in,
                    time_out=time_out,
                    duration_minutes=duration_minutes,
                    auto_closed=auto_closed,
                    notes="Automatically timed out at the end of the OJT duty window; review required." if auto_closed else "",
                )
    return JsonResponse({
        "message": "Attendance timed out. Awaiting admin confirmation.",
        "status": assignment.status,
        "attendance": _serialize_volunteer_attendance(record),
    })


def _parse_volunteer_ids(raw_values):
    values = []
    if isinstance(raw_values, (list, tuple, set)):
        values.extend(raw_values)
    elif raw_values is not None:
        values.append(raw_values)

    volunteer_ids = []
    for raw_value in values:
        if raw_value is None:
            continue
        if isinstance(raw_value, (list, tuple, set)):
            volunteer_ids.extend(_parse_volunteer_ids(raw_value))
            continue
        for item in str(raw_value).split(","):
            item = item.strip()
            if item:
                try:
                    volunteer_ids.append(int(item))
                except ValueError:
                    continue

    unique_ids = []
    seen = set()
    for volunteer_id in volunteer_ids:
        if volunteer_id not in seen:
            seen.add(volunteer_id)
            unique_ids.append(volunteer_id)
    return unique_ids


def _extract_activity_volunteer_ids(post_data):
    # Accept all current and legacy payload shapes from the activity form.
    candidate_values = []
    candidate_values.extend(post_data.getlist("volunteer_ids[]"))
    candidate_values.extend(post_data.getlist("volunteer_ids"))
    candidate_values.extend(post_data.getlist("volunteerIds"))

    single_legacy = str(post_data.get("volunteerIds", "") or "").strip()
    if single_legacy:
        candidate_values.append(single_legacy)

    return _parse_volunteer_ids(candidate_values)


def _clear_activity_assignment_notifications(volunteer, activity_name=None):
    if not volunteer:
        return
    notification_query = CommunityNotification.objects.filter(
        recipient=volunteer,
        notification_type=CommunityNotification.TYPE_VOLUNTEER_ASSIGNMENT,
        target_url=reverse("volunteer_dashboard_tasks_ojt"),
    )
    if activity_name:
        notification_query = notification_query.filter(message__icontains=activity_name)
    notification_query.delete()


def _sync_activity_volunteer_assignments(activity, volunteer_ids, actor):
    if activity is None:
        return []

    normalized_ids = _parse_volunteer_ids(volunteer_ids)

    selected_user_ids = set(normalized_ids)
    existing_assignments = list(
        VolunteerActivityAssignment.objects.filter(activity=activity)
        .select_related("volunteer")
    )
    existing_by_volunteer = {assignment.volunteer_id: assignment for assignment in existing_assignments}

    valid_volunteers = list(
        User.objects.filter(
            id__in=selected_user_ids,
            is_active=True,
            userprofile__account_role=UserProfile.ROLE_VOLUNTEER,
        )
        .select_related("userprofile")
    )
    valid_by_id = {volunteer.id: volunteer for volunteer in valid_volunteers}

    removed_assignments = [
        assignment for assignment in existing_assignments if assignment.volunteer_id not in valid_by_id
    ]
    if removed_assignments:
        for assignment in removed_assignments:
            _clear_activity_assignment_notifications(assignment.volunteer, assignment.activity_name)
        VolunteerActivityAssignment.objects.filter(id__in=[assignment.id for assignment in removed_assignments]).delete()

    created_assignments = []
    for volunteer in valid_volunteers:
        assignment = existing_by_volunteer.get(volunteer.id)
        if assignment is None:
            assignment = VolunteerActivityAssignment.objects.create(
                activity=activity,
                volunteer=volunteer,
                activity_name=activity.title,
                activity_type=activity.category,
                scheduled_date=activity.date,
                scheduled_time=activity.start_time,
                location=activity.location,
                notes="",
                assigned_by=actor,
            )
            created_assignments.append(assignment)
            _create_in_app_notification(
                recipient=volunteer,
                actor=actor,
                notification_type=CommunityNotification.TYPE_VOLUNTEER_ASSIGNMENT,
                message=f"You have been assigned to {activity.title} on {activity.date.strftime('%b %d, %Y') }.",
                target_url=reverse("volunteer_dashboard_tasks_ojt"),
            )
            _send_volunteer_assignment_email(volunteer, activity.title, activity.date)
        else:
            changed = False
            if assignment.activity_name != activity.title:
                assignment.activity_name = activity.title
                changed = True
            if assignment.scheduled_date != activity.date:
                assignment.scheduled_date = activity.date
                changed = True
            if assignment.scheduled_time != activity.start_time:
                assignment.scheduled_time = activity.start_time
                changed = True
            if assignment.location != activity.location:
                assignment.location = activity.location
                changed = True
            if assignment.activity_type != activity.category:
                assignment.activity_type = activity.category
                changed = True
            if assignment.activity_id != activity.id:
                assignment.activity = activity
                changed = True
            if changed:
                assignment.save()

    activity.volunteer_count = len(valid_volunteers)
    activity.save(update_fields=["volunteer_count", "updated_at"])
    return created_assignments


def _build_beneficiary_options():
    latest_beneficiary_status = (
        RoleApplication.objects
        .filter(user=OuterRef("pk"), role=RoleApplication.ROLE_BENEFICIARY)
        .order_by("-created_at", "-id")
        .values("status")[:1]
    )
    beneficiaries = (
        User.objects
        .filter(is_active=True, userprofile__account_role=UserProfile.ROLE_BENEFICIARY)
        .annotate(latest_beneficiary_status=Subquery(latest_beneficiary_status))
        .filter(latest_beneficiary_status__in=[RoleApplication.STATUS_APPROVED, RoleApplication.STATUS_INACTIVE])
        .order_by("first_name", "last_name", "username")
    )
    return [
        {"id": int(beneficiary.id), "name": _display_name_for_user(beneficiary)}
        for beneficiary in beneficiaries
    ]


def _parse_beneficiary_ids(raw_values):
    values = raw_values if isinstance(raw_values, (list, tuple)) else [raw_values]
    parsed = []
    for value in values:
        for item in str(value or "").split(","):
            try:
                number = int(item.strip())
            except (TypeError, ValueError):
                continue
            if number > 0 and number not in parsed:
                parsed.append(number)
    return parsed


def _extract_activity_beneficiary_ids(post_data):
    values = list(post_data.getlist("beneficiary_ids[]")) + list(post_data.getlist("beneficiary_ids"))
    if not values:
        values = [post_data.get("beneficiary_ids", "")]
    return _parse_beneficiary_ids(values)


def _sync_activity_beneficiary_assignments(activity, beneficiary_ids, actor):
    normalized_ids = _parse_beneficiary_ids(beneficiary_ids)
    selected_ids = set(normalized_ids)
    existing = list(ActivityBeneficiaryAssignment.objects.filter(activity=activity))
    existing_ids = {assignment.beneficiary_id for assignment in existing}
    valid_ids = set(
        User.objects.filter(
            id__in=selected_ids,
            is_active=True,
            userprofile__account_role=UserProfile.ROLE_BENEFICIARY,
        ).filter(
            role_applications__role=RoleApplication.ROLE_BENEFICIARY,
            role_applications__status__in=[RoleApplication.STATUS_APPROVED, RoleApplication.STATUS_INACTIVE],
        ).values_list("id", flat=True)
    )
    ActivityBeneficiaryAssignment.objects.filter(
        activity=activity,
        beneficiary_id__in=existing_ids - valid_ids,
    ).delete()
    ActivityBeneficiaryAssignment.objects.bulk_create([
        ActivityBeneficiaryAssignment(activity=activity, beneficiary_id=beneficiary_id, assigned_by=actor)
        for beneficiary_id in valid_ids - existing_ids
    ])
    return sorted(valid_ids)


def _activity_audience_ids(activity):
    volunteer_ids = set(
        VolunteerActivityAssignment.objects.filter(activity=activity).values_list("volunteer_id", flat=True)
    )
    beneficiary_ids = set(
        ActivityBeneficiaryAssignment.objects.filter(activity=activity).values_list("beneficiary_id", flat=True)
    )
    selected_ids = volunteer_ids | beneficiary_ids
    if selected_ids:
        return selected_ids

    latest_volunteer_status = (
        RoleApplication.objects
        .filter(user=OuterRef("pk"), role=RoleApplication.ROLE_VOLUNTEER)
        .order_by("-created_at", "-id")
        .values("status")[:1]
    )
    latest_beneficiary_status = (
        RoleApplication.objects
        .filter(user=OuterRef("pk"), role=RoleApplication.ROLE_BENEFICIARY)
        .order_by("-created_at", "-id")
        .values("status")[:1]
    )
    general_audience = User.objects.filter(is_active=True).annotate(
        latest_volunteer_status=Subquery(latest_volunteer_status),
        latest_beneficiary_status=Subquery(latest_beneficiary_status),
    ).filter(
        Q(
            userprofile__account_role=UserProfile.ROLE_VOLUNTEER,
            latest_volunteer_status=RoleApplication.STATUS_APPROVED,
        ) | Q(
            userprofile__account_role=UserProfile.ROLE_BENEFICIARY,
            latest_beneficiary_status__in=[RoleApplication.STATUS_APPROVED, RoleApplication.STATUS_INACTIVE],
        )
    )
    return set(general_audience.values_list("id", flat=True))


def _sync_activity_announcement_notifications(activity, actor):
    message = f"New activity: {activity.title} on {activity.date.strftime('%b %d, %Y')}."
    notification_qs = CommunityNotification.objects.filter(
        notification_type=CommunityNotification.TYPE_ACTIVITY_ANNOUNCEMENT,
        message=message,
    )
    if activity.status != Activity.STATUS_ACTIVE:
        notification_qs.delete()
        return

    audience_ids = _activity_audience_ids(activity)
    notification_qs.exclude(recipient_id__in=audience_ids).delete()
    existing_ids = set(notification_qs.values_list("recipient_id", flat=True))
    message = f"New activity: {activity.title} on {activity.date.strftime('%b %d, %Y')}."
    for recipient_id in audience_ids - existing_ids:
        recipient = User.objects.filter(id=recipient_id).first()
        _create_in_app_notification(
            recipient=recipient,
            actor=actor,
            notification_type=CommunityNotification.TYPE_ACTIVITY_ANNOUNCEMENT,
            message=message,
            target_url=reverse("user_dashboard") + "#distribution-outreach",
        )


def _visible_activity_announcement_filter(user):
    if user.is_superuser:
        return Q()

    visible_activity = (
        Q(activity__isnull=True)
        | Q(activity__volunteer_assignments__volunteer=user)
        | Q(activity__beneficiary_assignments__beneficiary=user)
        | (
            Q(activity__volunteer_assignments__isnull=True)
            & Q(activity__beneficiary_assignments__isnull=True)
        )
    )
    return Q(post_type__in=["discussions", "tips"]) | (
        Q(post_type="announcements") & visible_activity
    )


def _visible_activity_filter(user):
    if user.is_superuser:
        return Q()

    return (
        Q(volunteer_assignments__volunteer=user)
        | Q(beneficiary_assignments__beneficiary=user)
        | (
            Q(volunteer_assignments__isnull=True)
            & Q(beneficiary_assignments__isnull=True)
        )
    )


def _get_user_role(user):
    if not user or not user.is_authenticated:
        return UserProfile.ROLE_REGULAR

    if user.is_superuser:
        return "admin"

    try:
        return user.userprofile.account_role or UserProfile.ROLE_REGULAR
    except UserProfile.DoesNotExist:
        return UserProfile.ROLE_REGULAR


def _is_chat_enabled_user(user):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    try:
        profile = user.userprofile
    except UserProfile.DoesNotExist:
        profile = None
    return bool(profile and profile.account_role == UserProfile.ROLE_VOLUNTEER)


def _chat_user_name(user):
    if not user:
        return "User"
    full_name = getattr(user, "get_full_name", lambda: "")()
    if full_name and full_name.strip():
        return full_name.strip()
    return (user.username or "User").strip() or "User"


def _chat_user_initials(user):
    name = _chat_user_name(user)
    initials = "".join(part[:1].upper() for part in name.split() if part)[:2]
    return initials or "U"


def _serialize_chat_message(message, current_user=None):
    sender_is_current = bool(current_user and message.sender_id == current_user.id)
    try:
        attachment = message.attachment
    except ObjectDoesNotExist:
        attachment = None
    attachment_name = getattr(attachment, "original_name", "") if attachment else ""
    attachment_mime_type = str(getattr(attachment, "mime_type", "") or "").lower() if attachment else ""
    attachment_extension = os.path.splitext(attachment_name)[1].lower() if attachment_name else ""
    is_image_attachment = attachment_mime_type.startswith("image/") or attachment_extension in {".jpg", ".jpeg", ".jfif", ".png", ".gif", ".webp", ".bmp", ".svg", ".heic", ".heif"}
    attachment_url = ""
    if attachment and attachment.file:
        try:
            attachment_url = attachment.file.url
        except (AttributeError, ValueError):
            attachment_url = ""
    return {
        "id": message.id,
        "sender_id": message.sender_id,
        "sender_name": _chat_user_name(message.sender),
        "sender_initials": _chat_user_initials(message.sender),
        "thread_user_id": message.thread_user_id,
        "message": message.message,
        "is_edited": bool(message.is_edited),
        "reply_to": ({
            "id": message.reply_to_id,
            "message": message.reply_to.message,
            "sender_name": _chat_user_name(message.reply_to.sender),
        } if message.reply_to_id and message.reply_to else None),
        "created_at": timezone.localtime(message.created_at).isoformat(),
        "is_read": bool(message.is_read),
        "is_self": sender_is_current,
        "attachment": ({
            "name": attachment.original_name,
            "mime_type": attachment.mime_type,
            "size": attachment.size_bytes,
            "url": attachment_url,
            "is_image": is_image_attachment,
        } if attachment else None),
    }


def _chat_mark_thread_read_for_user(user, thread_user):
    if not user or not thread_user or not _is_chat_enabled_user(user):
        return 0
    queryset = VolunteerAdminMessage.objects.filter(thread_user=thread_user).exclude(sender=user)
    if user.is_superuser:
        return queryset.filter(is_read=False).update(is_read=True)
    return queryset.filter(is_read=False).update(is_read=True)


def _get_chat_admin_conversation_threads(request):
    if not request.user.is_superuser:
        return []
    volunteers = User.objects.filter(
        userprofile__account_role=UserProfile.ROLE_VOLUNTEER,
        is_active=True,
    ).distinct().order_by("username")
    threads = []
    for volunteer in volunteers:
        thread_messages = list(
            VolunteerAdminMessage.objects
            .filter(thread_user=volunteer)
            .select_related("sender", "thread_user")
            .order_by("created_at")
        )
        last_message = thread_messages[-1] if thread_messages else None
        unread_count = (
            VolunteerAdminMessage.objects
            .filter(thread_user=volunteer, is_read=False)
            .exclude(sender=request.user)
            .count()
        )
        threads.append({
            "user_id": volunteer.id,
            "name": _chat_user_name(volunteer),
            "initials": _chat_user_initials(volunteer),
            "preview": (last_message.message[:120] if last_message else ""),
            "last_message_time": timezone.localtime(last_message.created_at).isoformat() if last_message else None,
            "unread_count": unread_count,
            "has_conversation": bool(thread_messages),
            "avatar_url": getattr(getattr(volunteer, "userprofile", None), "avatar", None).url if getattr(getattr(volunteer, "userprofile", None), "avatar", None) else "",
        })
    threads.sort(key=lambda item: item["last_message_time"] or "", reverse=True)
    return threads


def _get_latest_role_applications(user):
    applications = list(
        RoleApplication.objects.filter(user=user).order_by("-created_at", "-id")
    )
    latest_by_role = {}
    for application in applications:
        latest_by_role.setdefault(application.role, application)
    return latest_by_role


def _is_active_beneficiary(user):
    if not user or not user.is_authenticated:
        return False
    profile = _get_or_create_user_profile(user)
    if profile.account_role != UserProfile.ROLE_BENEFICIARY:
        return False
    latest = _get_latest_role_applications(user).get(RoleApplication.ROLE_BENEFICIARY)
    return bool(latest and latest.status in {RoleApplication.STATUS_APPROVED, RoleApplication.STATUS_INACTIVE})


def _is_active_volunteer(user):
    if not user or not user.is_authenticated:
        return False
    profile = _get_or_create_user_profile(user)
    if profile.account_role != UserProfile.ROLE_VOLUNTEER:
        return False
    latest = _get_latest_role_applications(user).get(RoleApplication.ROLE_VOLUNTEER)
    return bool(latest and latest.status == RoleApplication.STATUS_APPROVED)


def _has_dashboard_access(user):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    profile = _get_or_create_user_profile(user)
    if profile.account_role == UserProfile.ROLE_VOLUNTEER:
        return True
    if profile.account_role != UserProfile.ROLE_BENEFICIARY:
        return False
    latest = _get_latest_role_applications(user).get(RoleApplication.ROLE_BENEFICIARY)
    return bool(latest and latest.status in {RoleApplication.STATUS_APPROVED, RoleApplication.STATUS_INACTIVE})


def _serialize_pending_beneficiary_application(application):
    profile = UserProfile.objects.filter(user_id=application.user_id).first() if application.user_id else None
    email, phone = _split_contact_details(application.contact_details)
    location = (profile.address_line if profile else "") or application.supporting_information or "Not provided"
    return {
        "id": int(application.id),
        "name": application.full_name,
        "contactDetails": application.contact_details,
        "email": email,
        "phone": phone,
        "location": str(location).strip()[:160],
        "reasonForAssistance": application.reason_for_assistance or "",
        "supportingInformation": application.supporting_information or "",
        "submittedAt": timezone.localtime(application.created_at).strftime("%Y-%m-%d"),
    }


@login_required
@require_GET
def chat_widget_state(request):
    if not _is_chat_enabled_user(request.user):
        return JsonResponse({"enabled": False, "unread_count": 0})

    if request.user.is_superuser:
        unread_count = VolunteerAdminMessage.objects.filter(
            thread_user__userprofile__account_role=UserProfile.ROLE_VOLUNTEER,
            is_read=False,
        ).exclude(sender=request.user).count()
    else:
        unread_count = VolunteerAdminMessage.objects.filter(
            thread_user=request.user,
            is_read=False,
        ).exclude(sender=request.user).count()

    return JsonResponse({
        "enabled": True,
        "unread_count": unread_count,
        "role": "admin" if request.user.is_superuser else "volunteer",
        "user_id": request.user.id,
    })


@login_required
@require_GET
def chat_conversations(request):
    if not request.user.is_superuser:
        return JsonResponse({"error": "Only admins can view the full conversation inbox."}, status=403)

    threads = _get_chat_admin_conversation_threads(request)
    return JsonResponse({"threads": threads})


@login_required
@require_GET
def chat_messages(request, thread_user_id):
    if not _is_chat_enabled_user(request.user):
        return JsonResponse({"error": "Volunteer/admin chat is only available for volunteers and admins."}, status=403)

    thread_user = get_object_or_404(User, id=thread_user_id)
    if request.user.is_superuser:
        allowable = bool(thread_user.userprofile.account_role == UserProfile.ROLE_VOLUNTEER) if hasattr(thread_user, "userprofile") else False
        if not allowable:
            return JsonResponse({"error": "Only volunteer conversations are available in the admin inbox."}, status=400)
    elif thread_user_id != request.user.id:
        return JsonResponse({"error": "You can only view your own conversation thread."}, status=403)

    messages = VolunteerAdminMessage.objects.filter(thread_user=thread_user).select_related("sender", "thread_user").prefetch_related("attachment").order_by("created_at")
    _chat_mark_thread_read_for_user(request.user, thread_user)
    return JsonResponse({
        "thread_user_id": thread_user.id,
        "thread_user_name": _chat_user_name(thread_user),
        "messages": [_serialize_chat_message(message, request.user) for message in messages],
    })


@login_required
@require_POST
def chat_send_message(request):
    if not _is_chat_enabled_user(request.user):
        return JsonResponse({"error": "Volunteer/admin chat is only available for volunteers and admins."}, status=403)

    content_type = (request.content_type or "").lower()
    if content_type.startswith("application/json"):
        try:
            data = json.loads(request.body.decode("utf-8") or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError):
            data = {}
    elif content_type.startswith("multipart/form-data") or content_type.startswith("application/x-www-form-urlencoded"):
        data = request.POST
    else:
        data = request.POST

    thread_user_id = data.get("thread_user_id")
    message_text = str(data.get("message") or "").strip()
    attachment_file = request.FILES.get("attachment")
    if attachment_file and attachment_file.size > 5 * 1024 * 1024:
        return JsonResponse({"error": "Attachments must be 5 MB or smaller."}, status=400)
    if not thread_user_id or (not message_text and not attachment_file):
        return JsonResponse({"error": "A thread and message or attachment are required."}, status=400)

    try:
        thread_user_id = int(thread_user_id)
    except (TypeError, ValueError):
        return JsonResponse({"error": "Invalid conversation target."}, status=400)

    thread_user = get_object_or_404(User, id=thread_user_id)
    if request.user.is_superuser:
        profile = getattr(thread_user, "userprofile", None)
        if not profile or profile.account_role != UserProfile.ROLE_VOLUNTEER:
            return JsonResponse({"error": "Admins can only send messages to volunteers."}, status=400)
    elif thread_user_id != request.user.id:
        return JsonResponse({"error": "Volunteers can only send messages in their own thread."}, status=403)

    reply_to_id = data.get("reply_to_id") or None
    if reply_to_id:
        reply_to = get_object_or_404(VolunteerAdminMessage, id=reply_to_id, thread_user=thread_user)
    else:
        reply_to = None

    message = VolunteerAdminMessage.objects.create(
        sender=request.user,
        thread_user=thread_user,
        message=message_text,
        reply_to=reply_to,
        is_read=False,
    )
    if attachment_file:
        VolunteerAdminMessageAttachment.objects.create(message=message, file=attachment_file, original_name=attachment_file.name)
        message = VolunteerAdminMessage.objects.select_related("sender", "thread_user").prefetch_related("attachment").get(pk=message.pk)
    return JsonResponse({
        "ok": True,
        "message": _serialize_chat_message(message, request.user),
    })


@login_required
@require_http_methods(["PATCH", "DELETE"])
def chat_message_manage(request, message_id):
    if not _is_chat_enabled_user(request.user):
        return JsonResponse({"error": "Volunteer/admin chat is only available for volunteers and admins."}, status=403)

    message = get_object_or_404(VolunteerAdminMessage.objects.select_related("sender", "thread_user"), id=message_id)
    can_manage_thread = request.user.is_superuser or message.thread_user_id == request.user.id
    if not can_manage_thread:
        return JsonResponse({"error": "You can only manage messages in your own conversation."}, status=403)

    if request.method == "DELETE":
        message.delete()
        return JsonResponse({"ok": True})

    if message.sender_id != request.user.id:
        return JsonResponse({"error": "You can only edit your own messages."}, status=403)

    try:
        data = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        data = {}
    message_text = str(data.get("message") or "").strip()
    if not message_text:
        return JsonResponse({"error": "Message text is required."}, status=400)
    message.message = message_text
    message.is_edited = True
    message.save(update_fields=["message", "is_edited"])
    return JsonResponse({"ok": True, "message": _serialize_chat_message(message, request.user)})


def _build_beneficiaries_payload():
    approved_apps = list(
        RoleApplication.objects
        .filter(role=RoleApplication.ROLE_BENEFICIARY, status__in=[RoleApplication.STATUS_APPROVED, RoleApplication.STATUS_INACTIVE])
        .select_related("user", "user__userprofile")
        .order_by("-updated_at", "-created_at", "-id")
    )

    latest_assistance_by_application = {}
    assistance_records = list(
        BeneficiaryAssistanceRecord.objects
        .select_related("beneficiary", "assigned_volunteer")
        .order_by("beneficiary_id", "-assistance_date", "-created_at", "-id")
    )
    for record in assistance_records:
        latest_assistance_by_application.setdefault(record.beneficiary_id, record)

    seen_beneficiaries = set()
    beneficiaries_data = []
    for app in approved_apps:
        user = app.user
        profile = getattr(user, "userprofile", None) if user else None
        duplicate_key = f"user:{user.id}" if user else f"app:{app.full_name.lower().strip()}|{app.contact_details.lower().strip()}"
        if duplicate_key in seen_beneficiaries:
            continue
        seen_beneficiaries.add(duplicate_key)

        reviewed_at = timezone.localtime(app.reviewed_at) if app.reviewed_at else None
        approved_label = reviewed_at.strftime("%Y-%m-%d") if reviewed_at else "N/A"
        latest_assistance = latest_assistance_by_application.get(app.id)
        last_assistance_label = ""
        if latest_assistance and latest_assistance.assistance_date:
            last_assistance_label = latest_assistance.assistance_date.strftime("%Y-%m-%d")
        elif reviewed_at:
            last_assistance_label = approved_label if approved_label != "N/A" else ""

        contact_email, contact_phone = _split_contact_details(app.contact_details)
        display_name = _display_name_for_user(user) if user else app.full_name
        address_line = (profile.address_line if profile else "") or (app.supporting_information or "")
        email = (user.email if user else "") or contact_email
        phone = (profile.phone if profile else "") or contact_phone
        contact_details = " / ".join([part for part in [email, phone] if part])

        beneficiaries_data.append({
            "id": int(user.id) if user else int(app.id),
            "applicationId": int(app.id),
            "userId": int(user.id) if user else None,
            "name": display_name,
            "email": email,
            "phone": phone,
            "contactDetails": contact_details or app.contact_details or "",
            "addressLine": address_line,
            "category": "Beneficiary",
            "location": address_line[:100] if address_line else "To be determined",
            "program": "Community Support Program",
            "status": "Inactive" if app.status == RoleApplication.STATUS_INACTIVE else "Active",
            "registeredAt": approved_label if approved_label != "N/A" else "",
            "notes": app.admin_notes or app.reason_for_assistance or "",
            "lastAssistanceDate": last_assistance_label,
            "personalInfo": [
                "Contact: " + (app.contact_details[:100] if app.contact_details else "N/A"),
                "Approved: " + approved_label,
            ],
            "enrollment": ["Approved on: " + approved_label],
            "requests": [],
            "documents": [],
        })

    return beneficiaries_data


def _build_volunteer_options():
    latest_volunteer_status = (
        RoleApplication.objects
        .filter(user=OuterRef("pk"), role=RoleApplication.ROLE_VOLUNTEER)
        .order_by("-created_at", "-id")
        .values("status")[:1]
    )
    volunteers = (
        User.objects
        .filter(is_active=True, userprofile__account_role=UserProfile.ROLE_VOLUNTEER)
        .annotate(latest_volunteer_status=Subquery(latest_volunteer_status))
        .filter(latest_volunteer_status=RoleApplication.STATUS_APPROVED)
        .select_related("userprofile")
        .order_by("first_name", "last_name", "username")
    )

    return [
        {
            "id": int(volunteer.id),
            "name": _display_name_for_user(volunteer),
            "username": volunteer.username,
            "email": volunteer.email or "",
        }
        for volunteer in volunteers
    ]


def _build_admin_certificate_payload():
    return [
        {
            "id": certificate.id,
            "volunteer_id": certificate.volunteer_id,
            "volunteer_name": _display_name_for_user(certificate.volunteer),
            "recipient_name": certificate.recipient_name,
            "issued_date": timezone.localtime(certificate.issued_at).strftime("%B %d, %Y"),
            "preview_url": reverse("volunteer_certificate_download", args=[certificate.id]),
        }
        for certificate in VolunteerCertificate.objects.select_related("volunteer").all()
    ]


def _build_activity_volunteer_map(activities_qs):
    activity_ids = list(activities_qs.values_list("id", flat=True))
    if not activity_ids:
        return {}

    assignments = (
        VolunteerActivityAssignment.objects
        .filter(activity_id__in=activity_ids)
        .values_list("activity_id", "volunteer_id")
        .order_by("activity_id", "volunteer_id")
    )

    activity_map = {}
    for activity_id, volunteer_id in assignments:
        key = str(activity_id)
        activity_map.setdefault(key, [])
        if volunteer_id not in activity_map[key]:
            activity_map[key].append(int(volunteer_id))

    return {
        str(activity_id): activity_map.get(str(activity_id), [])
        for activity_id in activity_ids
    }


def _build_volunteers_payload():
    volunteer_users = (
        User.objects
        .select_related("userprofile")
        .filter(userprofile__account_role=UserProfile.ROLE_VOLUNTEER)
        .order_by("first_name", "last_name", "username")
    )

    volunteer_apps = (
        RoleApplication.objects
        .filter(role=RoleApplication.ROLE_VOLUNTEER, user__isnull=False)
        .select_related("user")
        .order_by("-created_at", "-id")
    )
    latest_app_by_user = {}
    for app in volunteer_apps:
        if app.user_id not in latest_app_by_user:
            latest_app_by_user[app.user_id] = app

    volunteer_activity_records = list(
        BeneficiaryAssistanceRecord.objects
        .select_related("beneficiary", "assigned_volunteer")
        .order_by("-assistance_date", "-created_at", "-id")
    )
    activity_history_by_user = {}
    for record in volunteer_activity_records:
        if not record.assigned_volunteer_id:
            continue
        activity_history_by_user.setdefault(record.assigned_volunteer_id, []).append(_serialize_volunteer_activity_record(record))

    participated_events_by_user = {}
    volunteer_assignments = (
        VolunteerActivityAssignment.objects
        .filter(volunteer__in=volunteer_users)
        .order_by("-scheduled_date", "-scheduled_time", "-id")
    )
    for assignment in volunteer_assignments:
        participated_events_by_user.setdefault(assignment.volunteer_id, []).append({
            "name": assignment.activity_name,
            "date": assignment.scheduled_date.isoformat(),
            "location": assignment.location or "TBA",
            "status": assignment.current_status_label,
        })

    seen_volunteers = set()

    today = timezone.localdate()
    ojt_schedules_by_user = {}
    for schedule in VolunteerOjtSchedule.objects.filter(
        volunteer__in=volunteer_users,
        effective_from__lte=today,
    ).filter(
        Q(effective_until__isnull=True) | Q(effective_until__gte=today),
    ).order_by("volunteer_id", "-effective_from", "-id"):
        ojt_schedules_by_user.setdefault(schedule.volunteer_id, schedule)
    for schedule in VolunteerOjtSchedule.objects.filter(
        volunteer__in=volunteer_users,
        effective_from__gt=today,
    ).order_by("volunteer_id", "effective_from", "id"):
        ojt_schedules_by_user.setdefault(schedule.volunteer_id, schedule)
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    assigned_volunteer_ids = set(
        BeneficiaryAssistanceRecord.objects
        .filter(
            assistance_date__range=(week_start, week_end),
            assigned_volunteer_id__isnull=False,
        )
        .values_list("assigned_volunteer_id", flat=True)
    )

    volunteers_data = []
    for volunteer in volunteer_users:
        profile = getattr(volunteer, "userprofile", None)
        app = latest_app_by_user.get(volunteer.id)
        activity_history = activity_history_by_user.get(volunteer.id, [])
        participated_events = participated_events_by_user.get(volunteer.id, [])
        duplicate_key = (volunteer.email or volunteer.username or str(volunteer.id)).strip().lower()
        if duplicate_key in seen_volunteers:
            continue
        seen_volunteers.add(duplicate_key)

        status = "Active"
        if app:
            if app.status == RoleApplication.STATUS_PENDING:
                status = "Pending"
            elif app.status in {RoleApplication.STATUS_INACTIVE, RoleApplication.STATUS_REJECTED}:
                status = "Inactive"

        joined_at = app.created_at if app else volunteer.date_joined
        joined_label = timezone.localtime(joined_at).strftime("%Y-%m-%d") if joined_at else ""
        contact_email, contact_phone = _split_contact_details(app.contact_details if app else "")
        display_name = _display_name_for_user(volunteer)
        email = volunteer.email or contact_email
        phone = (profile.phone if profile else "") or contact_phone
        contact_details = " / ".join([part for part in [email, phone] if part])

        volunteers_data.append({
            "id": int(volunteer.id),
            "name": display_name,
            "username": volunteer.username,
            "email": email,
            "contact": phone,
            "contactDetails": contact_details,
            "program": (profile.volunteer_role if profile else "") or "Volunteer",
            "skills": (app.skills if app else "") or ((profile.volunteer_role if profile else "") or ""),
            "areasOfInterest": (app.areas_of_interest if app else "") or ((profile.assigned_chapter_area if profile else "") or ""),
            "availability": (app.availability if app else "") or "N/A",
            "hoursRendered": 0,
            "ojtHours": float(profile.ojt_hours or 0) if profile else 0,
            "requiredOjtHours": float(profile.required_ojt_hours or 80) if profile else 80,
            "ojtSupervisor": (profile.ojt_supervisor or "") if profile else "",
            "ojtProgram": (profile.ojt_program or "") if profile else "",
            "ojtNextCheckIn": profile.ojt_next_check_in.isoformat() if profile and profile.ojt_next_check_in else "",
            "ojtSchedule": {
                "effectiveFrom": ojt_schedules_by_user[volunteer.id].effective_from.isoformat() if ojt_schedules_by_user.get(volunteer.id) else "",
                "effectiveUntil": ojt_schedules_by_user[volunteer.id].effective_until.isoformat() if ojt_schedules_by_user.get(volunteer.id) and ojt_schedules_by_user[volunteer.id].effective_until else "",
                "weekdays": ojt_schedules_by_user[volunteer.id].weekdays if ojt_schedules_by_user.get(volunteer.id) else [],
                "dailyTimes": ojt_schedules_by_user[volunteer.id].daily_times if ojt_schedules_by_user.get(volunteer.id) else {},
            },
            "scheduleDefaultDate": today.isoformat(),
            "status": status,
            "participationRate": 0,
            "joinedDate": joined_label,
            "applicationId": int(app.id) if app else None,
            "activityHistory": activity_history,
            "activityCount": len(activity_history),
            "participatedEvents": participated_events,
            "lastActivityDate": activity_history[0]["date"] if activity_history else "",
            "assignedThisWeek": volunteer.id in assigned_volunteer_ids,
        })

    return volunteers_data


def _serialize_volunteer_activity_record(record):
    payload = _serialize_assistance_record(record)
    payload["activityLabel"] = f"{payload['beneficiaryName']} received {payload['quantity']} of {payload['aidType']}"
    return payload


def _serialize_assistance_record(record, include_feedback=True):
    volunteer_name = _display_name_for_user(record.assigned_volunteer) if record.assigned_volunteer_id else "Unassigned"
    beneficiary_name = record.beneficiary.full_name if record.beneficiary_id else "Unknown"
    feedback = getattr(record, "feedback", None) if include_feedback else None
    feedback_payload = None
    if feedback:
        feedback_payload = {
            "rating": int(feedback.rating or 0),
            "comment": (feedback.comment or "").strip(),
            "submittedBy": _display_name_for_user(feedback.user) if feedback.user_id else "Beneficiary",
            "submittedAt": feedback.created_at.isoformat() if feedback.created_at else None,
            "ratingLabel": "★" * int(feedback.rating or 0) + "☆" * max(0, 5 - int(feedback.rating or 0)),
        }

    return {
        "id": int(record.id),
        "beneficiaryApplicationId": int(record.beneficiary_id),
        "beneficiaryName": beneficiary_name,
        "aidType": record.aid_type,
        "quantity": record.quantity_or_amount,
        "date": record.assistance_date.strftime("%Y-%m-%d"),
        "volunteer": volunteer_name,
        "notes": record.notes or "",
        "status": "Completed",
        "feedback": feedback_payload,
        "hasFeedback": bool(feedback),
    }


def _get_volunteer_payload_for_user(user_id):
    volunteers_data = _build_volunteers_payload()
    return next((item for item in volunteers_data if item.get("id") == int(user_id)), None)


def _build_assistance_tracking_payload():
    feedback_table_exists = "webapp_beneficiaryassistancefeedback" in connection.introspection.table_names()
    records = (
        BeneficiaryAssistanceRecord.objects
        .select_related("beneficiary", "assigned_volunteer")
        .order_by("-assistance_date", "-created_at", "-id")
    )
    if feedback_table_exists:
        records = records.prefetch_related("feedback")
    return [_serialize_assistance_record(record, include_feedback=feedback_table_exists) for record in records]


def _build_assistance_feedbacks_payload():
    feedbacks = []
    assistance_feedbacks = BeneficiaryAssistanceFeedback.objects.select_related(
        "assistance_record", "assistance_record__beneficiary", "user"
    ).order_by("-created_at", "-id")
    for feedback in assistance_feedbacks:
        record = feedback.assistance_record
        feedbacks.append({
            "id": f"assistance-{feedback.id}",
            "source": "Assistance",
            "beneficiaryName": record.beneficiary.full_name,
            "subject": f"{record.quantity_or_amount} of {record.aid_type}",
            "date": record.assistance_date.strftime("%Y-%m-%d"),
            "rating": int(feedback.rating or 0),
            "comment": (feedback.comment or "").strip(),
            "submittedBy": _display_name_for_user(feedback.user),
            "submittedAt": feedback.created_at.isoformat() if feedback.created_at else None,
            "ratingLabel": "★" * int(feedback.rating or 0) + "☆" * max(0, 5 - int(feedback.rating or 0)),
            "assistanceId": int(record.id),
        })

    activity_feedbacks = BeneficiaryActivityFeedback.objects.select_related(
        "activity", "beneficiary", "user"
    ).order_by("-created_at", "-id")
    for feedback in activity_feedbacks:
        feedbacks.append({
            "id": f"activity-{feedback.id}",
            "source": "Activity",
            "beneficiaryName": feedback.beneficiary.full_name,
            "subject": feedback.activity.title,
            "date": feedback.activity.date.strftime("%Y-%m-%d"),
            "rating": int(feedback.rating or 0),
            "comment": (feedback.comment or "").strip(),
            "submittedBy": _display_name_for_user(feedback.user),
            "submittedAt": feedback.created_at.isoformat() if feedback.created_at else None,
            "ratingLabel": "★" * int(feedback.rating or 0) + "☆" * max(0, 5 - int(feedback.rating or 0)),
            "assistanceId": None,
        })
    return sorted(feedbacks, key=lambda item: item.get("submittedAt") or "", reverse=True)


def _build_beneficiaries_dashboard_payload():
    return {
        "beneficiaries": _build_beneficiaries_payload(),
        "pending_applications": [
            _serialize_pending_beneficiary_application(application)
            for application in _get_pending_role_applications(RoleApplication.ROLE_BENEFICIARY)
        ],
        "assistance_tracking": _build_assistance_tracking_payload(),
        "assistance_feedbacks": _build_assistance_feedbacks_payload(),
        "volunteer_options": _build_volunteer_options(),
    }


def _build_volunteers_dashboard_payload():
    _auto_close_expired_duty_sessions()
    monitor_records = VolunteerAttendanceRecord.objects.select_related("volunteer", "assignment")

    def monitor_payload(attendance):
        payload = _serialize_volunteer_attendance(attendance)
        payload.update({
            "volunteer_name": _display_name_for_user(attendance.volunteer),
            "volunteer_initials": _initials_for_name(_display_name_for_user(attendance.volunteer)),
            "activity_name": attendance.assignment.activity_name if attendance.assignment_id else "OJT duty day",
            "location": attendance.assignment.location or "TBA" if attendance.assignment_id else "OJT duty day",
        })
        return payload

    active_assignments = list(
        VolunteerActivityAssignment.objects.filter(
            status__in=[
                VolunteerActivityAssignment.STATUS_TIME_IN,
                VolunteerActivityAssignment.STATUS_IN_PROGRESS,
            ],
        ).select_related("volunteer").order_by("attendance_started_at", "id")
    )
    active_duty_records = list(
        monitor_records.filter(
            status=VolunteerAttendanceRecord.STATUS_ACTIVE,
            assignment__isnull=True,
        ).order_by("time_in", "id")
    )
    awaiting_records = list(
        monitor_records.filter(status=VolunteerAttendanceRecord.STATUS_PENDING)
        .order_by("time_out", "id")
    )
    completed_records = list(
        monitor_records.filter(status=VolunteerAttendanceRecord.STATUS_CONFIRMED)
        .order_by("-reviewed_at", "-id")[:5]
    )

    return {
        "volunteers": _build_volunteers_payload(),
        "pending_applications": [
            _serialize_pending_volunteer_application(application)
            for application in _get_pending_role_applications(RoleApplication.ROLE_VOLUNTEER)
        ],
        "pending_attendance": [
            {
                **_serialize_volunteer_attendance(attendance),
                "volunteer_name": _display_name_for_user(attendance.volunteer),
                "activity_name": attendance.assignment.activity_name if attendance.assignment_id else "OJT duty day",
                "scheduled_date": attendance.assignment.scheduled_date.isoformat() if attendance.assignment_id else attendance.duty_date.isoformat(),
            }
            for attendance in VolunteerAttendanceRecord.objects
            .filter(status=VolunteerAttendanceRecord.STATUS_PENDING)
            .select_related("volunteer", "assignment")
        ],
        "pending_beneficiary_attendance": [
            {
                **_serialize_beneficiary_activity_attendance(attendance),
                "beneficiary_name": _display_name_for_user(attendance.beneficiary),
                "volunteer_name": _display_name_for_user(attendance.volunteer) if attendance.volunteer else "Unassigned volunteer",
                "activity_name": attendance.activity.title,
                "scheduled_date": attendance.activity.date.isoformat(),
            }
            for attendance in BeneficiaryActivityAttendance.objects
            .filter(status=BeneficiaryActivityAttendance.STATUS_PENDING, confirmed_at__isnull=False)
            .select_related("activity", "beneficiary", "volunteer")
        ],
        "attendance_monitor": {
            "in_progress": [
                {
                    "id": int(assignment.id),
                    "assignment_id": int(assignment.id),
                    "attendance_id": None,
                    "volunteer_id": int(assignment.volunteer_id),
                    "volunteer_name": _display_name_for_user(assignment.volunteer),
                    "volunteer_initials": _initials_for_name(_display_name_for_user(assignment.volunteer)),
                    "activity_name": assignment.activity_name,
                    "location": assignment.location or "TBA",
                    "time_in": assignment.attendance_started_at.isoformat() if assignment.attendance_started_at else "",
                    "status": assignment.status,
                }
                for assignment in active_assignments
            ] + [
                {
                    "id": f"duty-{int(attendance.id)}",
                    "assignment_id": None,
                    "attendance_id": int(attendance.id),
                    "volunteer_id": int(attendance.volunteer_id),
                    "volunteer_name": _display_name_for_user(attendance.volunteer),
                    "volunteer_initials": _initials_for_name(_display_name_for_user(attendance.volunteer)),
                    "activity_name": "OJT duty day",
                    "location": "OJT duty day",
                    "time_in": attendance.time_in.isoformat() if attendance.time_in else "",
                    "status": attendance.status,
                }
                for attendance in active_duty_records
            ],
            "awaiting_confirmation": [monitor_payload(record) for record in awaiting_records],
            "recently_completed": [monitor_payload(record) for record in completed_records],
        },
    }


def _serialize_pending_volunteer_application(application):
    return {
        "id": int(application.id),
        "name": application.full_name,
        "contactDetails": application.contact_details,
        "skills": application.skills or "",
        "availability": application.availability or "",
        "areasOfInterest": application.areas_of_interest or "",
        "submittedAt": timezone.localtime(application.created_at).strftime("%Y-%m-%d"),
    }


def _get_pending_role_applications(role):
    return list(
        RoleApplication.objects.filter(role=role, status=RoleApplication.STATUS_PENDING)
        .order_by("-created_at", "-id")
    )


def _serialize_pending_role_application(application):
    return {
        "id": int(application.id),
        "role": application.role,
        "name": application.full_name,
        "submittedAt": timezone.localtime(application.created_at).strftime("%Y-%m-%d"),
    }


def _notify_admins_about_role_application(application):
    admin_users = User.objects.filter(is_superuser=True, is_active=True)
    if not admin_users.exists():
        return

    if application.role == RoleApplication.ROLE_BENEFICIARY:
        role_label = "beneficiary"
        target_url = reverse("beneficiaries")
    else:
        role_label = "volunteer"
        target_url = reverse("volunteers")

    message = f"New {role_label} application from {application.full_name}."

    for admin_user in admin_users:
        actor = application.user if getattr(application, "user_id", None) else admin_users.exclude(id=admin_user.id).first()
        if actor is None:
            continue
        if admin_user.id == getattr(actor, "id", None):
            continue

        _create_in_app_notification(
            recipient=admin_user,
            actor=actor,
            notification_type=CommunityNotification.TYPE_ROLE_APPLICATION,
            message=message,
            target_url=target_url,
        )
        _send_admin_application_email(admin_user, application)


def _review_role_application(application, *, status, reviewer, admin_notes=""):
    application.status = status
    application.reviewed_at = timezone.now()
    application.reviewed_by = reviewer
    application.admin_notes = admin_notes
    application.save(update_fields=["status", "reviewed_at", "reviewed_by", "admin_notes", "updated_at"])

    if status == RoleApplication.STATUS_APPROVED and application.user_id:
        profile = _get_or_create_user_profile(application.user)
        profile.account_role = application.role
        profile.save(update_fields=["account_role", "updated_at"])

    if status in {RoleApplication.STATUS_APPROVED, RoleApplication.STATUS_REJECTED} and application.user_id:
        if application.role == RoleApplication.ROLE_BENEFICIARY:
            decision_type = CommunityNotification.TYPE_BENEFICIARY_APPLICATION_DECISION
        else:
            decision_type = CommunityNotification.TYPE_VOLUNTEER_APPLICATION_DECISION
        decision_label = "approved" if status == RoleApplication.STATUS_APPROVED else "rejected"
        _create_in_app_notification(
            recipient=application.user,
            actor=reviewer,
            notification_type=decision_type,
            message=f"Your {application.role} application was {decision_label}.",
            target_url=reverse("user_dashboard") if application.role == RoleApplication.ROLE_BENEFICIARY else reverse("volunteer_dashboard"),
        )
        _send_application_decision_email(application, status)


def _review_role_application_response(application, status):
    dashboard_name = "user_dashboard" if application.role == RoleApplication.ROLE_BENEFICIARY else "volunteer_dashboard"
    return JsonResponse({
        "message": f"Application marked as {status}.",
        "applicationId": int(application.id),
        "role": application.role,
        "status": status,
        "redirectUrl": reverse(dashboard_name),
    })


def _initials_for_name(name):
    initials = "".join([part[:1].upper() for part in str(name or "").split() if part])[:2]
    return initials or "U"


def _serialize_profile_payload(user, profile):
    display_name = _display_name_for_user(user)
    return {
        "user": {
            "first_name": user.first_name or "",
            "last_name": user.last_name or "",
            "email": user.email or "",
            "display_name": display_name,
            "initials": _initials_for_name(display_name),
        },
        "profile": {
            "phone": profile.phone or "",
            "birthdate": profile.birthdate.isoformat() if profile.birthdate else "",
            "civil_status": profile.civil_status or "",
            "address_line": profile.address_line or "",
            "barangay": profile.barangay or "",
            "city_municipality": profile.city_municipality or "",
            "emergency_contact_name": profile.emergency_contact_name or "",
            "emergency_contact_relationship": profile.emergency_contact_relationship or "",
            "emergency_contact_phone": profile.emergency_contact_phone or "",
            "volunteer_role": profile.volunteer_role or "",
            "assigned_chapter_area": profile.assigned_chapter_area or "",
            "avatar_url": profile.avatar.url if profile.avatar else "",
        },
    }


def _format_file_size(size_bytes):
    size = float(size_bytes or 0)
    units = ["B", "KB", "MB", "GB"]
    unit_index = 0

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    rounded = round(size) if size >= 10 or unit_index == 0 else round(size, 1)
    return f"{rounded} {units[unit_index]}"


def _attachment_icon_name(file_name, mime_type):
    file_name = str(file_name or "")
    mime_type = str(mime_type or "").lower()
    extension = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""

    if extension == "pdf" or mime_type == "application/pdf":
        return "file-text"
    if extension in {"doc", "docx", "txt", "rtf", "md"}:
        return "file-text"
    if extension in {"xls", "xlsx", "csv"}:
        return "file-spreadsheet"
    if extension in {"ppt", "pptx", "key"}:
        return "presentation"
    if extension in {"zip", "rar", "7z"}:
        return "archive"

    return "file"


def _attachment_is_image(attachment):
    mime_type = str(getattr(attachment, "mime_type", "") or "").lower()
    if mime_type.startswith("image/"):
        return True

    name = getattr(attachment.file, "name", "") or getattr(attachment, "original_name", "") or ""
    extension = Path(name).suffix.lower().lstrip(".")
    return extension in {"png", "jpg", "jpeg", "jfif", "gif", "webp", "bmp", "svg", "heic", "heif", "avif"}


def _serialize_community_attachment(attachment):
    file_name = attachment.original_name or Path(getattr(attachment.file, "name", "") or "").name or "Attachment"
    file_url = attachment.file.url if attachment.file else ""
    is_image = _attachment_is_image(attachment)

    payload = {
        "id": str(attachment.id),
        "name": file_name,
        "url": file_url,
        "previewUrl": file_url if is_image else "",
        "src": file_url if is_image else "",
        "isImage": is_image,
        "sizeLabel": _format_file_size(attachment.size_bytes),
        "icon": _attachment_icon_name(file_name, attachment.mime_type),
    }

    if is_image:
        payload["alt"] = file_name

    return payload


def _avatar_url_for_user(user):
    try:
        return user.userprofile.avatar.url if user.userprofile.avatar else ""
    except UserProfile.DoesNotExist:
        return ""


def _serialize_community_comment_payload(comment, like_total=0, liked=False, viewer=None):
    author_name = _display_name_for_user(comment.user)

    return {
        "id": str(comment.id),
        "author": author_name,
        "canManage": bool(viewer and viewer.is_authenticated and (viewer.is_staff or comment.user_id == viewer.id)),
        "avatar": _initials_for_name(author_name),
        "avatarImage": _avatar_url_for_user(comment.user),
        "likes": max(0, int(like_total or 0)),
        "liked": bool(liked),
        "time": timezone.localtime(comment.created_at).strftime("%b %d, %Y %I:%M %p"),
        "text": comment.content,
    }


def _resolve_comment_root(comment_lookup, comment):
    current = comment
    seen = set()

    while current.parent_id:
        if current.parent_id in seen:
            break

        seen.add(current.parent_id)
        parent = comment_lookup.get(current.parent_id)
        if not parent:
            break

        current = parent

    return current


def _serialize_community_comment_threads(post, viewer=None, offset=0, limit=COMMUNITY_COMMENT_PAGE_SIZE):
    safe_offset = max(0, int(offset or 0))
    safe_limit = max(1, min(COMMUNITY_COMMENT_PAGE_SIZE, int(limit or COMMUNITY_COMMENT_PAGE_SIZE)))

    top_level_qs = (
        CommunityPostComment.objects
        .filter(post=post, parent__isnull=True)
        .select_related("user")
        .order_by("created_at", "id")
    )
    total_top_level = top_level_qs.count()
    top_level_comments = list(top_level_qs[safe_offset:safe_offset + safe_limit])

    thread_comments = list(top_level_comments)
    root_ids = [comment.id for comment in top_level_comments]

    if root_ids:
        frontier = list(root_ids)
        seen_ids = set(root_ids)

        while frontier:
            descendants = list(
                CommunityPostComment.objects
                .filter(post=post, parent_id__in=frontier)
                .select_related("user", "parent", "parent__user")
                .order_by("created_at", "id")
            )

            if not descendants:
                break

            next_frontier = []
            for descendant in descendants:
                if descendant.id in seen_ids:
                    continue
                seen_ids.add(descendant.id)
                thread_comments.append(descendant)
                next_frontier.append(descendant.id)

            if not next_frontier:
                break
            frontier = next_frontier

    comment_lookup = {comment.id: comment for comment in thread_comments}

    comment_like_totals = {}
    liked_comment_ids = set()
    if thread_comments:
        comment_ids = [comment.id for comment in thread_comments]
        comment_like_totals = {
            entry["comment_id"]: entry["total"]
            for entry in (
                CommunityPostCommentLike.objects
                .filter(comment_id__in=comment_ids)
                .values("comment_id")
                .annotate(total=Count("id"))
            )
        }

        if viewer and viewer.is_authenticated:
            liked_comment_ids = set(
                CommunityPostCommentLike.objects
                .filter(comment_id__in=comment_ids, user=viewer)
                .values_list("comment_id", flat=True)
            )

    top_level_payload_by_id = {}
    serialized_top_level = []
    for comment in top_level_comments:
        payload = _serialize_community_comment_payload(
            comment,
            like_total=comment_like_totals.get(comment.id, 0),
            liked=comment.id in liked_comment_ids,
            viewer=viewer,
        )
        payload["replies"] = []
        top_level_payload_by_id[comment.id] = payload
        serialized_top_level.append(payload)

    reply_comments = [comment for comment in thread_comments if comment.parent_id]
    reply_comments.sort(key=lambda comment: (comment.created_at, comment.id))

    for comment in reply_comments:
        root_comment = _resolve_comment_root(comment_lookup, comment)
        root_payload = top_level_payload_by_id.get(root_comment.id)
        if not root_payload:
            continue

        reply_payload = _serialize_community_comment_payload(
            comment,
            like_total=comment_like_totals.get(comment.id, 0),
            liked=comment.id in liked_comment_ids,
            viewer=viewer,
        )

        direct_parent = comment_lookup.get(comment.parent_id)
        reply_targets_reply = bool(direct_parent and direct_parent.parent_id)
        reply_payload["replyShowsChain"] = reply_targets_reply
        reply_payload["replyFromAuthor"] = reply_payload["author"] if reply_targets_reply else ""
        reply_payload["replyToAuthor"] = _display_name_for_user(direct_parent.user) if reply_targets_reply else ""
        root_payload["replies"].append(reply_payload)

    next_offset = safe_offset + len(top_level_comments)
    has_more = next_offset < total_top_level

    return {
        "comments": serialized_top_level,
        "hasMore": has_more,
        "nextOffset": next_offset if has_more else None,
    }


def _serialize_community_post(post, viewer=None, liked_post_ids=None, reported_post_ids=None):
    display_name = _display_name_for_user(post.user)
    avatar_url = _avatar_url_for_user(post.user)

    attachments = list(post.attachments.all())
    image_attachments = [_serialize_community_attachment(attachment) for attachment in attachments if _attachment_is_image(attachment)]
    file_attachments = [_serialize_community_attachment(attachment) for attachment in attachments if not _attachment_is_image(attachment)]

    activity = getattr(post, "activity", None)
    activity_image_url = _activity_image_url(activity) if activity else ""
    if activity_image_url:
        activity_image_name = Path(getattr(activity.image, "name", "") or "").name or "Activity image"
        image_attachments.insert(0, {
            "id": f"activity-image-{activity.id}",
            "name": activity_image_name,
            "url": activity_image_url,
            "previewUrl": activity_image_url,
            "src": activity_image_url,
            "isImage": True,
            "alt": f"{activity.title} activity image",
            "sizeLabel": "",
            "icon": "image",
        })

    post_likes_count = int(getattr(post, "likes_total", post.likes.count()))
    comment_count = int(getattr(post, "comments_total", post.comments.count()))

    liked_post = False
    if viewer and viewer.is_authenticated:
        if liked_post_ids is not None:
            liked_post = post.id in liked_post_ids
        else:
            liked_post = post.likes.filter(user=viewer).exists()

    author_id = getattr(post, 'user_id', None)
    is_author = bool(viewer and viewer.is_authenticated and author_id is not None and getattr(viewer, 'id', None) == author_id)

    reported_by_viewer = False
    if viewer and viewer.is_authenticated and reported_post_ids is not None:
        reported_by_viewer = post.id in reported_post_ids

    content = str(post.content or "")
    if content.startswith("[activity:"):
        marker_end = content.find("\n")
        if marker_end != -1:
            content = content[marker_end + 1 :]

    activity_details = None
    if activity:
        activity_date = _coerce_activity_date(getattr(activity, "date", None))
        activity_time = getattr(activity, "time_label", "TBA") or "TBA"
        activity_details = {
            "title": str(getattr(activity, "title", "") or "").strip(),
            "date": activity_date.strftime("%b %d, %Y") if activity_date else "",
            "time": str(activity_time),
            "dateTime": f"{activity_date.strftime('%a, %b %d, %Y') if activity_date else 'TBA'} · {activity_time}",
            "location": str(getattr(activity, "location", "") or "").strip() or "To be announced",
            "isAnnouncement": True,
        }

    return {
        "id": post.id,
        "author": display_name,
        "authorId": author_id,
        "isAuthor": is_author,
        "avatar": _initials_for_name(display_name),
        "avatarImage": avatar_url,
        "timestamp": timezone.localtime(post.created_at).strftime("%b %d, %Y %I:%M %p"),
        "timestampIso": timezone.localtime(post.created_at).isoformat(),
        "title": "",
        "content": content,
        "type": post.post_type,
        "likes": post_likes_count,
        "liked": bool(liked_post),
        "showComments": False,
        "commentsList": [],
        "commentCount": comment_count,
        "commentsHasMore": comment_count > 0,
        "commentsNextOffset": 0 if comment_count > 0 else None,
        "images": image_attachments,
        "attachments": file_attachments,
        "activity": activity_details,
        "reportedByViewer": reported_by_viewer,
    }


def _coerce_activity_date(value):
    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    text = str(value or "").strip()
    if not text:
        return None

    for pattern in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        return None


def _format_activity_schedule_label(activity):
    schedule_date = _coerce_activity_date(getattr(activity, "date", None))
    schedule_time = activity.time_label if activity else "TBA"
    schedule_date_label = schedule_date.strftime("%a, %b %d, %Y") if schedule_date else "TBA"
    return f"{schedule_date_label} · {schedule_time}"


def _activity_image_url(activity):
    image = getattr(activity, "image", None)
    if not image:
        return ""
    try:
        return image.url
    except ValueError:
        return ""


def _build_activity_announcement_content(activity):
    schedule_line = _format_activity_schedule_label(activity)
    location = str(getattr(activity, "location", "") or "").strip() or "To be announced"
    description = str(getattr(activity, "description", "") or "").strip()
    marker = f"[activity:{activity.id}]"

    lines = [
        marker,
        f"Activity update: {activity.title}",
        schedule_line,
        f"Location: {location}",
    ]
    if description:
        lines.append(description)

    return "\n".join(lines)


def _community_post_activity_link_is_available():
    try:
        with connection.cursor() as cursor:
            columns = {column.name for column in connection.introspection.get_table_description(cursor, CommunityPost._meta.db_table)}
        return "activity_id" in columns
    except Exception:
        return False


def _ensure_community_post_activity_schema():
    if _community_post_activity_link_is_available():
        return

    field = CommunityPost._meta.get_field("activity")
    try:
        with connection.schema_editor() as schema_editor:
            schema_editor.add_field(CommunityPost, field)
    except Exception:
        # If the DB cannot be altered at runtime, the calling view will fail
        # naturally on the next CommunityPost query rather than corrupting data.
        return


def _sync_activity_announcement_post(activity, actor):
    _ensure_community_post_activity_schema()
    existing_post = (
        CommunityPost.objects
        .filter(activity=activity)
        .order_by("-created_at", "-id")
        .first()
    )

    if activity.status != Activity.STATUS_ACTIVE:
        if existing_post:
            existing_post.delete()
        return None

    content = _build_activity_announcement_content(activity)
    if existing_post:
        existing_post.user = actor
        existing_post.content = content
        existing_post.post_type = "announcements"
        existing_post.save(update_fields=["user", "content", "post_type"])
        return existing_post

    return CommunityPost.objects.create(
        user=actor,
        activity=activity,
        content=content,
        post_type="announcements",
    )


def _redirect_to_dashboard_for_user(user):
    if user.is_superuser:
        return redirect("admin_dashboard")

    return redirect(_dashboard_url_for_user(user))


def _dashboard_url_for_user(user):
    if user and user.is_superuser:
        return reverse("admin_dashboard")

    role = _get_user_role(user)
    if role == UserProfile.ROLE_BENEFICIARY:
        return reverse("user_dashboard")
    if role == UserProfile.ROLE_VOLUNTEER:
        return reverse("volunteer_dashboard")
    return reverse("home")


def _settings_url_for_user(user):
    role = _get_user_role(user)
    if role == UserProfile.ROLE_VOLUNTEER:
        return reverse("volunteer_dashboard_settings")
    if role == UserProfile.ROLE_BENEFICIARY:
        return reverse("user_dashboard_settings")
    return reverse("home")


def _ensure_single_admin_template(template_filename):
    """Keep admin templates to one block set if external tooling appends duplicates."""
    template_path = Path(__file__).resolve().parent / "template" / "html" / "admin_dashboard" / template_filename

    try:
        if not template_path.exists():
            return

        raw = template_path.read_text(encoding="utf-8")
        if raw.count("{% block title %}") <= 1:
            return

        scripts_block = raw.find("{% block extra_scripts %}")
        if scripts_block == -1:
            return

        scripts_end = raw.find("{% endblock %}", scripts_block)
        if scripts_end == -1:
            return

        clean = raw[:scripts_end + len("{% endblock %}")].rstrip() + "\n"
        if clean != raw:
            template_path.write_text(clean, encoding="utf-8")
    except OSError:
        # Non-fatal: rendering should continue with current file content.
        return


def _ensure_single_dashboard_template(template_relative_path):
    """Keep dashboard templates to one block set if duplicate content is appended."""
    template_path = Path(__file__).resolve().parent / "template" / "html" / template_relative_path

    try:
        if not template_path.exists():
            return

        raw = template_path.read_text(encoding="utf-8")

        # Fast path: no duplicate starts and no duplicate title block.
        if raw.count("{% extends") <= 1 and raw.count("{% block title %}") <= 1:
            return

        first_extends = raw.find("{% extends")
        second_extends = raw.find("{% extends", first_extends + len("{% extends")) if first_extends != -1 else -1

        if second_extends != -1:
            clean = raw[:second_extends].rstrip() + "\n"
            if clean != raw:
                template_path.write_text(clean, encoding="utf-8")
            return

        scripts_block = raw.find("{% block extra_scripts %}")
        if scripts_block == -1:
            return

        scripts_end = raw.find("{% endblock %}", scripts_block)
        if scripts_end == -1:
            return

        clean = raw[:scripts_end + len("{% endblock %}")].rstrip() + "\n"
        if clean != raw:
            template_path.write_text(clean, encoding="utf-8")
    except OSError:
        # Non-fatal: rendering should continue with current file content.
        return


def _ensure_single_user_and_volunteer_community_templates():
    template_root = Path(__file__).resolve().parent / "template" / "html"
    user_template_path = template_root / "user_dashboard" / "user_community_user.html"
    expected_user_template = '{% extends "volunteer_dashboard/community_volunteer.html" %}\n'

    try:
        current = user_template_path.read_text(encoding="utf-8") if user_template_path.exists() else ""
        if current != expected_user_template:
            user_template_path.write_text(expected_user_template, encoding="utf-8")
    except OSError:
        # Non-fatal: continue rendering and still try to normalize volunteer template.
        pass

    _ensure_single_dashboard_template("volunteer_dashboard/community_volunteer.html")


def _ensure_single_donation_template():
    _ensure_single_admin_template("donation.html")


def _ensure_single_inventory_template():
    _ensure_single_admin_template("inventory.html")


def _ensure_single_payment_template():
    _ensure_single_admin_template("payment.html")


def _ensure_single_announcements_template():
    _ensure_single_admin_template("announcements.html")


def _ensure_single_community_posts_template():
    _ensure_single_admin_template("community_posts.html")


def _ensure_single_feedback_template():
    _ensure_single_admin_template("feedback.html")


def _ensure_single_moderation_template():
    _ensure_single_admin_template("moderation.html")


def _ensure_single_exports_template():
    _ensure_single_admin_template("exports.html")


def _ensure_single_audit_logs_template():
    _ensure_single_admin_template("audit_logs.html")


def index(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect("admin_dashboard")

    profile = None
    current_role = UserProfile.ROLE_REGULAR
    if request.user.is_authenticated:
        profile = _get_or_create_user_profile(request.user)
        current_role = profile.account_role or UserProfile.ROLE_REGULAR

    if request.user.is_authenticated and current_role == UserProfile.ROLE_BENEFICIARY:
        return redirect("user_dashboard")
    if request.user.is_authenticated and current_role == UserProfile.ROLE_VOLUNTEER:
        return redirect("volunteer_dashboard")

    beneficiary_form = BeneficiaryApplicationForm()
    volunteer_form = VolunteerApplicationForm()
    latest_applications = []
    if request.user.is_authenticated:
        latest_applications = list(_get_latest_role_applications(request.user).values())

    return render(request, "index.html", {
        "signin_form": SignInForm(),
        "signup_form": SignUpForm(),
        "is_authenticated_home": request.user.is_authenticated,
        "user_role": current_role,
        "current_user_profile": profile,
        "beneficiary_application_form": beneficiary_form,
        "volunteer_application_form": volunteer_form,
        "latest_role_applications": latest_applications,
    })


def signin(request):
    if request.user.is_authenticated:
        return _redirect_to_dashboard_for_user(request.user)

    if request.method != "POST":
        return redirect("home")

    form = SignInForm(request.POST)
    next_url = str(request.POST.get("next", "") or "").strip()
    safe_next_url = next_url if url_has_allowed_host_and_scheme(next_url, {request.get_host()}, require_https=request.is_secure()) else ""
    if form.is_valid():
        user = form.cleaned_data.get("user")

        if is_two_factor_enabled(user):
            return_url = safe_next_url or (_settings_url_for_user(user) if not is_two_factor_confirmed(user) else _dashboard_url_for_user(user))
            purpose = "setup" if not is_two_factor_confirmed(user) else "login"
            started, error_message = start_two_factor_challenge(request, user, purpose, return_url)
            if started:
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                return redirect("two_factor_verify")

            form.add_error(None, error_message or "We could not send a verification code right now.")
            return render(request, "index.html", {
                "signin_form": form,
                "signup_form": SignUpForm(),
                "open_modal": "signin",
            })

        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        if safe_next_url:
            return redirect(safe_next_url)
        return _redirect_to_dashboard_for_user(user)

    return render(request, "index.html", {
        "signin_form": form,
        "signup_form": SignUpForm(),
        "open_modal": "signin",
    })


def about(request):
    return render(request, "about.html", {
        "signin_form": SignInForm(),
        "signup_form": SignUpForm(),
    })


def donate(request):
    donation_config = getattr(django_settings, "DONATION_CONFIG", {})
    impact_examples = donation_config.get("impact_examples", [])
    programs = donation_config.get("programs") or getattr(django_settings, "DONATION_FALLBACK_PROGRAMS", [])
    programs = [dict(program) for program in programs if isinstance(program, dict)]
    shares = []
    for program in programs:
        try:
            shares.append(max(float(program.get("share", 0)), 0))
        except (TypeError, ValueError):
            shares.append(0)
    share_total = sum(shares)
    if not programs or share_total <= 0:
        programs = [dict(program) for program in getattr(django_settings, "DONATION_FALLBACK_PROGRAMS", [])]
        shares = [float(program.get("share", 0)) for program in programs]
        share_total = sum(shares)
    if programs and share_total > 0:
        normalized_total = 0
        for index, program in enumerate(programs):
            if index == len(programs) - 1:
                percentage = round(100 - normalized_total, 2)
            else:
                percentage = round(shares[index] / share_total * 100, 2)
                normalized_total += percentage
            program["share"] = percentage
            program.setdefault("color", ("#5c8d68", "#d28757", "#6885a0")[index % 3])
    return render(request, "donate.html", {
        "signin_form": SignInForm(),
        "signup_form": SignUpForm(),
        "donation_config": donation_config,
        "programs": programs,
    })


@login_required(login_url="signin")
def two_factor_verify(request):
    pending_challenge = get_pending_two_factor_challenge(request)
    if not pending_challenge or pending_challenge.get("user_id") != request.user.id:
        if is_two_factor_enabled(request.user) and not is_two_factor_confirmed(request.user):
            purpose = "setup"
            return_url = _settings_url_for_user(request.user)
            started, error_message = start_two_factor_challenge(request, request.user, purpose, return_url)
            if not started:
                return render(request, "two_factor_verify.html", {
                    "challenge_email_display": request.user.email,
                    "challenge_purpose": purpose,
                    "challenge_allow_logout": True,
                    "form_error": error_message or "We could not send a verification code right now.",
                })
            pending_challenge = get_pending_two_factor_challenge(request)
        else:
            return _redirect_to_dashboard_for_user(request.user)

    purpose = pending_challenge.get("purpose") or ("setup" if is_two_factor_enabled(request.user) and not is_two_factor_confirmed(request.user) else "login")
    return_url = pending_challenge.get("return_url") or _dashboard_url_for_user(request.user)

    if request.method == "POST":
        action = str(request.POST.get("action", "verify") or "verify").strip().lower()

        if action == "resend":
            started, error_message = start_two_factor_challenge(request, request.user, purpose, return_url)
            if not started:
                return render(request, "two_factor_verify.html", {
                    "challenge_email_display": request.user.email,
                    "challenge_purpose": purpose,
                    "challenge_allow_logout": True,
                    "form_error": error_message or "We could not send a new code right now.",
                })

            return render(request, "two_factor_verify.html", {
                "challenge_email_display": request.user.email,
                "challenge_purpose": purpose,
                "challenge_allow_logout": True,
                "success_message": "We sent a fresh code to your email.",
            })

        verification_code = str(request.POST.get("verification_code", "") or "").strip()
        if not verification_code:
            return render(request, "two_factor_verify.html", {
                "challenge_email_display": request.user.email,
                "challenge_purpose": purpose,
                "challenge_allow_logout": True,
                "form_error": "Please enter the 6-digit code from your email.",
            })

        if is_two_factor_challenge_expired(pending_challenge):
            started, error_message = start_two_factor_challenge(request, request.user, purpose, return_url)
            if not started:
                return render(request, "two_factor_verify.html", {
                    "challenge_email_display": request.user.email,
                    "challenge_purpose": purpose,
                    "challenge_allow_logout": True,
                    "form_error": error_message or "That code expired. Please request a new one.",
                })
            return render(request, "two_factor_verify.html", {
                "challenge_email_display": request.user.email,
                "challenge_purpose": purpose,
                "challenge_allow_logout": True,
                "form_error": "That code expired, so we sent a new one.",
            })

        if not is_two_factor_code_valid(pending_challenge, verification_code):
            touch_two_factor_challenge_attempt(request)
            return render(request, "two_factor_verify.html", {
                "challenge_email_display": request.user.email,
                "challenge_purpose": purpose,
                "challenge_allow_logout": True,
                "form_error": "That code was not correct. Please try again or send a new one.",
            })

        if is_two_factor_enabled(request.user):
            profile = _get_or_create_user_profile(request.user)
            state = profile.settings_state if isinstance(profile.settings_state, dict) else {}
            next_state = dict(state)
            next_state["security_2fa_enabled"] = True
            next_state["security_2fa_confirmed"] = True
            profile.settings_state = next_state
            profile.save(update_fields=["settings_state", "updated_at"])

        mark_two_factor_session_verified(request, request.user)
        return redirect(return_url)

    return render(request, "two_factor_verify.html", {
        "challenge_email_display": request.user.email,
        "challenge_purpose": purpose,
        "challenge_allow_logout": True,
    })


def products(request):
    is_regular_user = False
    if request.user.is_authenticated:
        user_profile = getattr(request.user, "userprofile", None)
        account_role = getattr(user_profile, "account_role", None)
        is_regular_user = (
            _get_user_role(request.user) == UserProfile.ROLE_REGULAR
            or account_role is None
        )
        print("PRODUCT PAGE ROLE: request.user.role=", getattr(request.user, "role", None), "userprofile.account_role=", account_role)

    return render(request, "product.html", {
        "signin_form": SignInForm(),
        "signup_form": SignUpForm(),
        "is_regular_user": is_regular_user,
    })


@login_required
@require_POST
def save_product_buyer_details(request):
    profile, _created = UserProfile.objects.get_or_create(user=request.user)
    profile.phone = str(request.POST.get("phone", "") or "").strip()
    profile.city_municipality = str(request.POST.get("city", "") or "").strip()
    profile.address_line = str(request.POST.get("street", "") or "").strip()
    profile.save(update_fields=["phone", "city_municipality", "address_line", "updated_at"])
    return JsonResponse({
        "phone": profile.phone,
        "city": profile.city_municipality,
        "street": profile.address_line,
    })


@login_required
@require_GET
def product_order_tracker(request):
    status_labels = {
        ProductInquiry.STATUS_PENDING: "Pending",
        ProductInquiry.STATUS_VERIFIED: "Confirmed",
        ProductInquiry.STATUS_COMPLETED: "Completed",
        ProductInquiry.STATUS_CANCELLED: "Cancelled",
        ProductInquiry.STATUS_FAILED: "Cancelled",
        ProductInquiry.STATUS_REFUNDED: "Cancelled",
    }
    image_map = {
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
    payment_labels = dict(ProductInquiry.PAYMENT_METHOD_CHOICES)
    orders = []
    for order in ProductInquiry.objects.filter(user=request.user).order_by("-created_at", "-id"):
        item = (order.order_items or [{}])[0]
        name = str(item.get("name", "Product")).strip()
        receipt_items = []
        for receipt_item in order.order_items or []:
            quantity = int(receipt_item.get("quantity", 1) or 1)
            unit_price = int(receipt_item.get("unit_price", 0) or 0)
            receipt_items.append({
                "name": str(receipt_item.get("name", "Product")).strip(),
                "variation": str(receipt_item.get("variation", "")).strip(),
                "quantity": quantity,
                "line_total": int(receipt_item.get("line_total", unit_price * quantity) or 0),
            })
        orders.append({
            "id": str(order.id),
            "order_number": f"ORD-{order.id:04d}",
            "name": name,
            "image": image_map.get(name, "/static/media/hand woven doormat.jpg"),
            "variation": str(item.get("variation", "")).strip(),
            "quantity": item.get("quantity", 1),
            "total": order.order_total,
            "date": order.created_at.strftime("%b %d, %Y"),
            "items": receipt_items,
            "payment_method": payment_labels.get(order.payment_method, order.payment_method),
            "payment_status": status_labels.get(order.status, "Pending"),
            "customer_name": order.full_name or "Guest",
            "status": order.status,
            "status_label": status_labels.get(order.status, "Pending"),
        })
    return JsonResponse({
        "orders": orders,
        "active_count": sum(order["status"] not in {"completed", "cancelled"} for order in orders),
    })


@login_required
@require_POST
def cancel_product_order(request, order_id):
    order = get_object_or_404(ProductInquiry, id=order_id, user=request.user)
    if order.status not in {ProductInquiry.STATUS_PENDING, ProductInquiry.STATUS_VERIFIED}:
        return JsonResponse({"error": "This order can no longer be cancelled."}, status=400)
    order.delete()
    return JsonResponse({"deleted": True})


def _format_php(amount):
    return f"PHP {amount:,.0f}"


def _build_product_inquiry_admin_notification(full_name, email, phone, country_code, payment_method, order_items, order_total, message=""):
    payment_label = dict(ProductInquiry.PAYMENT_METHOD_CHOICES).get(payment_method, payment_method)
    lines = [
        f"Customer: {full_name}",
        f"Email: {email}",
        f"Phone: {country_code} {phone}".strip(),
        f"Payment Method: {payment_label}",
        "Order Items:",
    ]

    for item in order_items:
        lines.append(
            f"- {item['quantity']} x {item['name']} ({item['category']}) @ {_format_php(item['unit_price'])} = {_format_php(item['line_total'])}"
        )

    lines.append(f"Total: {_format_php(order_total)}")
    if message:
        lines.append(f"Message: {message}")

    return "\n".join(lines)


def _build_order_confirmation_email_html(inquiry):
    order_id = f"ORD-{inquiry.id:04d}"
    reference = f"PI-{inquiry.id:05d}"

    item_rows = ""
    for item in (inquiry.order_items or []):
        item_rows += (
            '<tr style="border-bottom:1px solid #f3f4f6;">'
            f'<td style="padding:8px 0;font-size:14px;color:#374151;">{item.get("name", "")}</td>'
            f'<td style="padding:8px 0;font-size:14px;color:#374151;text-align:center;">{item.get("quantity", 0)}</td>'
            f'<td style="padding:8px 0;font-size:14px;color:#374151;text-align:right;">&#x20B1;&nbsp;{item.get("unit_price", 0):,}</td>'
            f'<td style="padding:8px 0;font-size:14px;color:#374151;text-align:right;">&#x20B1;&nbsp;{item.get("line_total", 0):,}</td>'
            '</tr>'
        )

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
</head>
<body style="margin:0;padding:0;background:#f4f7f6;font-family:Arial,Helvetica,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f7f6;">
    <tr>
      <td align="center" style="padding:40px 16px;">
        <table cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;max-width:600px;width:100%;">

          <!-- Header -->
          <tr>
            <td style="background:#0F6E56;padding:28px 32px;text-align:center;">
              <h1 style="color:#ffffff;margin:0;font-size:22px;font-weight:700;letter-spacing:-0.3px;">HappYness Project</h1>
              <p style="color:rgba(255,255,255,0.75);margin:5px 0 0;font-size:13px;">Happy Nanays Initiative</p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:36px 32px 28px;">
              <h2 style="color:#0F6E56;margin:0 0 6px;font-size:21px;font-weight:700;">Your order has been confirmed! &#x1F389;</h2>
              <p style="color:#374151;margin:0 0 22px;font-size:15px;line-height:1.6;">Hi {inquiry.full_name},</p>
              <p style="color:#374151;margin:0 0 28px;font-size:15px;line-height:1.7;">
                Great news! We have received your payment and your order has been verified.
              </p>

              <!-- Order meta -->
              <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0faf6;border-radius:8px;margin-bottom:28px;">
                <tr>
                  <td style="padding:14px 16px;vertical-align:top;">
                    <span style="color:#6b7280;font-size:11px;text-transform:uppercase;letter-spacing:0.06em;display:block;margin-bottom:4px;">Order ID</span>
                    <strong style="color:#111827;font-size:14px;">{order_id}</strong>
                  </td>
                  <td style="padding:14px 16px;vertical-align:top;">
                    <span style="color:#6b7280;font-size:11px;text-transform:uppercase;letter-spacing:0.06em;display:block;margin-bottom:4px;">Reference</span>
                    <strong style="color:#111827;font-size:14px;">{reference}</strong>
                  </td>
                  <td style="padding:14px 16px;vertical-align:top;">
                    <span style="color:#6b7280;font-size:11px;text-transform:uppercase;letter-spacing:0.06em;display:block;margin-bottom:4px;">Payment Method</span>
                    <strong style="color:#111827;font-size:14px;">Cash on Delivery</strong>
                  </td>
                </tr>
              </table>

              <!-- Delivery address -->
              <p style="color:#0F6E56;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;margin:0 0 10px;">Delivery Address</p>
              <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0faf6;border-radius:8px;margin-bottom:28px;">
                <tr>
                  <td style="padding:14px 16px;">
                    <p style="margin:0 0 4px;font-size:14px;color:#111827;">{inquiry.delivery_street}</p>
                    <p style="margin:0 0 2px;font-size:14px;color:#374151;">{inquiry.delivery_city}, {inquiry.delivery_province} {inquiry.delivery_zip}</p>
                    <p style="margin:0;font-size:14px;color:#374151;">{inquiry.delivery_country}</p>
                  </td>
                </tr>
              </table>

              <!-- Items table -->
              <p style="color:#0F6E56;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;margin:0 0 10px;">Items Ordered</p>
              <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;margin-bottom:28px;">
                <thead>
                  <tr style="border-bottom:2px solid #e5e7eb;">
                    <th style="text-align:left;padding:7px 0;font-size:12px;color:#6b7280;font-weight:600;">Item</th>
                    <th style="text-align:center;padding:7px 0;font-size:12px;color:#6b7280;font-weight:600;">Qty</th>
                    <th style="text-align:right;padding:7px 0;font-size:12px;color:#6b7280;font-weight:600;">Unit Price</th>
                    <th style="text-align:right;padding:7px 0;font-size:12px;color:#6b7280;font-weight:600;">Total</th>
                  </tr>
                </thead>
                <tbody>{item_rows}</tbody>
                <tfoot>
                  <tr style="border-top:2px solid #e5e7eb;">
                    <td colspan="3" style="padding:12px 0;text-align:right;font-weight:700;color:#111827;font-size:15px;">Order Total</td>
                    <td style="padding:12px 0;text-align:right;font-weight:700;color:#0F6E56;font-size:16px;">&#x20B1;&nbsp;{inquiry.order_total:,}</td>
                  </tr>
                </tfoot>
              </table>

              <!-- Thank-you note -->
              <p style="color:#374151;font-size:15px;line-height:1.7;margin:0 0 28px;border-left:4px solid #0F6E56;padding-left:14px;">
                Thank you for supporting Happy Nanays! Your order is now being prepared.
              </p>

              <!-- Contact -->
              <p style="color:#6b7280;font-size:13px;margin:0;line-height:1.6;">
                Questions? Reach us at
                <a href="mailto:info@happynessproject.org" style="color:#0F6E56;text-decoration:none;">info@happynessproject.org</a>.
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background:#f0faf6;padding:18px 32px;text-align:center;border-top:1px solid #d1fae5;">
              <p style="color:#6b7280;font-size:12px;margin:0;">&copy; 2026 HappYness Project &middot; Happy Nanays Initiative</p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


@require_POST
def submit_product_inquiry(request):
    if not request.user.is_authenticated or _get_user_role(request.user) != UserProfile.ROLE_REGULAR:
        return JsonResponse({
            "error": "You must be signed in as a customer to place an order."
        }, status=403)

    # Handle initial inquiry submission
    full_name = str(request.POST.get("full_name", "")).strip()
    email = str(request.POST.get("email", "")).strip()
    phone = str(request.POST.get("phone", "")).strip()
    country_code = str(request.POST.get("country_code", "+63")).strip() or "+63"
    message = str(request.POST.get("message", "")).strip()
    delivery_street = str(request.POST.get("delivery_street", "")).strip()
    delivery_city = str(request.POST.get("delivery_city", "")).strip()
    delivery_province = str(request.POST.get("delivery_province", "")).strip()
    delivery_zip = str(request.POST.get("delivery_zip", "")).strip()
    delivery_country = str(request.POST.get("delivery_country", "Philippines")).strip() or "Philippines"
    payment_method = str(request.POST.get("payment_method", "")).strip()
    order_items_raw = str(request.POST.get("order_items", "")).strip()
    payment_screenshot = request.FILES.get("payment_screenshot")

    if not full_name or not email or not phone:
        return JsonResponse({"error": "Full name, email, and phone are required."}, status=400)

    if payment_method not in dict(ProductInquiry.PAYMENT_METHOD_CHOICES):
        return JsonResponse({"error": "Please choose a valid payment method."}, status=400)

    try:
        order_items_data = json.loads(order_items_raw or "[]")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Order details are invalid."}, status=400)

    if not isinstance(order_items_data, list) or not order_items_data:
        return JsonResponse({"error": "Please select at least one product."}, status=400)

    normalized_items = []
    order_total = 0

    for item in order_items_data:
        if not isinstance(item, dict):
            return JsonResponse({"error": "Order details are invalid."}, status=400)

        name = str(item.get("name", "")).strip()
        category = str(item.get("category", "")).strip()
        quantity = _parse_non_negative_int(item.get("quantity"), default=0)
        if not name or not category or quantity <= 0:
            return JsonResponse({"error": "Order details are invalid."}, status=400)

        unit_price = PRODUCT_CATEGORY_PRICES.get(category)
        if unit_price is None:
            return JsonResponse({"error": f"Unsupported product category: {category}."}, status=400)

        line_total = unit_price * quantity
        order_total += line_total
        normalized_items.append({
            "name": name,
            "category": category,
            "variation": str(item.get("variation", "")).strip(),
            "quantity": quantity,
            "unit_price": unit_price,
            "line_total": line_total,
        })

    admin_notification = _build_product_inquiry_admin_notification(
        full_name,
        email,
        phone,
        country_code,
        payment_method,
        normalized_items,
        order_total,
        message,
    )

    inquiry = ProductInquiry(
        user=request.user if request.user.is_authenticated else None,
        full_name=full_name,
        email=email,
        phone=phone,
        country_code=country_code,
        message=message,
        payment_method=payment_method,
        order_items=normalized_items,
        order_total=order_total,
        delivery_street=delivery_street,
        delivery_city=delivery_city,
        delivery_province=delivery_province,
        delivery_zip=delivery_zip,
        delivery_country=delivery_country,
        admin_notification=admin_notification,
    )

    if payment_screenshot:
        # Validate screenshot file type and size
        import os
        ext = os.path.splitext(payment_screenshot.name)[1].lower()
        if ext not in ['.jpg', '.jpeg', '.png']:
            return JsonResponse({'error': 'Only JPEG and PNG files are allowed.'}, status=400)
        
        # Check file size (5MB max)
        if payment_screenshot.size > 5 * 1024 * 1024:
            return JsonResponse({'error': 'File size must not exceed 5MB.'}, status=400)
        
        inquiry.payment_screenshot = payment_screenshot

    try:
        inquiry.save()
    except ValidationError as exc:
        print(f"ValidationError saving ProductInquiry: {exc}")
        return JsonResponse({"error": "; ".join(exc.messages)}, status=400)
    except Exception as exc:
        print(f"Unexpected error saving ProductInquiry: {type(exc).__name__}: {exc}")
        return JsonResponse({"error": "Unable to process your inquiry. Please try again."}, status=500)

    response_status_labels = {
        ProductInquiry.STATUS_PENDING: "Pending",
        ProductInquiry.STATUS_VERIFIED: "Confirmed",
        ProductInquiry.STATUS_COMPLETED: "Completed",
        ProductInquiry.STATUS_CANCELLED: "Cancelled",
        ProductInquiry.STATUS_FAILED: "Cancelled",
        ProductInquiry.STATUS_REFUNDED: "Cancelled",
    }
    return JsonResponse({
        "message": "Product inquiry received.",
        "inquiryId": str(inquiry.id),
        "paymentMethod": inquiry.payment_method,
        "orderTotal": inquiry.order_total,
        "order": {
            "id": str(inquiry.id),
            "order_number": f"ORD-{inquiry.id:04d}",
            "date": inquiry.created_at.strftime("%b %d, %Y"),
            "items": [
                {
                    "name": item["name"],
                    "variation": item["variation"],
                    "quantity": item["quantity"],
                    "line_total": item["line_total"],
                }
                for item in inquiry.order_items
            ],
            "total": inquiry.order_total,
            "payment_method": dict(ProductInquiry.PAYMENT_METHOD_CHOICES).get(inquiry.payment_method, inquiry.payment_method),
            "payment_status": response_status_labels.get(inquiry.status, "Pending"),
            "customer_name": inquiry.full_name or "Guest",
        },
    }, status=201)


def contact(request):
    return render(request, "contact.html", {
        "signin_form": SignInForm(),
        "signup_form": SignUpForm(),
    })


def signup(request):
    if request.user.is_authenticated:
        return _redirect_to_dashboard_for_user(request.user)

    if request.method != "POST":
        return redirect("home")

    form = SignUpForm(request.POST)
    if form.is_valid():
        user = form.save()
        _get_or_create_user_profile(user)
        authenticated_user = authenticate(request, username=user.username, password=form.cleaned_data.get("password1"), backend='django.contrib.auth.backends.ModelBackend')
        if authenticated_user is not None:
            login(request, authenticated_user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect("home")
        # Fallback: log in the saved user directly by assigning a backend if authentication did not return one
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return redirect("home")

    return render(request, "index.html", {
        "signup_form": form,
        "signin_form": SignInForm(),
        "open_modal": "signup",
    })


@login_required(login_url="signin")
def user_dashboard(request):
    if request.user.is_superuser:
        return redirect("admin_dashboard")

    profile = _get_or_create_user_profile(request.user)
    if profile.account_role == UserProfile.ROLE_VOLUNTEER:
        return redirect("volunteer_dashboard")
    if not _is_active_beneficiary(request.user):
        return redirect("home")

    return render(request, "user_dashboard/dashboard_user.html", {
        "active_page": "dashboard",
        "dashboard_scope": "beneficiary",
    })


@require_POST
def apply_beneficiary(request):
    if request.user.is_superuser:
        return JsonResponse({"error": "Only dashboard users can submit applications."}, status=403)

    if _get_user_role(request.user) != UserProfile.ROLE_REGULAR:
        return JsonResponse({"error": "Only regular users can submit a new application."}, status=403)

    barangay = str(request.POST.get("barangay", "") or "").strip()
    supporting_information = str(request.POST.get("supporting_information", "") or request.POST.get("address", "") or "").strip()
    if barangay:
        supporting_information = f"{barangay}, Bacoor City, Cavite"

    post_data = request.POST.copy()
    post_data["supporting_information"] = supporting_information

    form = BeneficiaryApplicationForm(post_data)
    if form.is_valid():
        application = form.save(request.user if request.user.is_authenticated else None)
        _notify_admins_about_role_application(application)
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"message": "Beneficiary application submitted.", "applicationId": str(application.id)}, status=201)
        return redirect("home")

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"error": form.errors}, status=400)

    return render(request, "index.html", {
        "signin_form": SignInForm(),
        "signup_form": SignUpForm(),
        "is_authenticated_home": True,
        "user_role": _get_user_role(request.user),
        "current_user_profile": _get_or_create_user_profile(request.user),
        "beneficiary_application_form": form,
        "volunteer_application_form": VolunteerApplicationForm(),
        "latest_role_applications": list(_get_latest_role_applications(request.user).values()),
        "open_application": "beneficiary",
    })


@require_POST
def apply_volunteer(request):
    if request.user.is_superuser:
        return JsonResponse({"error": "Only dashboard users can submit applications."}, status=403)

    if _get_user_role(request.user) != UserProfile.ROLE_REGULAR:
        return JsonResponse({"error": "Only regular users can submit a new application."}, status=403)

    post_data = request.POST.copy()
    email = str(post_data.get("email", "") or "").strip()
    phone = str(post_data.get("phone", "") or "").strip()
    contact_details = " / ".join([value for value in [phone, email] if value])
    post_data.setdefault("contact_details", contact_details)
    post_data.setdefault("skills", "")
    post_data.setdefault("areas_of_interest", "")

    form = VolunteerApplicationForm(post_data)
    if form.is_valid():
        application = form.save(request.user if request.user.is_authenticated else None)
        _notify_admins_about_role_application(application)
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"message": "Volunteer application submitted.", "applicationId": str(application.id)}, status=201)
        return redirect("home")

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"error": form.errors}, status=400)

    return render(request, "index.html", {
        "signin_form": SignInForm(),
        "signup_form": SignUpForm(),
        "is_authenticated_home": True,
        "user_role": _get_user_role(request.user),
        "current_user_profile": _get_or_create_user_profile(request.user),
        "beneficiary_application_form": BeneficiaryApplicationForm(),
        "volunteer_application_form": form,
        "latest_role_applications": list(_get_latest_role_applications(request.user).values()),
        "open_application": "volunteer",
    })


@login_required(login_url="signin")
@require_POST
def create_volunteer(request):
    if not request.user.is_superuser:
        return JsonResponse({"error": "Only administrators can add volunteers."}, status=403)

    full_name = str(request.POST.get("full_name", "") or "").strip()
    email = str(request.POST.get("email", "") or "").strip()
    phone = str(request.POST.get("phone", "") or "").strip()
    availability = str(request.POST.get("availability", "") or "").strip()
    skills = str(request.POST.get("skills", "") or "").strip()
    areas_of_interest = str(request.POST.get("areas_of_interest", "") or "").strip()
    username = str(request.POST.get("username", "") or "").strip()
    password = str(request.POST.get("password", "") or "")
    status_value = str(request.POST.get("status", RoleApplication.STATUS_PENDING) or RoleApplication.STATUS_PENDING).strip().lower()

    if not full_name or not email or not phone or not availability or not username or not password:
        return JsonResponse({"error": "Full name, email, phone, availability, username, and password are required."}, status=400)

    if User.objects.filter(username__iexact=username).exists():
        return JsonResponse({"error": "That username is already taken."}, status=400)

    if status_value not in {"active", "pending", "inactive"}:
        return JsonResponse({"error": "Please choose a valid status."}, status=400)

    first_name, last_name = _split_full_name(full_name)
    application_status = {
        "active": RoleApplication.STATUS_APPROVED,
        "pending": RoleApplication.STATUS_PENDING,
        "inactive": RoleApplication.STATUS_INACTIVE,
    }[status_value]

    with transaction.atomic():
        user = User.objects.filter(username__iexact=username).first()
        if not user and email:
            user = User.objects.filter(email__iexact=email).first()

        is_new_user = user is None

        if not user:
            user = User.objects.create_user(username=username, email=email)
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        if is_new_user:
            user.set_password(password)
        user.is_active = True
        user.save(update_fields=["first_name", "last_name", "email", "password", "is_active"])

        profile = _get_or_create_user_profile(user)
        profile.account_role = UserProfile.ROLE_VOLUNTEER
        profile.phone = phone
        profile.volunteer_role = skills or "Volunteer"
        profile.assigned_chapter_area = areas_of_interest
        profile.save(update_fields=["account_role", "phone", "volunteer_role", "assigned_chapter_area", "updated_at"])

        application, _created = RoleApplication.objects.update_or_create(
            user=user,
            role=RoleApplication.ROLE_VOLUNTEER,
            defaults={
                "status": application_status,
                "full_name": full_name,
                "contact_details": f"{phone} / {email}" if phone and email else (phone or email),
                "skills": skills,
                "availability": availability,
                "areas_of_interest": areas_of_interest,
            },
        )

    volunteer_payload = _build_volunteers_payload()
    created_volunteer = next((item for item in volunteer_payload if item["id"] == int(user.id)), None)
    if not created_volunteer:
        created_volunteer = {
            "id": int(user.id),
            "name": full_name,
            "email": email,
            "contact": phone,
            "program": skills or "Volunteer",
            "availability": availability,
            "hoursRendered": 0,
            "ojtHours": 0,
            "requiredOjtHours": 80,
            "status": status_value.capitalize(),
            "participationRate": 0,
            "joinedDate": timezone.localtime(application.created_at).strftime("%Y-%m-%d"),
            "assignedThisWeek": False,
        }

    application_payload = _serialize_pending_volunteer_application(application)
    application_payload["status"] = status_value

    return JsonResponse({
        "message": f"Volunteer added for {full_name}.",
        "volunteer": created_volunteer,
        "application": application_payload,
        "credentials": {
            "username": username,
            "password": password,
        },
    }, status=201)


@login_required(login_url="signin")
@require_POST
def update_volunteer_profile(request):
    if not request.user.is_superuser:
        return JsonResponse({"error": "Only administrators can update volunteer profiles."}, status=403)

    volunteer_user_id = _parse_non_negative_int(request.POST.get("volunteer_user_id") or request.POST.get("volunteer_id"), default=0)
    if volunteer_user_id <= 0:
        return JsonResponse({"error": "A volunteer profile is required."}, status=400)

    user = get_object_or_404(User, pk=volunteer_user_id)
    profile = _get_or_create_user_profile(user)

    full_name = str(request.POST.get("full_name", "") or "").strip()
    email = str(request.POST.get("email", "") or "").strip()
    phone = str(request.POST.get("phone", "") or "").strip()
    availability = str(request.POST.get("availability", "") or "").strip()
    skills = str(request.POST.get("skills", "") or "").strip()
    areas_of_interest = str(request.POST.get("areas_of_interest", "") or "").strip()
    status_value = str(request.POST.get("status", "Active") or "Active").strip().lower()

    if not full_name or not email or not phone or not availability:
        return JsonResponse({"error": "Full name, email, phone, and availability are required."}, status=400)

    if status_value not in {"active", "pending", "inactive"}:
        return JsonResponse({"error": "Please choose a valid status."}, status=400)

    name_parts = full_name.split()
    first_name = name_parts[0] if name_parts else ""
    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
    application_status = {
        "active": RoleApplication.STATUS_APPROVED,
        "pending": RoleApplication.STATUS_PENDING,
        "inactive": RoleApplication.STATUS_INACTIVE,
    }[status_value]

    with transaction.atomic():
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.is_active = True
        user.save(update_fields=["first_name", "last_name", "email", "is_active"])

        profile.account_role = UserProfile.ROLE_VOLUNTEER
        profile.phone = phone
        profile.volunteer_role = skills or profile.volunteer_role or "Volunteer"
        profile.assigned_chapter_area = areas_of_interest
        profile.save(update_fields=["account_role", "phone", "volunteer_role", "assigned_chapter_area", "updated_at"])

        volunteer_application = (
            RoleApplication.objects
            .filter(user=user, role=RoleApplication.ROLE_VOLUNTEER)
            .order_by("-created_at", "-id")
            .first()
        )

        contact_details = f"{phone} / {email}" if phone and email else (phone or email)
        if volunteer_application:
            volunteer_application.full_name = full_name
            volunteer_application.contact_details = contact_details
            volunteer_application.skills = skills
            volunteer_application.availability = availability
            volunteer_application.areas_of_interest = areas_of_interest
            volunteer_application.status = application_status
            volunteer_application.reviewed_at = timezone.now()
            volunteer_application.reviewed_by = request.user
            volunteer_application.save(update_fields=["full_name", "contact_details", "skills", "availability", "areas_of_interest", "status", "reviewed_at", "reviewed_by", "updated_at"])
        else:
            volunteer_application = RoleApplication.objects.create(
                user=user,
                role=RoleApplication.ROLE_VOLUNTEER,
                status=application_status,
                full_name=full_name,
                contact_details=contact_details,
                skills=skills,
                availability=availability,
                areas_of_interest=areas_of_interest,
                reviewed_at=timezone.now(),
                reviewed_by=request.user,
            )

    volunteer_payload = _get_volunteer_payload_for_user(user.id)
    if not volunteer_payload:
        volunteer_payload = {
            "id": int(user.id),
            "name": full_name,
            "username": user.username,
            "email": email,
            "contact": phone,
            "program": skills or "Volunteer",
            "skills": skills or "",
            "areasOfInterest": areas_of_interest,
            "availability": availability,
            "hoursRendered": 0,
            "ojtHours": 0,
            "status": status_value.capitalize(),
            "participationRate": 0,
            "joinedDate": timezone.localtime(volunteer_application.created_at).strftime("%Y-%m-%d") if volunteer_application else "",
            "assignedThisWeek": False,
            "activityHistory": [],
            "activityCount": 0,
            "lastActivityDate": "",
        }

    return JsonResponse({
        "message": f"Volunteer profile updated for {full_name}.",
        "volunteer": volunteer_payload,
    })


@login_required(login_url="signin")
@require_POST
def update_volunteer_ojt_requirement(request):
    if not request.user.is_superuser:
        return JsonResponse({"error": "Only administrators can update OJT requirements."}, status=403)

    volunteer_user_id = _parse_non_negative_int(request.POST.get("volunteer_user_id") or request.POST.get("volunteer_id"), default=0)
    if volunteer_user_id <= 0:
        return JsonResponse({"error": "A volunteer profile is required."}, status=400)

    raw_required_hours = str(request.POST.get("required_ojt_hours", "") or "").strip()
    try:
        required_hours = Decimal(raw_required_hours)
    except (InvalidOperation, ValueError):
        return JsonResponse({"error": "Required OJT hours must be a valid number."}, status=400)

    if not required_hours.is_finite() or required_hours <= 0 or required_hours > Decimal("10000"):
        return JsonResponse({"error": "Required OJT hours must be greater than 0 and no more than 10,000."}, status=400)

    if required_hours.as_tuple().exponent < -2:
        return JsonResponse({"error": "Required OJT hours can have at most 2 decimal places."}, status=400)

    supervisor = str(request.POST.get("ojt_supervisor", "") or "").strip()
    program = str(request.POST.get("ojt_program", "") or "").strip()
    next_check_in_raw = str(request.POST.get("ojt_next_check_in", "") or "").strip()
    next_check_in = None
    if next_check_in_raw:
        try:
            next_check_in = date.fromisoformat(next_check_in_raw)
        except ValueError:
            return JsonResponse({"error": "Next check-in must be a valid date."}, status=400)
    if len(supervisor) > 150 or len(program) > 150:
        return JsonResponse({"error": "Supervisor and program names must be 150 characters or fewer."}, status=400)

    schedule_update_requested = "schedule_days" in request.POST
    schedule_days = []
    schedule_times = {}
    effective_from = timezone.localdate()
    effective_until = None
    if schedule_update_requested:
        try:
            raw_days = json.loads(request.POST.get("schedule_days") or "[]")
            raw_times = json.loads(request.POST.get("schedule_times") or "{}")
        except (json.JSONDecodeError, TypeError):
            return JsonResponse({"error": "Schedule days and times must be valid JSON."}, status=400)
        if not isinstance(raw_days, list) or not isinstance(raw_times, dict):
            return JsonResponse({"error": "Schedule days and times have an invalid format."}, status=400)
        try:
            schedule_days = sorted({int(day) for day in raw_days})
        except (TypeError, ValueError):
            return JsonResponse({"error": "Choose valid weekdays for the OJT schedule."}, status=400)
        if any(day < 0 or day > 6 for day in schedule_days):
            return JsonResponse({"error": "Choose valid weekdays for the OJT schedule."}, status=400)

        effective_from_raw = str(request.POST.get("schedule_effective_from") or "").strip()
        if effective_from_raw:
            try:
                effective_from = date.fromisoformat(effective_from_raw)
            except ValueError:
                return JsonResponse({"error": "Effective from must be a valid date."}, status=400)
        if effective_from < timezone.localdate():
            return JsonResponse({"error": "Schedule changes cannot be effective before today."}, status=400)
        effective_until_raw = str(request.POST.get("schedule_effective_until") or "").strip()
        if effective_until_raw:
            try:
                effective_until = date.fromisoformat(effective_until_raw)
            except ValueError:
                return JsonResponse({"error": "Schedule end date must be a valid date."}, status=400)
            if effective_until < effective_from:
                return JsonResponse({"error": "Schedule end date must be on or after its effective date."}, status=400)

        for day in schedule_days:
            raw_day_times = raw_times.get(str(day), {})
            if not isinstance(raw_day_times, dict):
                return JsonResponse({"error": "Per-day schedule times have an invalid format."}, status=400)
            start_value = str(raw_day_times.get("start") or "").strip()
            end_value = str(raw_day_times.get("end") or "").strip()
            if bool(start_value) != bool(end_value):
                return JsonResponse({"error": "Enter both a start and end time for each timed duty day."}, status=400)
            if not start_value:
                continue
            try:
                start_time = time.fromisoformat(start_value)
                end_time = time.fromisoformat(end_value)
            except ValueError:
                return JsonResponse({"error": "Duty-day times must be valid times."}, status=400)
            if end_time <= start_time:
                return JsonResponse({"error": "Duty-day end times must be after their start times."}, status=400)
            schedule_times[str(day)] = {"start": start_time.strftime("%H:%M"), "end": end_time.strftime("%H:%M")}

    user = get_object_or_404(User, pk=volunteer_user_id)
    profile = _get_or_create_user_profile(user)
    if profile.account_role != UserProfile.ROLE_VOLUNTEER:
        return JsonResponse({"error": "This user is not currently a volunteer."}, status=400)

    schedule = None
    if schedule_update_requested:
        current_schedule = _ojt_schedule_for_date(user, timezone.localdate())
        if current_schedule and effective_from == timezone.localdate() and schedule_days == sorted(int(day) for day in current_schedule.weekdays) and schedule_times == current_schedule.daily_times and effective_until == current_schedule.effective_until:
            schedule_update_requested = False
        elif not current_schedule and not schedule_days:
            schedule_update_requested = False

    if schedule_update_requested:
        if VolunteerOjtSchedule.objects.filter(volunteer=user, effective_from=effective_from).exists():
            return JsonResponse({"error": "A schedule already starts on this date. Choose a later effective date to preserve that day's schedule history."}, status=400)
        future_schedule_exists = VolunteerOjtSchedule.objects.filter(
            volunteer=user,
            effective_from__gt=effective_from,
        ).exists()
        if future_schedule_exists:
            return JsonResponse({"error": "A later OJT schedule already exists. Choose an effective date after it or remove that future schedule first."}, status=400)

    with transaction.atomic():
        profile.required_ojt_hours = required_hours
        profile.ojt_supervisor = supervisor
        profile.ojt_program = program
        profile.ojt_next_check_in = next_check_in
        profile.save(update_fields=["required_ojt_hours", "ojt_supervisor", "ojt_program", "ojt_next_check_in", "updated_at"])

        if schedule_update_requested:
            previous_schedule = VolunteerOjtSchedule.objects.filter(
                volunteer=user,
                effective_from__lt=effective_from,
            ).filter(
                Q(effective_until__isnull=True) | Q(effective_until__gte=effective_from),
            ).order_by("-effective_from", "-id").first()
            if previous_schedule:
                previous_schedule.effective_until = effective_from - timedelta(days=1)
                previous_schedule.save(update_fields=["effective_until"])

            if schedule_days:
                schedule = VolunteerOjtSchedule.objects.create(
                    volunteer=user,
                    effective_from=effective_from,
                    effective_until=effective_until,
                    weekdays=schedule_days,
                    daily_times=schedule_times,
                )

    return JsonResponse({
        "message": f"Required OJT hours updated for {_display_name_for_user(user)}.",
        "requiredOjtHours": float(required_hours),
        "ojtSupervisor": supervisor,
        "ojtProgram": program,
        "ojtNextCheckIn": next_check_in.isoformat() if next_check_in else "",
        "ojtSchedule": {
            "effectiveFrom": schedule.effective_from.isoformat() if schedule else "",
            "effectiveUntil": schedule.effective_until.isoformat() if schedule and schedule.effective_until else "",
            "weekdays": schedule.weekdays if schedule else [],
            "dailyTimes": schedule.daily_times if schedule else {},
        },
    })


@login_required(login_url="signin")
@require_POST
def adjust_volunteer_ojt_hours(request):
    if not request.user.is_superuser:
        return JsonResponse({"error": "Only administrators can adjust logged OJT hours."}, status=403)

    volunteer_user_id = _parse_non_negative_int(request.POST.get("volunteer_user_id") or request.POST.get("volunteer_id"), default=0)
    if volunteer_user_id <= 0:
        return JsonResponse({"error": "A volunteer profile is required."}, status=400)

    reset_to_zero = str(request.POST.get("reset_to_zero") or "").strip().lower() in {"1", "true", "yes", "y"}
    raw_adjustment_minutes = str(request.POST.get("adjustment_minutes") or "").strip()
    raw_adjustment = str(request.POST.get("hours_adjustment") or request.POST.get("adjustment_hours") or "").strip()

    if reset_to_zero:
        adjustment = Decimal("0") - Decimal(str((getattr(_get_or_create_user_profile(get_object_or_404(User, pk=volunteer_user_id)), "ojt_hours") or 0)))
    elif raw_adjustment_minutes:
        try:
            adjustment_minutes = int(raw_adjustment_minutes)
        except ValueError:
            return JsonResponse({"error": "Adjustment minutes must be a whole number."}, status=400)
        if abs(adjustment_minutes) > 600000:
            return JsonResponse({"error": "Adjustment cannot exceed 10,000 hours."}, status=400)
        adjustment = Decimal(adjustment_minutes) / Decimal("60")
    else:
        if not raw_adjustment:
            return JsonResponse({"error": "An hours-and-minutes adjustment is required."}, status=400)

        try:
            adjustment = Decimal(raw_adjustment)
        except (InvalidOperation, ValueError):
            return JsonResponse({"error": "Adjustment must be a valid number."}, status=400)

        if not adjustment.is_finite():
            return JsonResponse({"error": "Adjustment must be a valid number."}, status=400)

        if adjustment.as_tuple().exponent < -2:
            return JsonResponse({"error": "Adjustment can have at most 2 decimal places."}, status=400)

    user = get_object_or_404(User, pk=volunteer_user_id)
    profile = _get_or_create_user_profile(user)
    if profile.account_role != UserProfile.ROLE_VOLUNTEER:
        return JsonResponse({"error": "This user is not currently a volunteer."}, status=400)

    current_total = Decimal(str(profile.ojt_hours or 0))
    adjusted_total = current_total + adjustment
    if adjusted_total < Decimal("0"):
        return JsonResponse({"error": "Adjusted logged hours cannot go below zero."}, status=400)

    profile.ojt_hours = float(adjusted_total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    profile.save(update_fields=["ojt_hours", "updated_at"])

    return JsonResponse({
        "message": f"Logged OJT hours adjusted for {_display_name_for_user(user)}.",
        "ojtHours": float(profile.ojt_hours),
        "hoursAdjustment": float(adjustment),
        "resetToZero": reset_to_zero,
    })


@login_required(login_url="signin")
@require_POST
def deactivate_volunteer(request):
    if not request.user.is_superuser:
        return JsonResponse({"error": "Only administrators can remove volunteers."}, status=403)

    volunteer_user_id = _parse_non_negative_int(request.POST.get("volunteer_user_id") or request.POST.get("volunteer_id"), default=0)
    if volunteer_user_id <= 0:
        return JsonResponse({"error": "A volunteer profile is required."}, status=400)

    user = get_object_or_404(User, pk=volunteer_user_id)
    profile = _get_or_create_user_profile(user)

    if profile.account_role != UserProfile.ROLE_VOLUNTEER:
        return JsonResponse({"error": "This user is not currently a volunteer."}, status=400)

    with transaction.atomic():
        profile.account_role = UserProfile.ROLE_REGULAR
        profile.volunteer_role = ""
        profile.assigned_chapter_area = ""
        profile.save(update_fields=["account_role", "volunteer_role", "assigned_chapter_area", "updated_at"])

        latest_application = (
            RoleApplication.objects
            .filter(user=user, role=RoleApplication.ROLE_VOLUNTEER)
            .order_by("-created_at", "-id")
            .first()
        )
        if latest_application:
            latest_application.status = RoleApplication.STATUS_INACTIVE
            latest_application.reviewed_at = timezone.now()
            latest_application.reviewed_by = request.user
            latest_application.save(update_fields=["status", "reviewed_at", "reviewed_by", "updated_at"])

    return JsonResponse({
        "message": f"{_display_name_for_user(user)} removed as a beneficiary.",
        "removedVolunteerId": int(user.id),
    })


def _quarter_start(reference_dt):
    month = ((reference_dt.month - 1) // 3) * 3 + 1
    return reference_dt.replace(month=month, day=1, hour=0, minute=0, second=0, microsecond=0)


def _build_user_dashboard_overview_payload(user):
    now = timezone.localtime()

    beneficiary_application = (
        RoleApplication.objects
        .filter(user=user, role=RoleApplication.ROLE_BENEFICIARY, status=RoleApplication.STATUS_APPROVED)
        .order_by("-updated_at", "-id")
        .first()
    )
    assistance_records = list(
        BeneficiaryAssistanceRecord.objects
        .filter(beneficiary=beneficiary_application)
        .select_related("beneficiary", "feedback")
        .order_by("-assistance_date", "-created_at", "-id")
    ) if beneficiary_application else []

    program_labels = []
    for record in assistance_records:
        aid_label = (record.aid_type or "").strip()
        aid_lower = aid_label.lower()
        if "food" in aid_lower:
            program_label = "Food assistance"
        elif "hygiene" in aid_lower:
            program_label = "Hygiene assistance"
        elif "school" in aid_lower:
            program_label = "School supplies"
        else:
            program_label = aid_label
        if program_label and program_label not in program_labels:
            program_labels.append(program_label)

    received_programs = set(program_labels)
    history_items = []
    for record in assistance_records:
        aid_label = (record.aid_type or "Assistance").strip()
        aid_lower = aid_label.lower()
        category = "food" if "food" in aid_lower else "hygiene" if "hygiene" in aid_lower else "school" if "school" in aid_lower else "other"
        history_category = "teaching-kids" if "school" in aid_lower else "outreach"
        history_items.append({
            "assistance_record_id": int(record.id),
            "category": category,
            "outreach_category": history_category,
            "item": aid_label,
            "quantity": (record.quantity_or_amount or "").strip(),
            "date": record.assistance_date.strftime("%b %d, %Y"),
            "location": "Pickup point not recorded",
            "hasFeedback": bool(getattr(record, "feedback", None)),
            "feedback": {
                "rating": int(record.feedback.rating or 0),
                "comment": (record.feedback.comment or "").strip(),
            } if getattr(record, "feedback", None) else None,
        })

    completed_activities = list(
        Activity.objects
        .filter(status=Activity.STATUS_COMPLETED)
        .order_by("-date", "-id")
    )
    completed_activity_ids = [activity.id for activity in completed_activities]
    activity_feedback_by_id = {
        feedback.activity_id: feedback
        for feedback in BeneficiaryActivityFeedback.objects.filter(
            activity_id__in=completed_activity_ids,
            beneficiary=beneficiary_application,
        )
    } if beneficiary_application and completed_activity_ids else {}
    completed_activity_items = []
    for activity in completed_activities:
        feedback = activity_feedback_by_id.get(activity.id)
        completed_activity_items.append({
            "id": int(activity.id),
            "feedback_target": "activity",
            "outreach_category": activity.category or "other",
            "item": activity.title,
            "date": activity.date.strftime("%b %d, %Y"),
            "location": (activity.location or "Pickup location not recorded").strip(),
            "hasFeedback": bool(feedback),
            "feedback": {
                "rating": int(feedback.rating or 0),
                "comment": (feedback.comment or "").strip(),
            } if feedback else None,
        })

    skill_topics = list(SkillLearningTopic.objects.order_by("-is_recommended", "-popularity_score", "-created_at", "-id"))
    month_start = now.date().replace(day=1)
    skills_new = sum(1 for topic in skill_topics if topic.created_at and topic.created_at.date() >= month_start)
    skill_learning_url = reverse("user_dashboard_skill_learning")
    recommended_skills = [
        {
            "id": str(topic.id),
            "name": topic.title,
            "title": topic.title,
            "badge": (topic.badge_label or topic.primary_filter_tag or "Topic").strip() or "Topic",
            "category": topic.primary_filter_tag or "Community",
            "status": "new" if topic.created_at and topic.created_at.date() >= month_start else "learn",
            "course_slug": str(topic.id),
            "url": f"{skill_learning_url}?topic={topic.id}",
        }
        for topic in skill_topics[:4]
    ]

    announcement_posts = list(
        CommunityPost.objects.filter(post_type="announcements")
        .filter(_visible_activity_announcement_filter(user))
        .select_related("user")
        .order_by("-created_at", "-id")[:3]
    )
    announcement_payload = []
    for post in announcement_posts:
        content = (post.content or "").strip()
        if not content:
            continue
        title = content.splitlines()[0].strip() or content
        announcement_payload.append({
            "title": title[:180],
            "date_label": timezone.localtime(post.created_at).strftime("%b %d, %Y"),
        })

    next_pickup = {
        "state": "none",
            "id": None,
        "title": "",
        "datetime": "",
        "location": "",
        "requirements": "",
        "status": "Confirmed",
        "upcoming_items": [],
    }

    upcoming_activities = list(
        Activity.objects
        .filter(date__gte=now.date(), status=Activity.STATUS_ACTIVE)
        .filter(_visible_activity_filter(user))
        .distinct()
        .order_by("date", "start_time", "title")
    )
    beneficiary_attendance_by_activity = {}
    if getattr(user, "userprofile", None) and user.userprofile.account_role == UserProfile.ROLE_BENEFICIARY:
        beneficiary_attendance_by_activity = {
            row.activity_id: row
            for row in BeneficiaryActivityAttendance.objects.filter(
                activity_id__in=[activity.id for activity in upcoming_activities],
                beneficiary=user,
            )
        }
    upcoming_items = []
    for activity in upcoming_activities:
        time_label = None
        if getattr(activity, "start_time", None):
            time_label = activity.start_time.strftime("%I:%M %p").lstrip("0")
        location = (getattr(activity, "location", "") or "").strip()
        description = (getattr(activity, "description", "") or "").strip()
        activity_date = getattr(activity, "date", None)
        date_label = activity_date.strftime("%b %d, %Y") if activity_date else None
        date_time_text = _format_activity_schedule_label(activity)
        meta_parts = []
        if date_label and time_label:
            meta_parts.append(f"{date_label} · {time_label}")
        elif date_label:
            meta_parts.append(date_label)
        elif time_label:
            meta_parts.append(time_label)
        if location:
            meta_parts.append(location)
        upcoming_items.append({
            "id": int(activity.id),
            "title": activity.title,
            "category": getattr(activity, "category", "other") or "other",
            "category_label": activity.get_category_display() if hasattr(activity, "get_category_display") else "Other",
            "description": description,
            "image_url": _activity_image_url(activity),
            "datetime": date_time_text,
            "date_label": date_label,
            "time_label": time_label,
            "location": location or None,
            "status": "Confirmed",
            "beneficiary_attendance_status": (
                beneficiary_attendance_by_activity.get(activity.id).status
                if activity.id in beneficiary_attendance_by_activity else "unsubmitted"
            ),
            "beneficiary_attendance_status_label": (
                _serialize_beneficiary_activity_attendance(beneficiary_attendance_by_activity[activity.id])["status_label"]
                if activity.id in beneficiary_attendance_by_activity else "Awaiting volunteer confirmation"
            ),
            "beneficiary_attendance_confirmed_at": (
                beneficiary_attendance_by_activity[activity.id].confirmed_at.isoformat()
                if activity.id in beneficiary_attendance_by_activity and beneficiary_attendance_by_activity[activity.id].confirmed_at else ""
            ),
            "volunteer_count": int(getattr(activity, "volunteer_count", 0) or 0),
            "meta_line": " · ".join(meta_parts),
        })

    if upcoming_items:
        first_activity = upcoming_activities[0]
        first_location = (getattr(first_activity, "location", "") or "").strip()
        first_description = (getattr(first_activity, "description", "") or "").strip()
        first_time_label = None
        if getattr(first_activity, "start_time", None):
            first_time_label = first_activity.start_time.strftime("%I:%M %p").lstrip("0")
        next_pickup = {
            "state": "pending",
            "id": int(first_activity.id),
            "title": first_activity.title,
            "datetime": _format_activity_schedule_label(first_activity),
            "date_label": first_activity.date.strftime("%b %d, %Y") if getattr(first_activity, "date", None) else None,
            "time_label": first_time_label,
            "location": first_location or None,
            "description": first_description,
            "image_url": _activity_image_url(first_activity),
            "requirements": first_description or "Bring your beneficiary card and an eco bag.",
            "status": "Confirmed",
            "beneficiary_attendance_status": (
                beneficiary_attendance_by_activity.get(first_activity.id).status
                if first_activity.id in beneficiary_attendance_by_activity else "unsubmitted"
            ),
            "beneficiary_attendance_status_label": (
                _serialize_beneficiary_activity_attendance(beneficiary_attendance_by_activity[first_activity.id])["status_label"]
                if first_activity.id in beneficiary_attendance_by_activity else "Awaiting volunteer confirmation"
            ),
            "beneficiary_attendance_confirmed_at": (
                beneficiary_attendance_by_activity[first_activity.id].confirmed_at.isoformat()
                if first_activity.id in beneficiary_attendance_by_activity and beneficiary_attendance_by_activity[first_activity.id].confirmed_at else ""
            ),
            "volunteer_count": int(getattr(first_activity, "volunteer_count", 0) or 0),
            "upcoming_items": upcoming_items,
        }

    first_name = (user.first_name or "").strip()
    application_name = (beneficiary_application.full_name or "").strip() if beneficiary_application else ""
    display_name = first_name or (application_name.split()[0] if application_name else user.username)

    return {
        "greeting": {
            "name": display_name,
            "date_label": now.strftime("%B %d, %Y"),
        },
        "metrics": {
            "programs_enrolled": len(program_labels),
            "programs_enrolled_meta": ", ".join(program_labels) if program_labels else "None yet",
            "next_pickup": (
                next_pickup.get("date_label")
                or next_pickup.get("datetime")
                or "None scheduled yet"
            ),
            "skills_available": len(skill_topics),
            "skills_new": skills_new,
        },
        "next_pickup": next_pickup,
        "distribution_history": history_items,
        "completed_activities": completed_activity_items,
        "skills": recommended_skills,
        "announcements": announcement_payload,
        "links": {
            "skill_learning": reverse("user_dashboard_skill_learning"),
        },
    }


@login_required(login_url="signin")
@require_POST
def submit_beneficiary_pickup_feedback(request):
    if request.user.is_superuser:
        return JsonResponse({"error": "Only beneficiaries can submit pickup feedback."}, status=403)

    if not _is_active_beneficiary(request.user):
        return JsonResponse({"error": "Only active beneficiaries can submit pickup feedback."}, status=403)

    raw_activity_id = str(request.POST.get("activity_id") or "").strip()

    raw_rating = str(request.POST.get("rating") or "").strip()
    try:
        rating = int(raw_rating)
    except (TypeError, ValueError):
        return JsonResponse({"error": "rating must be an integer from 1 to 5."}, status=400)

    if rating < 1 or rating > 5:
        return JsonResponse({"error": "rating must be between 1 and 5."}, status=400)

    comment = str(request.POST.get("comment") or "").strip()
    if raw_activity_id:
        try:
            activity_id = int(raw_activity_id)
        except (TypeError, ValueError):
            return JsonResponse({"error": "activity_id must be a valid activity."}, status=400)

        activity = get_object_or_404(Activity, id=activity_id, status=Activity.STATUS_COMPLETED)
        beneficiary_application = (
            RoleApplication.objects
            .filter(user=request.user, role=RoleApplication.ROLE_BENEFICIARY, status=RoleApplication.STATUS_APPROVED)
            .order_by("-updated_at", "-id")
            .first()
        )
        if not beneficiary_application:
            return JsonResponse({"error": "An approved beneficiary profile is required."}, status=403)

        if BeneficiaryActivityFeedback.objects.filter(activity=activity, beneficiary=beneficiary_application).exists():
            return JsonResponse({"error": "Feedback has already been submitted for this activity."}, status=409)
        feedback = BeneficiaryActivityFeedback.objects.create(
            activity=activity,
            beneficiary=beneficiary_application,
            user=request.user,
            rating=rating,
            comment=comment,
        )
        created = True
        return JsonResponse({
            "message": "Feedback saved.",
            "created": created,
            "feedback": {
                "rating": int(feedback.rating),
                "comment": (feedback.comment or "").strip(),
                "submittedBy": _display_name_for_user(request.user),
                "ratingLabel": "★" * int(feedback.rating) + "☆" * (5 - int(feedback.rating)),
            },
        })

    raw_id = str(request.POST.get("assistance_record_id") or request.POST.get("assistanceId") or "").strip()
    try:
        assistance_id = int(raw_id)
    except (TypeError, ValueError):
        return JsonResponse({"error": "assistance_record_id is required."}, status=400)

    try:
        record = BeneficiaryAssistanceRecord.objects.select_related("beneficiary", "beneficiary__user").get(id=assistance_id)
    except BeneficiaryAssistanceRecord.DoesNotExist:
        return JsonResponse({"error": "Assistance record was not found."}, status=404)

    if record.beneficiary.user_id != request.user.id:
        return JsonResponse({"error": "Feedback can only be submitted for your own assistance record."}, status=403)

    if BeneficiaryAssistanceFeedback.objects.filter(assistance_record=record).exists():
        return JsonResponse({"error": "Feedback has already been submitted for this assistance event."}, status=409)
    feedback = BeneficiaryAssistanceFeedback.objects.create(
        assistance_record=record,
        beneficiary=record.beneficiary,
        user=request.user,
        rating=rating,
        comment=comment,
    )
    created = True

    return JsonResponse({
        "message": "Feedback saved.",
        "created": created,
        "feedback": {
            "rating": int(feedback.rating),
            "comment": (feedback.comment or "").strip(),
            "submittedBy": _display_name_for_user(request.user),
            "ratingLabel": "★" * int(feedback.rating) + "☆" * (5 - int(feedback.rating)),
        },
    })


@login_required(login_url="signin")
@require_GET
def user_dashboard_overview_api(request):
    if request.user.is_superuser:
        return JsonResponse({"error": "Only beneficiaries can access this endpoint."}, status=403)

    if not _is_active_beneficiary(request.user):
        return JsonResponse({"error": "Only beneficiaries can access this endpoint."}, status=403)

    return JsonResponse(_build_user_dashboard_overview_payload(request.user))


def format_ojt_duration_display(hours_value):
    total_minutes = round(float(hours_value or 0) * 60)
    if total_minutes < 0:
        sign = "-"
        total_minutes = abs(total_minutes)
    else:
        sign = ""

    whole_hours, minutes = divmod(total_minutes, 60)
    if minutes:
        return f"{sign}{whole_hours} hr {minutes} min"
    return f"{sign}{whole_hours} hr"


def _build_volunteer_dashboard_payload(user):
    profile = _get_or_create_user_profile(user)
    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    assignments_qs = VolunteerActivityAssignment.objects.filter(
        volunteer=user,
        activity__isnull=False,
    ).select_related("assigned_by")
    total_tasks = assignments_qs.count()
    pending_this_week = assignments_qs.filter(
        scheduled_date__range=(week_start, week_end),
    ).exclude(
        status__in=[
            VolunteerActivityAssignment.STATUS_COMPLETED,
            VolunteerActivityAssignment.STATUS_MISSED,
            VolunteerActivityAssignment.STATUS_CANCELLED,
        ],
    ).count()

    active_assignment = assignments_qs.filter(
        status__in=[
            VolunteerActivityAssignment.STATUS_TIME_IN,
            VolunteerActivityAssignment.STATUS_IN_PROGRESS,
        ],
    ).order_by("attendance_started_at", "id").first()

    future_assignments = list(
        assignments_qs.filter(
            scheduled_date__gte=today,
        ).exclude(
            status__in=[
                VolunteerActivityAssignment.STATUS_COMPLETED,
                VolunteerActivityAssignment.STATUS_MISSED,
                VolunteerActivityAssignment.STATUS_CANCELLED,
            ],
        ).order_by("scheduled_date", "scheduled_time", "id")[:3]
    )

    upcoming_tasks = []
    for assignment in future_assignments:
        schedule_date = assignment.scheduled_date
        task_date = timezone.localtime(timezone.now()).date()
        is_today = schedule_date == task_date
        upcoming_tasks.append({
            "id": int(assignment.id),
            "title": assignment.activity_name or "Volunteer activity",
            "location": assignment.location or "TBA",
            "schedule_label": assignment.scheduled_date.strftime("%b %d, %Y") + (f" · {assignment.scheduled_time.strftime('%I:%M %p').lstrip('0') }" if assignment.scheduled_time else ""),
            "is_today": is_today,
        })

    valid_check_in_assignments = assignments_qs.exclude(
        status__in=[
            VolunteerActivityAssignment.STATUS_COMPLETED,
            VolunteerActivityAssignment.STATUS_MISSED,
            VolunteerActivityAssignment.STATUS_CANCELLED,
        ],
    )

    next_check_in = valid_check_in_assignments.filter(
        scheduled_date__gte=today,
    ).order_by("scheduled_date", "scheduled_time", "id").first()
    if next_check_in is None and valid_check_in_assignments.exists():
        next_check_in = valid_check_in_assignments.order_by("-scheduled_date", "-scheduled_time", "-id").first()

    if active_assignment:
        active_timestamp = active_assignment.attendance_started_at or timezone.now()
        active_assignment_payload = {
            "id": int(active_assignment.id),
            "activity_name": active_assignment.activity_name or "Volunteer activity",
            "location": active_assignment.location or "TBA",
            "time_in": active_timestamp.isoformat(),
            "time_in_label": timezone.localtime(active_timestamp).strftime("%I:%M %p"),
            "started_ms": int(timezone.localtime(active_timestamp).timestamp() * 1000),
        }
    else:
        active_assignment_payload = None

    announcements = list(
        CommunityPost.objects.filter(post_type="announcements")
        .filter(_visible_activity_announcement_filter(user))
        .select_related("user")
        .order_by("-created_at", "-id")[:3]
    )
    announcement_payload = []
    for post in announcements:
        announcement_payload.append({
            "id": str(post.id),
            "title": (post.content or "").strip().splitlines()[0][:180] if (post.content or "").strip() else "Announcement",
            "date_label": timezone.localtime(post.created_at).strftime("%b %d, %Y"),
        })

    content_topics_count = SkillLearningTopic.objects.count()
    content_materials_total = SkillLearningMaterial.objects.count()

    ojt_hours = float(profile.ojt_hours or 0)
    required_ojt_hours = float(profile.required_ojt_hours or 80)
    ojt_progress = min(100, max(0, round((ojt_hours / required_ojt_hours) * 100, 1))) if required_ojt_hours else 0
    if ojt_hours <= 0:
        ojt_status_label = "Not started"
    elif ojt_hours >= required_ojt_hours:
        ojt_status_label = "Completed"
    else:
        ojt_status_label = "In progress"

    supervisor_name = profile.ojt_supervisor or "Program lead"
    if not profile.ojt_supervisor and getattr(profile, "assigned_chapter_area", None):
        supervisor_name = profile.assigned_chapter_area
    elif active_assignment and active_assignment.assigned_by_id:
        supervisor_name = _display_name_for_user(active_assignment.assigned_by) or "Program lead"

    next_check_in_label = "No upcoming check-in"
    if profile.ojt_next_check_in:
        next_check_in_label = profile.ojt_next_check_in.strftime("%b %d, %Y")
    elif next_check_in:
        next_check_in_label = next_check_in.scheduled_date.strftime("%b %d, %Y")

    ojt_hours_display = format_ojt_duration_display(ojt_hours)
    ojt_required_hours_display = format_ojt_duration_display(required_ojt_hours)
    ojt_remaining_hours = max(0, required_ojt_hours - ojt_hours)
    ojt_remaining_display = "Required hours completed" if ojt_remaining_hours <= 0 else f"{format_ojt_duration_display(ojt_remaining_hours)} remaining"

    return {
        "current_date": timezone.localdate().strftime("%B %d, %Y"),
        "ojt_hours": ojt_hours,
        "ojt_hours_display": ojt_hours_display,
        "ojt_hours_required": required_ojt_hours,
        "ojt_required_hours_display": ojt_required_hours_display,
        "ojt_remaining_display": ojt_remaining_display,
        "ojt_progress_percent": ojt_progress,
        "ojt_status_label": ojt_status_label,
        "tasks_assigned": total_tasks,
        "tasks_pending_this_week": pending_this_week,
        "content_topics_count": content_topics_count,
        "content_materials_total": content_materials_total,
        "supervisor_name": supervisor_name,
        "ojt_program": profile.ojt_program or (profile.volunteer_role or "Volunteer program"),
        "next_check_in_label": next_check_in_label,
        "upcoming_tasks": upcoming_tasks,
        "announcements": announcement_payload,
        "certificates": [
            {
                "id": certificate.id,
                "recipient_name": certificate.recipient_name,
                "issued_date": timezone.localtime(certificate.issued_at).strftime("%B %d, %Y"),
                "download_url": reverse("volunteer_certificate_download", args=[certificate.id]),
            }
            for certificate in VolunteerCertificate.objects.filter(volunteer=user)
        ],
        "active_assignment": active_assignment_payload,
    }


@login_required(login_url="signin")
def volunteer_dashboard(request):
    if request.user.is_superuser:
        return redirect("admin_dashboard")

    profile = _get_or_create_user_profile(request.user)
    if not _is_active_volunteer(request.user):
        return redirect("home")

    from django.utils.formats import date_format
    current_date = date_format(timezone.now(), format='F j, Y')
    payload = _build_volunteer_dashboard_payload(request.user)
    payload.update({
        "active_page": "dashboard",
        "dashboard_scope": "volunteer",
        "current_date": current_date,
    })

    return render(request, "volunteer_dashboard/dashboard_volunteer.html", payload)


@login_required(login_url="signin")
@require_GET
def volunteer_certificate_download(request, certificate_id):
    certificate = get_object_or_404(VolunteerCertificate, pk=certificate_id)
    if not request.user.is_superuser and certificate.volunteer_id != request.user.id:
        raise Http404

    if certificate.pdf_file:
        return FileResponse(
            certificate.pdf_file.open("rb"),
            as_attachment=True,
            filename="Certificate_of_Appreciation_{}.pdf".format("_".join(certificate.recipient_name.split())),
            content_type="application/pdf",
        )

    def pdf_text(value):
        return str(value).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    lines = [
        "CERTIFICATE OF APPRECIATION",
        "",
        "This certificate is proudly presented to",
        certificate.recipient_name,
        "",
        *certificate.reason.splitlines(),
        "",
        "HappYness Project",
    ]
    commands = ["BT", "/F1 22 Tf", "190 520 Td", f"({pdf_text(lines[0])}) Tj", "/F1 12 Tf", "0 -55 Td"]
    for index, line in enumerate(lines[1:]):
        if index == 2:
            commands.append("/F1 18 Tf")
        commands.append(f"({pdf_text(line[:120])}) Tj")
        commands.append("0 -22 Td")
    commands.append("ET")
    content = "\n".join(commands).encode("latin-1", "replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 792 612] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(content)).encode("ascii") + b" >>\nstream\n" + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    pdf_parts = [b"%PDF-1.4\n"]
    offsets = [0]
    for object_id, body in enumerate(objects, start=1):
        offsets.append(sum(len(part) for part in pdf_parts))
        pdf_parts.extend([f"{object_id} 0 obj\n".encode("ascii"), body, b"\nendobj\n"])
    xref_offset = sum(len(part) for part in pdf_parts)
    pdf_parts.append(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("ascii"))
    pdf_parts.extend(f"{offset:010d} 00000 n \n".encode("ascii") for offset in offsets[1:])
    pdf_parts.append(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode("ascii"))
    buffer = io.BytesIO(b"".join(pdf_parts))
    filename = "Certificate_of_Appreciation_{}.pdf".format("_".join(certificate.recipient_name.split()))
    return FileResponse(buffer, as_attachment=True, filename=filename, content_type="application/pdf")


@login_required(login_url="signin")
@require_POST
def admin_certificate_create(request):
    if not request.user.is_superuser:
        return JsonResponse({"error": "Only admins can issue certificates."}, status=403)

    if request.content_type.startswith("multipart/form-data"):
        volunteer_id = request.POST.get("volunteer_id")
        recipient_name = str(request.POST.get("recipient_name") or "").strip()
        reason = str(request.POST.get("reason") or "").strip()
        pdf_file = request.FILES.get("pdf_file")
    else:
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except (TypeError, ValueError, UnicodeDecodeError):
            return JsonResponse({"error": "Invalid certificate request."}, status=400)
        volunteer_id = payload.get("volunteer_id")
        recipient_name = str(payload.get("recipient_name") or "").strip()
        reason = str(payload.get("reason") or "").strip()
        pdf_file = None
    volunteer = get_object_or_404(User, pk=volunteer_id)
    if not _is_active_volunteer(volunteer):
        return JsonResponse({"error": "Only active volunteers can receive certificates."}, status=400)
    if not recipient_name or not reason:
        return JsonResponse({"error": "Volunteer name and certificate body are required."}, status=400)

    certificate = VolunteerCertificate.objects.create(
        volunteer=volunteer,
        issued_by=request.user,
        recipient_name=recipient_name,
        reason=reason,
        pdf_file=pdf_file,
    )
    return JsonResponse({
        "certificate": {
            "id": certificate.id,
            "download_url": reverse("volunteer_certificate_download", args=[certificate.id]),
        },
    }, status=201)


@login_required(login_url="signin")
@require_POST
def admin_certificate_delete(request, certificate_id):
    if not request.user.is_superuser:
        return JsonResponse({"error": "Only admins can remove certificates."}, status=403)

    certificate = get_object_or_404(VolunteerCertificate, pk=certificate_id)
    if certificate.pdf_file:
        certificate.pdf_file.delete(save=False)
    certificate.delete()
    return JsonResponse({"message": "Certificate removed."})


@login_required(login_url="signin")
def user_dashboard_community(request):
    if request.user.is_superuser:
        return redirect("admin_dashboard")

    profile = _get_or_create_user_profile(request.user)
    if profile.account_role == UserProfile.ROLE_VOLUNTEER:
        return redirect("volunteer_dashboard_community")
    if not _is_active_beneficiary(request.user):
        return redirect("home")

    _ensure_single_user_and_volunteer_community_templates()

    return render(request, "user_dashboard/user_community_user.html", {
        "active_page": "community",
        "dashboard_scope": "beneficiary",
    })


@login_required(login_url="signin")
def user_dashboard_settings(request):
    if request.user.is_superuser:
        return redirect("admin_dashboard")

    profile = _get_or_create_user_profile(request.user)
    if profile.account_role == UserProfile.ROLE_VOLUNTEER:
        return redirect("volunteer_dashboard_settings")
    if not _is_active_beneficiary(request.user):
        return redirect("home")

    return render(request, "user_dashboard/settings_user.html", {
        "active_page": "settings",
        "dashboard_scope": "beneficiary",
        "profile": profile,
        "settings_state": profile.settings_state or {},
    })


@login_required(login_url="signin")
def user_dashboard_skill_learning(request):
    if request.user.is_superuser:
        return redirect("admin_dashboard")

    profile = _get_or_create_user_profile(request.user)
    if profile.account_role == UserProfile.ROLE_VOLUNTEER:
        return redirect("volunteer_dashboard_skill_learning")
    if not _is_active_beneficiary(request.user):
        return redirect("home")

    _ensure_skill_learning_content()

    return render(request, "user_dashboard/skill_learning_user.html", {
        "active_page": "skill_learning",
        "dashboard_scope": "beneficiary",
        "skill_learning_payload": _skill_learning_payload(request.user),
        "skill_learning_api_base": reverse("volunteer_dashboard_skill_learning"),
    })


@login_required(login_url="signin")
def volunteer_dashboard_community(request):
    if request.user.is_superuser:
        return redirect("admin_dashboard")

    if not _is_active_volunteer(request.user):
        return redirect("home")

    _ensure_single_user_and_volunteer_community_templates()

    return render(request, "volunteer_dashboard/community_volunteer.html", {
        "active_page": "community",
        "dashboard_scope": "volunteer",
    })


@login_required(login_url="signin")
def volunteer_dashboard_tasks_ojt(request):
    if request.user.is_superuser:
        return redirect("admin_dashboard")

    if not _is_active_volunteer(request.user):
        return redirect("home")

    # Placeholder view: template includes client-side hooks for real data integration.
    return render(request, "volunteer_dashboard/tasks_ojt_volunteer.html", {
        "active_page": "tasks_ojt",
        "dashboard_scope": "volunteer",
    })
    
@login_required(login_url="signin")
def volunteer_beneficiary_attendance_page(request):
    if request.user.is_superuser:
        return redirect("home")

    profile = _get_or_create_user_profile(request.user)
    if profile.account_role != UserProfile.ROLE_VOLUNTEER:
        return redirect("home")

    activity_id = str(request.GET.get("activity_id") or request.GET.get("activityId") or "").strip()
    try:
        activity_id = int(activity_id)
    except (TypeError, ValueError):
        return redirect("volunteer_dashboard_tasks_ojt")
    assignment = VolunteerActivityAssignment.objects.filter(
        volunteer=request.user,
        activity_id=activity_id,
    ).select_related("activity").first()
    if assignment is None:
        return redirect("volunteer_dashboard_tasks_ojt")

    return render(request, "volunteer_dashboard/beneficiary_attendance.html", {
        "active_page": "tasks_ojt",
        "dashboard_scope": "volunteer",
        "assignment_payload": _serialize_volunteer_activity_assignment(assignment),
    })


@login_required(login_url="signin")
@require_GET
def volunteer_assigned_activities_api(request):
    if request.user.is_superuser:
        return JsonResponse({"error": "Only volunteers can access this endpoint."}, status=403)

    profile = _get_or_create_user_profile(request.user)
    if profile.account_role != UserProfile.ROLE_VOLUNTEER:
        return JsonResponse({"error": "Only volunteers can access this endpoint."}, status=403)

    assignments = VolunteerActivityAssignment.objects.filter(
        volunteer=request.user,
    ).filter(
        Q(activity__isnull=False)
        | Q(status=VolunteerActivityAssignment.STATUS_COMPLETED)
        | Q(attendance_records__status=VolunteerAttendanceRecord.STATUS_CONFIRMED)
    ).distinct().order_by(
        "scheduled_date",
        "scheduled_time",
        "id",
    )
    attendance_records = list(
        VolunteerAttendanceRecord.objects
        .filter(volunteer=request.user)
        .select_related("reviewed_by", "assignment")
    )
    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    pending_minutes = sum(
        int(record.duration_minutes or 0)
        for record in attendance_records
        if record.status == VolunteerAttendanceRecord.STATUS_PENDING
    )
    week_minutes = 0
    for record in attendance_records:
        record_date = record.duty_date or (record.assignment.scheduled_date if record.assignment_id else None)
        if record.status in {VolunteerAttendanceRecord.STATUS_CONFIRMED, VolunteerAttendanceRecord.STATUS_PENDING} and record_date and week_start <= record_date <= week_end:
            week_minutes += int(record.duration_minutes or 0)

    return JsonResponse({
        "items": [_serialize_volunteer_activity_assignment(assignment) for assignment in assignments],
        "ojt_hours": float(profile.ojt_hours or 0),
        "ojt_hours_required": float(profile.required_ojt_hours or 80),
        "ojt_pending_hours": round(pending_minutes / 60, 2),
        "ojt_this_week_hours": round(week_minutes / 60, 2),
        "ojt_supervisor": profile.ojt_supervisor or "Program lead",
        "ojt_program": profile.ojt_program or (profile.volunteer_role or "Volunteer program"),
        "ojt_next_check_in": profile.ojt_next_check_in.isoformat() if profile.ojt_next_check_in else "",
        "attendance": [
            _serialize_volunteer_attendance(attendance)
            for attendance in attendance_records
        ],
    })


@login_required(login_url="signin")
@require_GET
def volunteer_activity_calendar_api(request):
    if request.user.is_superuser:
        return JsonResponse({"error": "Only volunteers can access this endpoint."}, status=403)

    profile = _get_or_create_user_profile(request.user)
    if profile.account_role != UserProfile.ROLE_VOLUNTEER:
        return JsonResponse({"error": "Only volunteers can access this endpoint."}, status=403)

    month_value = str(request.GET.get("month") or timezone.localdate().strftime("%Y-%m"))
    try:
        parsed_month = datetime.strptime(month_value, "%Y-%m").date()
    except ValueError:
        return JsonResponse({"error": "month must use YYYY-MM format."}, status=400)
    month_start = parsed_month.replace(day=1)
    month_end = parsed_month.replace(day=calendar.monthrange(parsed_month.year, parsed_month.month)[1])
    now = timezone.localtime(timezone.now())

    _auto_close_expired_duty_sessions(request.user, now=now)

    assignments = list(
        VolunteerActivityAssignment.objects.filter(
            volunteer=request.user,
            scheduled_date__range=(month_start, month_end),
        ).exclude(
            status=VolunteerActivityAssignment.STATUS_CANCELLED,
        ).select_related("activity").order_by("scheduled_date", "scheduled_time", "id")
    )
    assigned_activity_ids = {assignment.activity_id for assignment in assignments if assignment.activity_id}
    assigned_items = []
    assignments_by_date = {}
    for assignment in assignments:
        activity = assignment.activity
        assignments_by_date.setdefault(assignment.scheduled_date, []).append(assignment)
        scheduled_time = assignment.scheduled_time or (activity.start_time if activity else None)
        assigned_items.append({
            "id": int(activity.id) if activity else int(assignment.id),
            "assignment_id": int(assignment.id),
            "title": (activity.title if activity else assignment.activity_name) or "Volunteer activity",
            "date": assignment.scheduled_date.isoformat(),
            "time": scheduled_time.strftime("%H:%M") if scheduled_time else "",
            "end_time": activity.end_time.strftime("%H:%M") if activity and activity.end_time else "",
            "location": assignment.location or (activity.location if activity else "") or "TBA",
            "category": activity.get_category_display() if activity else (assignment.activity_type or "Assigned task"),
            "type": "assigned",
            "status": assignment.status,
        })

    open_activities = Activity.objects.filter(
        status=Activity.STATUS_ACTIVE,
        date__range=(month_start, month_end),
    ).exclude(id__in=assigned_activity_ids).order_by("date", "start_time", "title")
    open_items = [
        {
            "id": int(activity.id),
            "assignment_id": None,
            "title": activity.title,
            "date": activity.date.isoformat(),
            "time": activity.start_time.strftime("%H:%M") if activity.start_time else "",
            "end_time": activity.end_time.strftime("%H:%M") if activity.end_time else "",
            "location": activity.location or "TBA",
            "category": activity.get_category_display() or "Uncategorized",
            "type": "open",
            "status": "upcoming",
        }
        for activity in open_activities
    ]

    schedules = list(
        VolunteerOjtSchedule.objects.filter(
            volunteer=request.user,
            effective_from__lte=month_end,
        ).filter(
            Q(effective_until__isnull=True) | Q(effective_until__gte=month_start),
        ).order_by("effective_from", "id")
    )
    attendance_records = list(
        VolunteerAttendanceRecord.objects.filter(volunteer=request.user).filter(
            Q(duty_date__range=(month_start, month_end))
            | Q(assignment__scheduled_date__range=(month_start, month_end)),
        ).select_related("assignment").order_by("time_in", "id")
    )
    attendance_by_date = {}
    for record in attendance_records:
        record_date = record.duty_date or (record.assignment.scheduled_date if record.assignment_id else None)
        if record_date:
            attendance_by_date.setdefault(record_date, []).append(record)

    duty_days = []
    cursor = month_start
    while cursor <= month_end:
        schedule = next((
            item for item in reversed(schedules)
            if item.effective_from <= cursor and (item.effective_until is None or item.effective_until >= cursor)
        ), None)
        day_payload = _ojt_duty_day_payload(
            cursor,
            schedule,
            attendance_by_date.get(cursor, []),
            assignments_by_date.get(cursor, []),
            now,
        )
        if day_payload:
            duty_days.append(day_payload)
        cursor += timedelta(days=1)

    summary_schedule_rows = list(
        VolunteerOjtSchedule.objects.filter(
            volunteer=request.user,
            effective_from__lte=timezone.localdate() + timedelta(days=366),
        ).order_by("effective_from", "id")
    )

    def schedule_for_summary_date(duty_date):
        return next((
            item for item in reversed(summary_schedule_rows)
            if item.effective_from <= duty_date and (item.effective_until is None or item.effective_until >= duty_date)
        ), None)

    today = timezone.localdate()
    current_schedule = schedule_for_summary_date(today)
    summary_schedule = current_schedule
    recent_candidates = []
    cursor = today
    while cursor >= today - timedelta(days=366) and len(recent_candidates) < 7:
        schedule = schedule_for_summary_date(cursor)
        if _ojt_is_duty_date(schedule, cursor):
            recent_candidates.append((cursor, schedule))
        cursor -= timedelta(days=1)

    next_duty_date = None
    cursor = today + timedelta(days=1)
    while cursor <= today + timedelta(days=366):
        schedule = schedule_for_summary_date(cursor)
        if _ojt_is_duty_date(schedule, cursor):
            next_duty_date = cursor
            break
        cursor += timedelta(days=1)
    if not summary_schedule and next_duty_date:
        summary_schedule = schedule_for_summary_date(next_duty_date)

    summary_dates = [duty_date for duty_date, _ in recent_candidates]
    summary_records_by_date = {}
    summary_assignments_by_date = {}
    if summary_dates:
        summary_records = VolunteerAttendanceRecord.objects.filter(volunteer=request.user).filter(
            Q(duty_date__in=summary_dates) | Q(assignment__scheduled_date__in=summary_dates),
        ).select_related("assignment").order_by("time_in", "id")
        for record in summary_records:
            record_date = record.duty_date or (record.assignment.scheduled_date if record.assignment_id else None)
            if record_date:
                summary_records_by_date.setdefault(record_date, []).append(record)
        summary_assignments = VolunteerActivityAssignment.objects.filter(
            volunteer=request.user,
            scheduled_date__in=summary_dates,
        ).exclude(status=VolunteerActivityAssignment.STATUS_CANCELLED).order_by("scheduled_date", "scheduled_time", "id")
        for assignment in summary_assignments:
            summary_assignments_by_date.setdefault(assignment.scheduled_date, []).append(assignment)

    recent_duty_days = []
    today_duty = None
    for duty_date, schedule in recent_candidates:
        day_payload = _ojt_duty_day_payload(
            duty_date,
            schedule,
            summary_records_by_date.get(duty_date, []),
            summary_assignments_by_date.get(duty_date, []),
            now,
        )
        if duty_date == today:
            today_duty = day_payload
        if day_payload and day_payload["status"] != "upcoming":
            recent_duty_days.append(day_payload)
        if len(recent_duty_days) >= 6:
            break

    return JsonResponse({
        "month": month_start.strftime("%Y-%m"),
        "items": assigned_items + open_items,
        "assigned_items": assigned_items,
        "open_items": open_items,
        "duty_days": duty_days,
        "schedule_weekdays": sorted({int(day) for day in (summary_schedule.weekdays or []) if str(day).isdigit()}) if summary_schedule else [],
        "has_schedule": bool(summary_schedule),
        "schedule_effective_from": summary_schedule.effective_from.isoformat() if summary_schedule else "",
        "today_duty": today_duty,
        "next_duty_date": next_duty_date.isoformat() if next_duty_date else "",
        "recent_duty_days": recent_duty_days[:5],
        "has_more_duty_days": len(recent_duty_days) > 5,
    })


@login_required(login_url="signin")
def export_volunteer_completed_pdf(request):
    if request.user.is_superuser:
        return redirect("admin_dashboard")

    profile = _get_or_create_user_profile(request.user)
    if profile.account_role != UserProfile.ROLE_VOLUNTEER:
        return redirect("home")

    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    attendance_records = VolunteerAttendanceRecord.objects.filter(
        volunteer=request.user,
        status=VolunteerAttendanceRecord.STATUS_CONFIRMED,
    ).select_related("assignment").order_by("-time_out", "-time_in", "-id")

    data = [["Task", "Date", "Location", "Time In", "Time Out", "Duration", "Status"]]
    for record in attendance_records:
        assignment = record.assignment
        data.append([
            assignment.activity_name or "Activity",
            assignment.scheduled_date.strftime("%b %d, %Y"),
            assignment.location or "TBA",
            timezone.localtime(record.time_in).strftime("%I:%M %p").lstrip("0") if record.time_in else "-",
            timezone.localtime(record.time_out).strftime("%I:%M %p").lstrip("0") if record.time_out else "-",
            f"{(record.duration_minutes or 0) / 60:.2f} hrs",
            "Confirmed",
        ])

    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
        leftMargin=0.4 * inch,
        rightMargin=0.4 * inch,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "VolunteerCompletedTitle",
        parent=styles["Heading1"],
        fontSize=16,
        textColor=colors.HexColor("#14352d"),
        spaceAfter=6,
        alignment=TA_CENTER,
    )
    subtitle_style = ParagraphStyle(
        "VolunteerCompletedSubtitle",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#56766c"),
        spaceAfter=12,
        alignment=TA_CENTER,
    )
    elements = [
        Paragraph("Completed Attendance Report", title_style),
        Paragraph(request.user.get_full_name() or request.user.username, subtitle_style),
        Spacer(1, 0.1 * inch),
    ]
    table = Table(data, colWidths=[1.65 * inch, 0.9 * inch, 1.1 * inch, 0.75 * inch, 0.75 * inch, 0.7 * inch, 0.75 * inch], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#edf8f3")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#14352d")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("FONTSIZE", (0, 1), (-1, -1), 7.5),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c9ddd6")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fdfb")]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(table)
    document.build(elements)
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="completed-attendance.pdf"'
    return response


@login_required(login_url="signin")
def admin_resource_library(request):
    if not request.user.is_superuser:
        return redirect("user_dashboard")

    resources = ResourceLibraryMaterial.objects.all()
    editing_resource = None
    original_file_name = ""
    original_file_storage = None
    if request.method == "POST":
        action = request.POST.get("action", "create")
        if action in {"toggle", "delete"}:
            resource = get_object_or_404(ResourceLibraryMaterial, pk=request.POST.get("resource_id"))
            if action == "delete":
                resource.delete()
            else:
                resource.is_published = not resource.is_published
                resource.save(update_fields=["is_published", "updated_at"])
            return redirect("admin_resource_library")

        if action == "update":
            editing_resource = get_object_or_404(ResourceLibraryMaterial, pk=request.POST.get("resource_id"))
            if editing_resource.file_upload:
                original_file_name = editing_resource.file_upload.name
                original_file_storage = editing_resource.file_upload.storage
                if request.POST.get("remove_current_file") == "on" and not request.FILES.get("file_upload"):
                    editing_resource.file_upload = None
        form = ResourceLibraryMaterialForm(
            request.POST,
            request.FILES,
            instance=editing_resource,
        )
        if form.is_valid():
            saved_resource = form.save()
            current_file_name = saved_resource.file_upload.name if saved_resource.file_upload else ""
            if original_file_name and original_file_name != current_file_name:
                original_file_storage.delete(original_file_name)
            return redirect("admin_resource_library")
    else:
        form = ResourceLibraryMaterialForm()

    return render(request, "admin_dashboard/resource_library_admin.html", {
        "active_page": "admin_resource_library",
        "dashboard_scope": "admin",
        "resources": resources,
        "resource_form": form,
        "editing_resource": editing_resource,
        "editing_resource_file_name": original_file_name,
    })


def volunteer_dashboard_resource_library(request):
    if request.user.is_superuser:
        return redirect("admin_dashboard")

    if not _is_active_volunteer(request.user):
        return redirect("home")

    return render(request, "volunteer_dashboard/resource_library_volunteer.html", {
        "active_page": "resource_library",
        "dashboard_scope": "volunteer",
        "resource_library_materials": ResourceLibraryMaterial.objects.filter(is_published=True),
    })


@login_required(login_url="signin")
@require_GET
def volunteer_resource_library_pdf_preview(request, material_id):
    material = get_object_or_404(ResourceLibraryMaterial, pk=material_id)
    if not request.user.is_superuser and (not _is_active_volunteer(request.user) or not material.is_published):
        raise Http404
    if material.preview_kind != "pdf" or not material.file_upload:
        raise Http404

    try:
        pdf_file = material.file_upload.open("rb")
    except (OSError, ValueError):
        raise Http404

    response = FileResponse(
        pdf_file,
        content_type="application/pdf",
        as_attachment=False,
        filename=os.path.basename(material.file_upload.name),
    )
    response["X-Frame-Options"] = "SAMEORIGIN"
    return response


@login_required(login_url="signin")
def volunteer_dashboard_settings(request):
    if request.user.is_superuser:
        return redirect("admin_dashboard")

    if not _is_active_volunteer(request.user):
        return redirect("home")

    profile = _get_or_create_user_profile(request.user)

    return render(request, "volunteer_dashboard/settings_volunteer.html", {
        "active_page": "settings",
        "dashboard_scope": "volunteer",
        "profile": profile,
        "settings_state": profile.settings_state or {},
    })


@login_required(login_url="signin")
@require_POST
def dashboard_profile_update(request):
    if not _has_dashboard_access(request.user):
        return JsonResponse({"error": "Only active dashboard users can update this profile."}, status=403)

    profile = _get_or_create_user_profile(request.user)

    full_name = str(request.POST.get("full_name", "") or "").strip()
    first_name = str(request.POST.get("first_name", "") or "").strip()
    last_name = str(request.POST.get("last_name", "") or "").strip()

    if full_name and not (first_name or last_name):
        parts = full_name.split()
        first_name = parts[0] if parts else ""
        last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

    avatar = request.FILES.get("profile_photo")
    if avatar:
        avatar_content_type = str(getattr(avatar, "content_type", "") or "").lower()
        avatar_name = str(getattr(avatar, "name", "") or "")
        if not avatar_content_type.startswith("image/"):
            return JsonResponse({"error": "Profile photo must be an image file."}, status=400)
        if (getattr(avatar, "size", 0) or 0) > PROFILE_AVATAR_MAX_SIZE:
            return JsonResponse({"error": "Profile photo must be 5MB or smaller."}, status=400)
        extension = avatar_name.rsplit(".", 1)[-1].lower() if "." in avatar_name else ""
        if extension not in {"jpg", "jpeg", "png", "gif", "webp"}:
            return JsonResponse({"error": "Supported avatar formats: JPG, PNG, GIF, WEBP."}, status=400)

    with transaction.atomic():
        request.user.first_name = first_name
        request.user.last_name = last_name
        request.user.email = str(request.POST.get("email", "") or "").strip()
        request.user.save(update_fields=["first_name", "last_name", "email"])

        profile.phone = str(request.POST.get("phone", "") or "").strip()
        profile.birthdate = str(request.POST.get("birthdate", "") or "").strip() or None
        profile.civil_status = str(request.POST.get("civil_status", "") or "").strip()
        profile.address_line = str(request.POST.get("address_line", "") or "").strip()
        profile.barangay = str(request.POST.get("barangay", "") or "").strip()
        profile.city_municipality = str(request.POST.get("city_municipality", "") or "").strip()
        profile.emergency_contact_name = str(request.POST.get("emergency_contact_name", "") or "").strip()
        profile.emergency_contact_relationship = str(request.POST.get("emergency_contact_relationship", "") or "").strip()
        profile.emergency_contact_phone = str(request.POST.get("emergency_contact_phone", "") or "").strip()
        profile.volunteer_role = str(request.POST.get("volunteer_role", "") or "").strip()
        profile.assigned_chapter_area = str(request.POST.get("assigned_chapter_area", "") or "").strip()

        if avatar:
            if profile.avatar:
                profile.avatar.delete(save=False)
            profile.avatar = avatar

        profile.save()

    return JsonResponse(
        {
            "message": "Profile updated successfully.",
            "data": _serialize_profile_payload(request.user, profile),
        }
    )


@login_required(login_url="signin")
@require_POST
def dashboard_settings_state_update(request):
    if request.user.is_superuser:
        return JsonResponse({"error": "Only dashboard users can update settings state."}, status=403)

    if not _has_dashboard_access(request.user):
        return JsonResponse({"error": "Only active dashboard users can update settings state."}, status=403)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid settings payload."}, status=400)

    state = payload.get("state") if isinstance(payload, dict) else None
    if not isinstance(state, dict):
        return JsonResponse({"error": "Settings state must be an object."}, status=400)

    profile = _get_or_create_user_profile(request.user)
    existing_state = profile.settings_state if isinstance(profile.settings_state, dict) else {}
    next_state = dict(existing_state)
    next_state.update(state)

    if not _normalize_notification_setting_value(next_state.get("security_2fa_enabled"), default=False):
        next_state["security_2fa_confirmed"] = False

    profile.settings_state = next_state
    profile.save(update_fields=["settings_state", "updated_at"])

    return JsonResponse({"message": "Settings autosaved."})


@login_required(login_url="signin")
@require_POST
def dashboard_two_factor_setup(request):
    if request.user.is_superuser:
        return JsonResponse({"error": "Only dashboard users can use 2FA setup."}, status=403)

    if not _has_dashboard_access(request.user):
        return JsonResponse({"error": "Only active dashboard users can use 2FA setup."}, status=403)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        payload = {}

    action = str(payload.get("action", "start") or "start").strip().lower()
    profile = _get_or_create_user_profile(request.user)
    current_state = profile.settings_state if isinstance(profile.settings_state, dict) else {}

    if action in {"start", "resend"}:
        started, error_message = start_two_factor_challenge(
            request,
            request.user,
            "setup",
            _settings_url_for_user(request.user),
        )
        if not started:
            return JsonResponse({"error": error_message or "We could not send a verification code right now."}, status=400)

        return JsonResponse({
            "message": "We sent a verification code to your email.",
        })

    if action != "verify":
        return JsonResponse({"error": "Unsupported 2FA action."}, status=400)

    challenge = get_pending_two_factor_challenge(request)
    if not challenge or challenge.get("user_id") != request.user.id or challenge.get("purpose") != "setup":
        return JsonResponse({"error": "Please request a new code."}, status=400)

    verification_code = str(payload.get("verification_code", "") or "").strip()
    if not verification_code:
        return JsonResponse({"error": "Please enter the 6-digit code from your email."}, status=400)

    if is_two_factor_challenge_expired(challenge):
        return JsonResponse({"error": "That code expired. Please request a new one."}, status=400)

    if not is_two_factor_code_valid(challenge, verification_code):
        touch_two_factor_challenge_attempt(request)
        return JsonResponse({"error": "That code was not correct. Please try again or send a new one."}, status=400)

    next_state = dict(current_state)
    next_state["security_2fa_enabled"] = True
    next_state["security_2fa_confirmed"] = True
    profile.settings_state = next_state
    profile.save(update_fields=["settings_state", "updated_at"])
    clear_two_factor_state(request)

    return JsonResponse({
        "message": "Two-factor authentication is now on.",
        "settings_state": next_state,
    })


@login_required(login_url="signin")
@require_GET
def dashboard_community_posts(request):
    if not (request.user.is_superuser or _has_dashboard_access(request.user)):
        return JsonResponse({"error": "Only active dashboard users can access community posts."}, status=403)

    _ensure_community_post_activity_schema()

    offset = _parse_non_negative_int(request.GET.get("offset"), default=0)
    limit = _parse_non_negative_int(request.GET.get("limit"), default=COMMUNITY_POST_PAGE_SIZE)
    if limit <= 0:
        limit = COMMUNITY_POST_PAGE_SIZE
    limit = min(limit, COMMUNITY_POST_PAGE_SIZE)

    visibility_filter = _visible_activity_announcement_filter(request.user)
    base_qs = CommunityPost.objects.filter(visibility_filter)
    total_posts = base_qs.count()

    posts_qs = (
        CommunityPost.objects
        .select_related("user", "activity")
        .prefetch_related("attachments")
        .filter(visibility_filter)
        .annotate(
            likes_total=Count("likes", distinct=True),
            comments_total=Count("comments", distinct=True),
        )
        .order_by("-created_at", "-id")[offset:offset + limit]
    )
    posts = list(posts_qs)

    liked_post_ids = set()
    if posts:
        liked_post_ids = set(
            CommunityPostLike.objects
            .filter(user=request.user, post_id__in=[post.id for post in posts])
            .values_list("post_id", flat=True)
        )

    reported_post_ids = set()
    if posts and request.user.is_authenticated:
        reported_post_ids = set(
            CommunityPostReport.objects
            .filter(reported_by=request.user, post_id__in=[post.id for post in posts])
            .values_list("post_id", flat=True)
        )

    next_offset = offset + len(posts)
    has_more = next_offset < total_posts

    recent_announcement_posts = list(
        CommunityPost.objects
        .filter(
            post_type="announcements",
            created_at__gte=timezone.now() - timedelta(days=30),
        )
        .filter(visibility_filter)
        .order_by("-created_at", "-id")
    )
    upcoming_activities = list(
        Activity.objects
        .filter(date__gte=timezone.localdate(), status=Activity.STATUS_ACTIVE)
        .filter(_visible_activity_filter(request.user))
        .distinct()
        .order_by("date", "start_time", "title")
    )

    return JsonResponse({
        "posts": [_serialize_community_post(post, viewer=request.user, liked_post_ids=liked_post_ids, reported_post_ids=reported_post_ids) for post in posts],
        "hasMore": has_more,
        "nextOffset": next_offset if has_more else None,
        "pageSize": COMMUNITY_POST_PAGE_SIZE,
        "totalPosts": total_posts,
        "sidebar": {
            "announcements": [
                {
                    "id": str(post.id),
                    "title": (post.content or "").strip().splitlines()[0][:180] if (post.content or "").strip() else "Announcement",
                    "body": "\n".join((post.content or "").strip().splitlines()[1:]).strip(),
                    "priority": "New" if post.created_at >= timezone.now() - timedelta(days=7) else "Recent",
                }
                for post in recent_announcement_posts[:3]
            ],
            "announcement_count": len(recent_announcement_posts),
            "events": [
                {
                    "id": str(activity.id),
                    "title": activity.title,
                    "dateTime": _format_activity_schedule_label(activity),
                    "location": (activity.location or "").strip() or "Location to be confirmed",
                    "imageUrl": _activity_image_url(activity),
                    "joined": False,
                    "interestedByUser": False,
                    "interestedCount": int(activity.volunteer_count or 0),
                }
                for activity in upcoming_activities[:3]
            ],
            "event_count": len(upcoming_activities),
        },
    })


@login_required(login_url="signin")
@require_GET
def dashboard_community_post_comments(request, post_id):
    if not (request.user.is_superuser or _has_dashboard_access(request.user)):
        return JsonResponse({"error": "Only active dashboard users can access post comments."}, status=403)

    _ensure_community_post_activity_schema()

    post = get_object_or_404(
        CommunityPost.objects
        .annotate(comments_total=Count("comments", distinct=True)),
        pk=post_id,
    )

    offset = _parse_non_negative_int(request.GET.get("offset"), default=0)
    limit = _parse_non_negative_int(request.GET.get("limit"), default=COMMUNITY_COMMENT_PAGE_SIZE)
    if limit <= 0:
        limit = COMMUNITY_COMMENT_PAGE_SIZE

    comments_payload = _serialize_community_comment_threads(
        post,
        viewer=request.user,
        offset=offset,
        limit=limit,
    )

    return JsonResponse(
        {
            "postId": str(post.id),
            "comments": comments_payload["comments"],
            "hasMore": comments_payload["hasMore"],
            "nextOffset": comments_payload["nextOffset"],
            "commentCount": int(getattr(post, "comments_total", post.comments.count())),
            "pageSize": COMMUNITY_COMMENT_PAGE_SIZE,
        }
    )


@login_required(login_url="signin")
@require_POST
def dashboard_community_post_create(request):
    if not (request.user.is_superuser or _has_dashboard_access(request.user)):
        return JsonResponse({"error": "Only active dashboard users can create posts."}, status=403)

    _ensure_community_post_activity_schema()

    content = str(request.POST.get("content", "") or "").strip()
    if not content:
        return JsonResponse({"error": "Post content is required."}, status=400)

    post_type = str(request.POST.get("type", "discussions") or "discussions").strip().lower()
    if post_type not in {"discussions", "tips", "announcements"}:
        post_type = "discussions"
    elif post_type == "announcements" and not request.user.is_superuser:
        post_type = "discussions"

    try:
        with transaction.atomic():
            created = CommunityPost.objects.create(user=request.user, content=content, post_type=post_type)
            for uploaded_file in request.FILES.getlist("attachments"):
                CommunityPostAttachment.objects.create(post=created, file=uploaded_file)
    except ValidationError as exc:
        message = exc.messages[0] if getattr(exc, "messages", None) else "Unable to upload attachments."
        return JsonResponse({"error": message}, status=400)

    created = CommunityPost.objects.select_related("user").prefetch_related("attachments").get(pk=created.pk)
    return JsonResponse({"message": "Post published.", "post": _serialize_community_post(created, viewer=request.user)}, status=201)


@login_required(login_url="signin")
@require_POST
def dashboard_community_post_like_toggle(request, post_id):
    if not (request.user.is_superuser or _has_dashboard_access(request.user)):
        return JsonResponse({"error": "Only active dashboard users can like posts."}, status=403)

    _ensure_community_post_activity_schema()

    post = get_object_or_404(CommunityPost, pk=post_id)

    like, created = CommunityPostLike.objects.get_or_create(post=post, user=request.user)
    liked = True
    if not created:
        like.delete()
        liked = False
    else:
        _create_community_notification(
            recipient=post.user,
            actor=request.user,
            notification_type=CommunityNotification.TYPE_POST_LIKE,
            post=post,
        )

    return JsonResponse(
        {
            "message": "Post liked." if liked else "Post like removed.",
            "liked": liked,
            "likes": post.likes.count(),
        }
    )


@login_required(login_url="signin")
@require_POST
def dashboard_community_post_comment_create(request, post_id):
    if not (request.user.is_superuser or _has_dashboard_access(request.user)):
        return JsonResponse({"error": "Only active dashboard users can comment on posts."}, status=403)

    _ensure_community_post_activity_schema()

    post = get_object_or_404(CommunityPost, pk=post_id)

    content = str(request.POST.get("content", "") or "").strip()
    if not content:
        return JsonResponse({"error": "Comment content is required."}, status=400)

    created = CommunityPostComment.objects.create(post=post, user=request.user, content=content)
    _create_community_notification(
        recipient=post.user,
        actor=request.user,
        notification_type=CommunityNotification.TYPE_POST_COMMENT,
        post=post,
        comment=created,
    )
    comment_payload = _serialize_community_comment_payload(created, like_total=0, liked=False, viewer=request.user)
    comment_payload["replies"] = []

    return JsonResponse(
        {
            "message": "Comment posted.",
            "comment": comment_payload,
            "commentCount": post.comments.count(),
        },
        status=201,
    )


@login_required(login_url="signin")
@require_POST
def dashboard_community_comment_reply_create(request, post_id, comment_id):
    if not (request.user.is_superuser or _has_dashboard_access(request.user)):
        return JsonResponse({"error": "Only active dashboard users can reply to comments."}, status=403)

    _ensure_community_post_activity_schema()

    post = get_object_or_404(CommunityPost, pk=post_id)
    parent_comment = get_object_or_404(
        CommunityPostComment.objects.select_related("user", "parent", "parent__user"),
        pk=comment_id,
        post=post,
    )

    content = str(request.POST.get("content", "") or "").strip()
    if not content:
        return JsonResponse({"error": "Reply content is required."}, status=400)

    reply = CommunityPostComment.objects.create(
        post=post,
        user=request.user,
        parent=parent_comment,
        content=content,
    )
    _create_community_notification(
        recipient=parent_comment.user,
        actor=request.user,
        notification_type=CommunityNotification.TYPE_COMMENT_REPLY,
        post=post,
        comment=reply,
    )
    reply = CommunityPostComment.objects.select_related("user", "parent", "parent__user").get(pk=reply.pk)

    reply_payload = _serialize_community_comment_payload(reply, like_total=0, liked=False, viewer=request.user)
    reply_targets_reply = bool(reply.parent_id and reply.parent and reply.parent.parent_id)
    reply_payload["replyShowsChain"] = reply_targets_reply
    reply_payload["replyFromAuthor"] = reply_payload["author"] if reply_targets_reply else ""
    reply_payload["replyToAuthor"] = _display_name_for_user(reply.parent.user) if reply_targets_reply else ""

    root_comment = parent_comment
    seen = set()
    while root_comment.parent_id:
        if root_comment.parent_id in seen:
            break
        seen.add(root_comment.parent_id)
        root_comment = root_comment.parent

    return JsonResponse(
        {
            "message": "Reply posted.",
            "reply": reply_payload,
            "rootCommentId": str(root_comment.id),
            "commentCount": post.comments.count(),
        },
        status=201,
    )


@login_required(login_url="signin")
@require_POST
def dashboard_community_comment_update(request, post_id, comment_id):
    if not (request.user.is_superuser or _has_dashboard_access(request.user)):
        return JsonResponse({"error": "Only active dashboard users can edit comments."}, status=403)

    _ensure_community_post_activity_schema()
    post = get_object_or_404(CommunityPost, pk=post_id)
    comment = get_object_or_404(CommunityPostComment, pk=comment_id, post=post)
    if comment.user_id != request.user.id and not request.user.is_staff:
        return JsonResponse({"error": "Only the comment author or an admin can edit this comment."}, status=403)

    content = str(request.POST.get("content", "") or "").strip()
    if not content:
        return JsonResponse({"error": "Comment content is required."}, status=400)
    if len(content) > 280:
        return JsonResponse({"error": "Comments must be 280 characters or fewer."}, status=400)

    comment.content = content
    comment.save(update_fields=["content"])
    return JsonResponse({"message": "Comment updated.", "commentId": str(comment.id), "text": comment.content})


@login_required(login_url="signin")
@require_POST
def dashboard_community_comment_delete(request, post_id, comment_id):
    if not (request.user.is_superuser or _has_dashboard_access(request.user)):
        return JsonResponse({"error": "Only active dashboard users can delete comments."}, status=403)

    _ensure_community_post_activity_schema()
    post = get_object_or_404(CommunityPost, pk=post_id)
    comment = get_object_or_404(CommunityPostComment, pk=comment_id, post=post)
    if comment.user_id != request.user.id and not request.user.is_staff:
        return JsonResponse({"error": "Only the comment author or an admin can delete this comment."}, status=403)

    comment.delete()
    return JsonResponse({"message": "Comment deleted.", "commentId": str(comment_id), "commentCount": post.comments.count()})


@login_required(login_url="signin")
@require_POST
def dashboard_community_comment_like_toggle(request, post_id, comment_id):
    if not (request.user.is_superuser or _has_dashboard_access(request.user)):
        return JsonResponse({"error": "Only active dashboard users can like comments."}, status=403)

    _ensure_community_post_activity_schema()

    post = get_object_or_404(CommunityPost, pk=post_id)
    comment = get_object_or_404(CommunityPostComment, pk=comment_id, post=post)

    like, created = CommunityPostCommentLike.objects.get_or_create(comment=comment, user=request.user)
    liked = True
    if not created:
        like.delete()
        liked = False

    return JsonResponse(
        {
            "message": "Comment liked." if liked else "Comment like removed.",
            "commentId": str(comment.id),
            "liked": liked,
            "likes": comment.likes.count(),
        }
    )


@login_required(login_url="signin")
@require_POST
def dashboard_community_post_update(request, post_id):
    if not (request.user.is_superuser or _has_dashboard_access(request.user)):
        return JsonResponse({"error": "Only active dashboard users can update posts."}, status=403)

    _ensure_community_post_activity_schema()

    post = get_object_or_404(CommunityPost, pk=post_id)
    if post.user != request.user:
        return JsonResponse({"error": "Only the author can edit this post."}, status=403)

    content = str(request.POST.get("content", "") or "").strip()
    if not content:
        return JsonResponse({"error": "Post content is required."}, status=400)

    with transaction.atomic():
        post.content = content
        post.save(update_fields=["content"])

        if request.POST.get("attachments_changed") == "1":
            removed_ids = {
                value.strip()
                for value in request.POST.getlist("remove_attachment_ids")
                if value.strip()
            }
            existing_attachments = list(post.attachments.all())
            for attachment in existing_attachments:
                if str(attachment.id) in removed_ids:
                    attachment.file.delete(save=False)
                    attachment.delete()

            for uploaded_file in request.FILES.getlist("attachments"):
                try:
                    attachment = CommunityPostAttachment(
                        post=post,
                        file=uploaded_file,
                        original_name=str(getattr(uploaded_file, "name", "") or "uploaded-file"),
                        mime_type=str(getattr(uploaded_file, "content_type", "") or "").lower(),
                        size_bytes=getattr(uploaded_file, "size", 0) or 0,
                    )
                    attachment.full_clean()
                    attachment.save()
                except ValidationError as exc:
                    message = exc.messages[0] if getattr(exc, "messages", None) else "Unable to upload attachment."
                    return JsonResponse({"error": message}, status=400)
    updated_post = CommunityPost.objects.select_related("user").prefetch_related("attachments").get(pk=post_id)

    return JsonResponse({"message": "Post updated.", "post": _serialize_community_post(updated_post, viewer=request.user)})


@login_required(login_url="signin")
@require_POST
def dashboard_community_post_delete(request, post_id):
    if not (request.user.is_superuser or _has_dashboard_access(request.user)):
        return JsonResponse({"error": "Only active dashboard users can delete posts."}, status=403)

    _ensure_community_post_activity_schema()

    post = get_object_or_404(CommunityPost, pk=post_id)
    if post.user != request.user and not request.user.is_staff:
        return JsonResponse({"error": "Only the author or an admin can delete this post."}, status=403)

    post.delete()
    return JsonResponse({"message": "Post deleted.", "postId": str(post_id)})


@login_required(login_url="signin")
@require_POST
def dashboard_community_post_report(request, post_id):
    if not (request.user.is_superuser or _has_dashboard_access(request.user)):
        return JsonResponse({"error": "Only active dashboard users can report posts."}, status=403)

    _ensure_community_post_activity_schema()

    post = get_object_or_404(CommunityPost, pk=post_id)
    if post.user == request.user:
        return JsonResponse({"error": "You cannot report your own post."}, status=400)

    reason = str(request.POST.get("reason", "") or "").strip()
    allowed_reasons = {choice[0] for choice in CommunityPostReport.REASON_CHOICES}
    if reason not in allowed_reasons:
        return JsonResponse({"error": "Please select a valid report reason."}, status=400)

    details = str(request.POST.get("details", "") or "").strip()

    report, created = CommunityPostReport.objects.get_or_create(
        post=post,
        reported_by=request.user,
        defaults={
            "reason": reason,
            "details": details,
        }
    )
    if not created:
        report.reason = reason
        report.details = details
        report.save(update_fields=["reason", "details", "updated_at"])

    return JsonResponse({
        "message": "Report submitted. Thank you for your feedback.",
        "postId": str(post_id),
        "reportId": str(report.id),
    })


@login_required(login_url="signin")
def dashboard_notifications(request):
    if not _has_dashboard_access(request.user):
        return redirect("home")

    dashboard_scope = "admin"
    base_template = "base.html"
    if not request.user.is_superuser:
        profile = _get_or_create_user_profile(request.user)
        if profile.account_role == UserProfile.ROLE_VOLUNTEER and _is_active_volunteer(request.user):
            dashboard_scope = "volunteer"
            base_template = "user_dashboard/base.html"
        elif _is_active_beneficiary(request.user):
            dashboard_scope = "beneficiary"
            base_template = "user_dashboard/base.html"
        else:
            return redirect("home")

    notifications = list(
        CommunityNotification.objects
        .filter(recipient=request.user)
        .order_by("-created_at", "-id")
    )
    serialized_notifications = [_serialize_community_notification(notification) for notification in notifications]

    return render(request, "user_dashboard/notifications.html", {
        "active_page": "notifications",
        "base_template": base_template,
        "dashboard_scope": dashboard_scope,
        "notifications_page_unread": [item for item in serialized_notifications if not item["is_read"]],
        "notifications_page_read": [item for item in serialized_notifications if item["is_read"]],
        "notifications_page_unread_count": sum(1 for notification in notifications if not notification.is_read),
    })


@login_required(login_url="signin")
@require_POST
def dashboard_notification_mark_read(request):
    if not _has_dashboard_access(request.user):
        return JsonResponse({"error": "Only active dashboard users can access notifications."}, status=403)

    notification_id = _parse_non_negative_int(request.POST.get("notification_id"), default=0)
    if notification_id <= 0:
        return JsonResponse({"error": "notification_id is required."}, status=400)

    updated = CommunityNotification.objects.filter(
        id=notification_id,
        recipient=request.user,
        is_read=False,
    ).update(is_read=True)

    unread_count = CommunityNotification.objects.filter(recipient=request.user, is_read=False).count()
    return JsonResponse(
        {
            "updated": bool(updated),
            "unreadCount": unread_count,
        }
    )


@login_required(login_url="signin")
@require_POST
def dashboard_notification_mark_all_read(request):
    if not _has_dashboard_access(request.user):
        return JsonResponse({"error": "Only active dashboard users can access notifications."}, status=403)

    CommunityNotification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return JsonResponse({"updated": True, "unreadCount": 0})


@login_required(login_url="signin")
@require_GET
def dashboard_notifications_feed(request):
    if not _has_dashboard_access(request.user):
        return JsonResponse({"error": "Only active dashboard users can access notifications."}, status=403)

    notifications = list(
        CommunityNotification.objects
        .filter(recipient=request.user)
        .order_by("-created_at", "-id")[:10]
    )

    return JsonResponse(
        {
            "notifications": [_serialize_community_notification(notification) for notification in notifications],
            "unreadCount": CommunityNotification.objects.filter(recipient=request.user, is_read=False).count(),
        }
    )


@login_required(login_url="signin")
def volunteer_dashboard_skill_learning(request):
    if request.user.is_superuser:
        return redirect("admin_dashboard")

    if not _is_active_volunteer(request.user):
        return redirect("home")

    _ensure_skill_learning_content()

    return render(request, "volunteer_dashboard/skill_learning_volunteer.html", {
        "active_page": "skill_learning",
        "dashboard_scope": "volunteer",
        "skill_learning_payload": _skill_learning_payload(request.user),
        "skill_learning_api_base": reverse("volunteer_dashboard_skill_learning"),
    })


@login_required(login_url="signin")
@require_GET
def skill_learning_data_api(request):
    if request.user.is_superuser:
        return JsonResponse({"error": "Only dashboard users can access learning topics."}, status=403)

    if not _has_dashboard_access(request.user):
        return JsonResponse({"error": "Only dashboard users can access learning topics."}, status=403)

    return JsonResponse(_skill_learning_payload(request.user))


@login_required(login_url="signin")
@require_POST
def skill_learning_topic_open(request, topic_id):
    if request.user.is_superuser or not _has_dashboard_access(request.user):
        return JsonResponse({"error": "Only dashboard users can access learning topics."}, status=403)
    topic = get_object_or_404(SkillLearningTopic, pk=topic_id)
    engagement, _ = SkillLearningTopicEngagement.objects.get_or_create(user=request.user, topic=topic)
    engagement.page_open_count += 1
    engagement.last_accessed_at = timezone.now()
    engagement.save(update_fields=["page_open_count", "last_accessed_at"])
    return JsonResponse({"ok": True})


@login_required(login_url="signin")
@require_POST
def skill_learning_material_engagement(request, material_id):
    if request.user.is_superuser or not _has_dashboard_access(request.user):
        return JsonResponse({"error": "Only dashboard users can access learning topics."}, status=403)
    material = get_object_or_404(SkillLearningMaterial, pk=material_id)
    action = str(request.POST.get("action") or "view").lower()
    if action not in {"view", "complete", "uncomplete"}:
        return JsonResponse({"error": "Unsupported engagement action."}, status=400)
    engagement, _ = SkillLearningMaterialEngagement.objects.get_or_create(user=request.user, material=material)
    engagement.last_accessed_at = timezone.now()
    if action == "view":
        engagement.view_count += 1
    elif action == "complete":
        engagement.completed_at = timezone.now()
    else:
        engagement.completed_at = None
    engagement.save(update_fields=["view_count", "completed_at", "last_accessed_at"])
    return JsonResponse({"ok": True, "completed": bool(engagement.completed_at)})


@login_required(login_url="signin")
@require_POST
def skill_learning_topic_create(request):
    if request.user.is_superuser or not _is_active_volunteer(request.user):
        return JsonResponse({"error": "Only volunteers can manage learning topics."}, status=403)

    form = SkillLearningTopicForm(request.POST, request.FILES)
    if not form.is_valid():
        return JsonResponse({"error": "Please fix the highlighted topic fields.", "fields": form.errors}, status=400)

    topic = form.save(commit=False)
    topic.filter_tags = form.cleaned_data.get("filter_tags") or []
    topic.is_recommended = False
    topic.popularity_score = 0
    topic.save()

    return JsonResponse({"message": "Topic created.", "topic": _skill_learning_topic_payload(topic)}, status=201)


@login_required(login_url="signin")
@require_POST
def skill_learning_topic_update(request, topic_id):
    if request.user.is_superuser or not _is_active_volunteer(request.user):
        return JsonResponse({"error": "Only volunteers can manage learning topics."}, status=403)

    topic = get_object_or_404(SkillLearningTopic, pk=topic_id)
    form = SkillLearningTopicForm(request.POST, request.FILES, instance=topic)
    if not form.is_valid():
        return JsonResponse({"error": "Please fix the highlighted topic fields.", "fields": form.errors}, status=400)

    topic = form.save(commit=False)
    topic.filter_tags = form.cleaned_data.get("filter_tags") or []
    topic.save()

    return JsonResponse({"message": "Topic updated.", "topic": _skill_learning_topic_payload(topic)})


@login_required(login_url="signin")
@require_POST
def skill_learning_topic_delete(request, topic_id):
    if request.user.is_superuser or not _is_active_volunteer(request.user):
        return JsonResponse({"error": "Only volunteers can manage learning topics."}, status=403)

    topic = get_object_or_404(SkillLearningTopic, pk=topic_id)
    topic.delete()
    return JsonResponse({"message": "Topic deleted.", "topicId": str(topic_id)})


@login_required(login_url="signin")
@require_POST
def skill_learning_material_create(request, topic_id):
    if request.user.is_superuser or not _is_active_volunteer(request.user):
        return JsonResponse({"error": "Only volunteers can manage learning materials."}, status=403)

    topic = get_object_or_404(SkillLearningTopic, pk=topic_id)
    form = SkillLearningMaterialForm(request.POST, request.FILES)
    if not form.is_valid():
        return JsonResponse({"error": "Please fix the highlighted material fields.", "fields": form.errors}, status=400)

    material = form.save(commit=False)
    material.topic = topic
    material.save()

    return JsonResponse({"message": "Material created.", "topic": _skill_learning_topic_payload(topic)})


@login_required(login_url="signin")
@require_POST
def skill_learning_material_update(request, material_id):
    if request.user.is_superuser or not _is_active_volunteer(request.user):
        return JsonResponse({"error": "Only volunteers can manage learning materials."}, status=403)

    material = get_object_or_404(SkillLearningMaterial.objects.select_related("topic"), pk=material_id)
    form = SkillLearningMaterialForm(request.POST, request.FILES, instance=material)
    if not form.is_valid():
        return JsonResponse({"error": "Please fix the highlighted material fields.", "fields": form.errors}, status=400)

    form.save()
    topic = SkillLearningTopic.objects.prefetch_related("materials").get(pk=material.topic_id)
    return JsonResponse({"message": "Material updated.", "topic": _skill_learning_topic_payload(topic)})


@login_required(login_url="signin")
@require_POST
def skill_learning_material_delete(request, material_id):
    if request.user.is_superuser or not _is_active_volunteer(request.user):
        return JsonResponse({"error": "Only volunteers can manage learning materials."}, status=403)

    material = get_object_or_404(SkillLearningMaterial.objects.select_related("topic"), pk=material_id)
    topic_id = material.topic_id
    material.delete()
    topic = SkillLearningTopic.objects.prefetch_related("materials").get(pk=topic_id)
    return JsonResponse({"message": "Material deleted.", "topic": _skill_learning_topic_payload(topic)})


def _serialize_submission_file(file_obj, request):
    return {
        "id": str(file_obj.id),
        "name": file_obj.original_name,
        "size": int(file_obj.size_bytes or 0),
        "download_url": request.build_absolute_uri(
            reverse("download_material_work_file", args=[file_obj.id])
        ),
    }


def _serialize_submission(submission, request):
    return {
        "id": str(submission.id),
        "topic_id": submission.topic_id,
        "material_id": submission.material_id,
        "note": submission.note,
        "created_at": submission.created_at.isoformat(),
        "files": [_serialize_submission_file(file_obj, request) for file_obj in submission.files.all()],
    }


def _build_latest_material_submission_payload(user, topic_id, material_id, request):
    latest_submission = (
        MaterialSubmission.objects
        .filter(user=user, topic_id=topic_id, material_id=material_id)
        .order_by("-created_at")
        .first()
    )
    if not latest_submission:
        return None

    all_files = (
        MaterialSubmissionFile.objects
        .filter(
            submission__user=user,
            submission__topic_id=topic_id,
            submission__material_id=material_id,
        )
        .select_related("submission")
        .order_by("-uploaded_at")
    )

    return {
        "id": str(latest_submission.id),
        "topic_id": latest_submission.topic_id,
        "material_id": latest_submission.material_id,
        "note": latest_submission.note,
        "created_at": latest_submission.created_at.isoformat(),
        "files": [_serialize_submission_file(file_obj, request) for file_obj in all_files],
    }


@login_required(login_url="signin")
@require_POST
def submit_material_work(request):
    if request.user.is_superuser:
        return JsonResponse({"error": "Only beneficiaries can upload material work."}, status=403)

    topic_id = str(request.POST.get("topic_id", "")).strip()
    topic_title = str(request.POST.get("topic_title", "")).strip()
    material_id = str(request.POST.get("material_id", "")).strip()
    material_title = str(request.POST.get("material_title", "")).strip()
    note = str(request.POST.get("note", "")).strip()
    uploaded_files = request.FILES.getlist("files")

    if not topic_id or not material_id:
        return JsonResponse({"error": "Missing topic or material identifier."}, status=400)

    if not uploaded_files:
        return JsonResponse({"error": "Please attach at least one file."}, status=400)

    if len(uploaded_files) > 5:
        return JsonResponse({"error": "You can upload up to 5 files per submission."}, status=400)

    existing_file_count = MaterialSubmissionFile.objects.filter(
        submission__user=request.user,
        submission__topic_id=topic_id,
        submission__material_id=material_id,
    ).count()
    if existing_file_count + len(uploaded_files) > 5:
        remaining = max(0, 5 - existing_file_count)
        return JsonResponse(
            {
                "error": f"You already uploaded {existing_file_count} file(s). "
                f"You can add {remaining} more only (max 5)."
            },
            status=400,
        )

    max_size_mb = MAX_UPLOAD_FILE_SIZE_BYTES // (1024 * 1024)
    for upload in uploaded_files:
        filename = str(getattr(upload, "name", "") or "")
        extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if extension not in ALLOWED_UPLOAD_EXTENSIONS:
            return JsonResponse(
                {"error": f"Unsupported file type for '{filename}'."},
                status=400,
            )

        if (getattr(upload, "size", 0) or 0) > MAX_UPLOAD_FILE_SIZE_BYTES:
            return JsonResponse(
                {"error": f"'{filename}' is too large. Max size is {max_size_mb} MB."},
                status=400,
            )

    submission = MaterialSubmission.objects.create(
        user=request.user,
        topic_id=topic_id,
        topic_title=topic_title,
        material_id=material_id,
        material_title=material_title,
        note=note,
    )

    try:
        for upload in uploaded_files:
            MaterialSubmissionFile.objects.create(
                submission=submission,
                file=upload,
                original_name=str(getattr(upload, "name", "") or "uploaded-file"),
                mime_type=str(getattr(upload, "content_type", "") or "").lower(),
                size_bytes=getattr(upload, "size", 0) or 0,
            )
    except ValidationError as exc:
        submission.delete()
        return JsonResponse({"error": "; ".join(exc.messages)}, status=400)

    submission_payload = _build_latest_material_submission_payload(
        request.user,
        topic_id,
        material_id,
        request,
    )
    return JsonResponse(
        {
            "message": "Work uploaded successfully.",
            "submission": submission_payload,
        },
        status=201,
    )


@login_required(login_url="signin")
@require_GET
def latest_material_work(request):
    if request.user.is_superuser:
        return JsonResponse({"error": "Only beneficiaries can access this endpoint."}, status=403)

    topic_id = str(request.GET.get("topic_id", "")).strip()
    material_id = str(request.GET.get("material_id", "")).strip()
    if not topic_id or not material_id:
        return JsonResponse({"error": "topic_id and material_id are required."}, status=400)

    submission_payload = _build_latest_material_submission_payload(
        request.user,
        topic_id,
        material_id,
        request,
    )

    if not submission_payload:
        return JsonResponse({"submission": None})

    return JsonResponse({"submission": submission_payload})


@login_required(login_url="signin")
@require_GET
def download_material_work_file(request, file_id):
    if request.user.is_superuser:
        raise Http404()

    file_obj = get_object_or_404(
        MaterialSubmissionFile.objects.select_related("submission"),
        id=file_id,
        submission__user=request.user,
    )

    response = FileResponse(file_obj.file.open("rb"), as_attachment=True, filename=file_obj.original_name)
    response["X-Content-Type-Options"] = "nosniff"
    return response


@login_required(login_url="signin")
@require_POST
def remove_material_work_file(request):
    if request.user.is_superuser:
        raise Http404()

    file_id = str(request.POST.get("file_id", "")).strip()
    if not file_id:
        return JsonResponse({"error": "file_id is required."}, status=400)

    file_obj = get_object_or_404(
        MaterialSubmissionFile.objects.select_related("submission"),
        id=file_id,
        submission__user=request.user,
    )

    file_obj.file.delete(save=False)
    file_obj.delete()
    return JsonResponse({"message": "File removed successfully."})


def _build_dashboard_priority_rows(pending_role_applications, low_stock_items):
    rows = []

    for application in pending_role_applications[:3]:
        label = "Volunteer approvals" if application.role == RoleApplication.ROLE_VOLUNTEER else "Beneficiary requests"
        detail = f"{application.full_name} waiting for review"
        rows.append({
            "title": label,
            "detail": detail,
            "priority": "Critical" if application.role == RoleApplication.ROLE_VOLUNTEER else "Medium",
            "dot_class": "ops-dot-critical" if application.role == RoleApplication.ROLE_VOLUNTEER else "ops-dot-medium",
            "badge_class": "ops-badge-critical" if application.role == RoleApplication.ROLE_VOLUNTEER else "ops-badge-medium",
        })

    for item in low_stock_items[:2]:
        rows.append({
            "title": f"{item.name} stock alert",
            "detail": f"{item.stock} units left",
            "priority": "High" if item.stock <= item.low_stock_threshold else "Monitor",
            "dot_class": "ops-dot-high",
            "badge_class": "ops-badge-high",
        })

    return rows[:5]


def _build_dashboard_inventory_rows():
    rows = []
    for item in InventoryItem.objects.order_by("stock")[:4]:
        if item.stock <= 5:
            status_label = "Critical"
            dot_class = "ops-dot-critical"
            badge_class = "ops-badge-critical"
        elif item.stock <= item.low_stock_threshold:
            status_label = "Low"
            dot_class = "ops-dot-high"
            badge_class = "ops-badge-high"
        else:
            status_label = "OK"
            dot_class = "ops-dot-low"
            badge_class = "ops-badge-low"

        rows.append({
            "name": item.name,
            "stock": item.stock,
            "status_label": status_label,
            "dot_class": dot_class,
            "badge_class": badge_class,
        })

    return rows


def _build_dashboard_recent_activity_rows(limit=4):
    rows = []

    for donation in Donation.objects.select_related("user").order_by("-created_at")[:5]:
        donor_name = (donation.donor_name or "Anonymous donor").strip() or "Anonymous donor"
        rows.append({
            "title": f"Donation received from {donor_name}",
            "detail": f"₱{donation.amount:,} · {donation.get_status_display() or donation.status}",
            "timestamp": donation.created_at,
            "badge_label": "Donated",
            "dot_class": "ops-dot-low",
            "badge_class": "ops-badge-low",
        })

    for order in ProductInquiry.objects.filter(status__in=[ProductInquiry.STATUS_VERIFIED, ProductInquiry.STATUS_COMPLETED]).order_by("-created_at")[:5]:
        customer_name = (order.full_name or "Online customer").strip() or "Online customer"
        rows.append({
            "title": f"E-commerce order from {customer_name}",
            "detail": f"₱{order.order_total:,} · {order.get_status_display() or order.status}",
            "timestamp": order.created_at,
            "badge_label": "Order",
            "dot_class": "ops-dot-low",
            "badge_class": "ops-badge-low",
        })

    for application in RoleApplication.objects.select_related("user").filter(status=RoleApplication.STATUS_PENDING).order_by("-created_at")[:5]:
        applicant_name = (application.full_name or (application.user.get_full_name() if application.user_id else "New applicant")).strip()
        if not applicant_name:
            applicant_name = "New applicant"
        role_label = "Volunteer application" if application.role == RoleApplication.ROLE_VOLUNTEER else "Beneficiary application"
        rows.append({
            "title": f"{role_label} from {applicant_name}",
            "detail": f"Submitted {application.created_at.strftime('%b %d, %Y') if application.created_at else 'recently'}",
            "timestamp": application.created_at,
            "badge_label": "Pending",
            "dot_class": "ops-dot-medium",
            "badge_class": "ops-badge-medium",
        })

    for item in InventoryItem.objects.order_by("-updated_at")[:3]:
        rows.append({
            "title": f"Inventory update for {item.name}",
            "detail": f"{item.stock} units remaining · {item.get_status_display() if hasattr(item, 'get_status_display') else 'Status updated'}",
            "timestamp": item.updated_at,
            "badge_label": "Updated",
            "dot_class": "ops-dot-high" if item.stock <= item.low_stock_threshold else "ops-dot-low",
            "badge_class": "ops-badge-high" if item.stock <= item.low_stock_threshold else "ops-badge-low",
        })

    unique_rows = []
    seen = set()
    for row in sorted(rows, key=lambda item: item["timestamp"], reverse=True):
        fingerprint = (row.get("title") or "") + "|" + (row.get("detail") or "")
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        unique_rows.append(row)
        if len(unique_rows) >= limit:
            break

    return unique_rows


def _summarize_moderation_detail(text, limit=90):
    cleaned = (text or "").strip().replace("\n", " ")
    return (cleaned[:limit] + "...") if len(cleaned) > limit else cleaned or "Needs moderator review"


def _build_dashboard_moderation_rows(limit=4):
    rows = []

    reported_posts = (
        CommunityPost.objects.filter(reports__isnull=False)
        .annotate(report_count=Count("reports", distinct=True))
        .order_by("-report_count", "-created_at")
        .distinct()[:8]
    )
    for post in reported_posts:
        report_count = getattr(post, "report_count", 0) or post.reports.count()
        escalated = report_count >= 2
        rows.append({
            "title": "Community post reported",
            "detail": _summarize_moderation_detail(post.content),
            "timestamp": post.created_at,
            "badge_label": "Escalated" if escalated else "Review",
            "dot_class": "ops-dot-critical" if escalated else "ops-dot-high",
            "badge_class": "ops-badge-critical" if escalated else "ops-badge-high",
            "sort_score": 200 if escalated else 140,
        })

    recent_posts = CommunityPost.objects.order_by("-created_at")[:8]
    for post in recent_posts:
        if post.reports.exists():
            continue
        rows.append({
            "title": "Pending post approval",
            "detail": _summarize_moderation_detail(post.content),
            "timestamp": post.created_at,
            "badge_label": "Moderate",
            "dot_class": "ops-dot-medium",
            "badge_class": "ops-badge-medium",
            "sort_score": 90,
        })

    seen = set()
    unique_rows = []
    for row in sorted(rows, key=lambda item: (item["sort_score"], item["timestamp"]), reverse=True):
        fingerprint = (row["title"], row["detail"])
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        unique_rows.append({
            key: value for key, value in row.items() if key != "sort_score"
        })
        if len(unique_rows) >= limit:
            break

    return unique_rows


def _build_weekly_series(days=8):
    today = timezone.localdate()
    labels = []
    values = []
    current = today - timedelta(days=7 * (days - 1))
    for _ in range(days):
        labels.append(current.strftime("%b %d"))
        values.append(0)
        current += timedelta(days=7)
    return labels, values


def _build_dashboard_chart_data():
    today = timezone.localdate()
    donation_series = [0] * 8
    volunteer_series = [0] * 8

    donation_qs = Donation.objects.filter(
        created_at__date__gte=today - timedelta(days=56),
        status__in=[Donation.STATUS_VERIFIED, Donation.STATUS_COMPLETED],
    )
    for donation in donation_qs:
        donation_date = timezone.localtime(donation.created_at).date()
        delta_days = (today - donation_date).days
        if delta_days < 56:
            week_index = min(7, int(delta_days // 7))
            donation_series[7 - week_index] += int(donation.amount or 0)

    attendance_qs = VolunteerAttendanceRecord.objects.filter(
        status=VolunteerAttendanceRecord.STATUS_CONFIRMED,
        created_at__gte=timezone.now() - timedelta(days=56),
    )
    for attendance in attendance_qs:
        attendance_date = timezone.localtime(attendance.created_at).date()
        delta_days = (today - attendance_date).days
        if delta_days < 56:
            week_index = min(7, int(delta_days // 7))
            volunteer_series[7 - week_index] += 1

    labels = []
    current = today - timedelta(days=7 * 7)
    for _ in range(8):
        labels.append(current.strftime("%b %d"))
        current += timedelta(days=7)

    return {"donations": labels, "donation_values": donation_series, "volunteers": labels, "volunteer_values": volunteer_series}


def admin_dashboard(request):
    if not request.user.is_superuser:
        return redirect("user_dashboard")

    pending_beneficiary_applications = _get_pending_role_applications(RoleApplication.ROLE_BENEFICIARY)
    pending_volunteer_applications = _get_pending_role_applications(RoleApplication.ROLE_VOLUNTEER)
    pending_role_applications = sorted(
        pending_beneficiary_applications + pending_volunteer_applications,
        key=lambda application: (application.created_at, application.id),
        reverse=True,
    )

    active_volunteers_count = User.objects.filter(
        is_active=True,
        userprofile__account_role=UserProfile.ROLE_VOLUNTEER,
    ).count()
    active_beneficiaries_count = User.objects.filter(
        is_active=True,
        userprofile__account_role=UserProfile.ROLE_BENEFICIARY,
    ).count()

    today_for_month = timezone.localdate()
    month_start = date(today_for_month.year, today_for_month.month, 1)
    month_end = date(today_for_month.year, today_for_month.month, calendar.monthrange(today_for_month.year, today_for_month.month)[1])
    donations_this_month = Donation.objects.filter(
        created_at__date__gte=month_start,
        created_at__date__lte=month_end,
        status__in=[Donation.STATUS_VERIFIED, Donation.STATUS_COMPLETED],
    )
    donations_this_month_amount = int(donations_this_month.aggregate(total=Sum("amount"))["total"] or 0)

    low_stock_items = InventoryItem.objects.filter(stock__lte=F("low_stock_threshold")).order_by("stock")
    low_stock_items_count = low_stock_items.count()
    low_stock_critical_count = InventoryItem.objects.filter(stock__lte=F("low_stock_threshold")).filter(stock__lte=5).count()

    activities_qs = Activity.objects.all().order_by("date", "title")
    today = timezone.localdate()
    upcoming_activities = list(
        activities_qs.filter(date__gte=today, status=Activity.STATUS_ACTIVE)
        .order_by("date", "start_time")[:5]
    )
    upcoming_activities_json = json.dumps([{
        'day': a.date.day,
        'month': a.date.month,
        'year': a.date.year,
        'month_name': a.date.strftime('%b'),
        'title': a.title,
        'time': a.start_time.strftime('%I:%M %p') if a.start_time else 'TBA',
        'location': a.location or 'TBA',
        'status': a.status,
        'status_display': a.get_status_display(),
        'image_url': _activity_image_url(a),
    } for a in upcoming_activities])
    activity_dates_current_month = sorted({
        a.day
        for a in activities_qs.filter(date__year=today.year, date__month=today.month).values_list("date", flat=True)
    })

    chart_data = _build_dashboard_chart_data()
    inventory_rows = _build_dashboard_inventory_rows()
    priority_rows = _build_dashboard_priority_rows(pending_role_applications, low_stock_items)
    recent_activity_rows = _build_dashboard_recent_activity_rows(limit=12)
    moderation_rows = _build_dashboard_moderation_rows(limit=4)

    return render(request, "admin_dashboard/dashboard_control_center_admin.html", {
        "active_page": "dashboard",
        "dashboard_scope": "admin",
        "active_volunteers_count": active_volunteers_count,
        "active_beneficiaries_count": active_beneficiaries_count,
        "donations_this_month_amount": donations_this_month_amount,
        "low_stock_items_count": low_stock_items_count,
        "low_stock_critical_count": low_stock_critical_count,
        "pending_beneficiary_count": len(pending_beneficiary_applications),
        "pending_volunteer_count": len(pending_volunteer_applications),
        "pending_application_count": len(pending_role_applications),
        "pending_beneficiary_applications": [
            _serialize_pending_role_application(application)
            for application in pending_beneficiary_applications[:10]
        ],
        "pending_volunteer_applications": [
            _serialize_pending_role_application(application)
            for application in pending_volunteer_applications[:10]
        ],
        "pending_role_applications": [
            _serialize_pending_role_application(application)
            for application in pending_role_applications[:5]
        ],
        "priority_rows": priority_rows,
        "inventory_rows": inventory_rows,
        "recent_activity_rows": recent_activity_rows,
        "moderation_rows": moderation_rows,
        "chart_data": chart_data,
        "upcoming_activities": upcoming_activities,
        "upcoming_activities_json": upcoming_activities_json,
        "activity_dates": activity_dates_current_month,
        "activity_dates_json": json.dumps(activity_dates_current_month),
        "today": today,
        "volunteer_options": _build_volunteer_options(),
    })


@login_required(login_url="signin")
@require_GET
def admin_dashboard_moderation_queue(request):
    if not request.user.is_superuser:
        return JsonResponse({"error": "Only admins can access moderation queue data."}, status=403)

    return JsonResponse({"rows": _build_dashboard_moderation_rows(limit=4)})


@login_required(login_url="signin")
def users(request):
    if not request.user.is_superuser:
        return redirect("user_dashboard")

    return render(request, "admin_dashboard/admins_management_admin.html", {
        "active_page": "users",
    })


@login_required(login_url="signin")
def volunteers(request):
    if not request.user.is_superuser:
        return redirect("user_dashboard")

    activities = Activity.objects.prefetch_related("volunteer_assignments").order_by("date", "start_time", "title")
    activity_options = [
        {
            "id": activity.id,
            "title": activity.title,
            "date": activity.date.isoformat() if activity.date else "",
            "time": activity.start_time.strftime("%H:%M") if activity.start_time else "",
            "time_label": activity.start_time.strftime("%I:%M %p").lstrip("0") if activity.start_time else "TBA",
            "location": activity.location or "TBA",
            "category": activity.category,
            "volunteer_ids": [assignment.volunteer_id for assignment in activity.volunteer_assignments.all()],
        }
        for activity in activities
    ]

    return render(request, "admin_dashboard/volunteers_admin.html", {
        "active_page": "volunteers",
        "volunteers_data": _build_volunteers_payload(),
        "pending_volunteer_applications": [
            _serialize_pending_volunteer_application(application)
            for application in _get_pending_role_applications(RoleApplication.ROLE_VOLUNTEER)
        ],
        "volunteer_options": _build_volunteer_options(),
        "volunteer_certificates": _build_admin_certificate_payload(),
        "activity_options": activity_options,
        "pending_attendance": [
            {
                **_serialize_volunteer_attendance(attendance),
                "volunteer_name": _display_name_for_user(attendance.volunteer),
                "activity_name": attendance.assignment.activity_name,
                "scheduled_date": attendance.assignment.scheduled_date.isoformat(),
            }
            for attendance in VolunteerAttendanceRecord.objects
            .filter(status=VolunteerAttendanceRecord.STATUS_PENDING)
            .select_related("volunteer", "assignment")
        ],
        "pending_beneficiary_attendance": [
            {
                **_serialize_beneficiary_activity_attendance(attendance),
                "beneficiary_name": _display_name_for_user(attendance.beneficiary),
                "volunteer_name": _display_name_for_user(attendance.volunteer) if attendance.volunteer else "Unassigned volunteer",
                "activity_name": attendance.activity.title,
                "scheduled_date": attendance.activity.date.isoformat(),
            }
            for attendance in BeneficiaryActivityAttendance.objects
            .filter(status=BeneficiaryActivityAttendance.STATUS_PENDING, confirmed_at__isnull=False)
            .select_related("activity", "beneficiary", "volunteer")
        ],
    })


@login_required(login_url="signin")
@require_POST
def assign_volunteer_activity(request):
    if not request.user.is_superuser:
        return JsonResponse({"error": "Only administrators can assign activities."}, status=403)

    activity_id = str(request.POST.get("activity_id", "") or request.POST.get("activityId", "")).strip()
    if activity_id:
        try:
            activity = get_object_or_404(Activity, pk=int(activity_id))
        except (TypeError, ValueError):
            return JsonResponse({"error": "A valid existing activity is required."}, status=400)

        volunteer_ids = request.POST.getlist("volunteer_ids[]") or request.POST.getlist("volunteer_ids")
        if not volunteer_ids:
            volunteer_ids = [value.strip() for value in str(request.POST.get("volunteer_ids", "") or "").split(",") if value.strip()]
        _sync_activity_volunteer_assignments(activity, volunteer_ids, request.user)
        return JsonResponse({
            "message": "Volunteer assignments saved.",
            "activity_id": activity.id,
            "volunteer_ids": _build_activity_volunteer_map(Activity.objects.filter(pk=activity.id)).get(str(activity.id), []),
        })

    activity_name = str(request.POST.get("activity_name", "") or request.POST.get("activityName", "")).strip()
    activity_type = str(request.POST.get("activity_type", "") or request.POST.get("activityType", "")).strip()
    location = str(request.POST.get("location", "")).strip()
    category = str(request.POST.get("category", "")).strip()
    date_value = str(request.POST.get("date", "") or request.POST.get("scheduled_date", "") or request.POST.get("scheduledDate", "")).strip()
    time_value = str(request.POST.get("time", "") or request.POST.get("scheduled_time", "") or request.POST.get("scheduledTime", "")).strip()
    notes = str(request.POST.get("notes", "") or request.POST.get("note", "")).strip()

    volunteer_ids = request.POST.getlist("volunteer_ids[]") or request.POST.getlist("volunteer_ids")
    if not volunteer_ids:
        volunteer_ids_raw = str(request.POST.get("volunteer_ids", "") or request.POST.get("volunteerIds", "")).strip()
        if volunteer_ids_raw:
            volunteer_ids = [value.strip() for value in volunteer_ids_raw.split(",") if value.strip()]

    if not activity_name:
        return JsonResponse({"error": "activity_name is required."}, status=400)

    if not activity_type:
        return JsonResponse({"error": "activity_type is required."}, status=400)

    if not date_value:
        return JsonResponse({"error": "date is required."}, status=400)

    if not location:
        return JsonResponse({"error": "location is required."}, status=400)

    if not volunteer_ids:
        return JsonResponse({"error": "volunteer_ids is required."}, status=400)

    try:
        scheduled_date = datetime.strptime(date_value, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({"error": "date must be in YYYY-MM-DD format."}, status=400)

    scheduled_time = None
    if time_value:
        try:
            scheduled_time = datetime.strptime(time_value, "%H:%M").time()
        except ValueError:
            return JsonResponse({"error": "time must be in HH:MM format."}, status=400)

    volunteers = list(
        User.objects.filter(
            id__in=volunteer_ids,
            is_active=True,
            userprofile__account_role=UserProfile.ROLE_VOLUNTEER,
        )
    )
    if len(volunteers) != len(volunteer_ids):
        return JsonResponse({"error": "One or more volunteers could not be found."}, status=400)

    assignments = []
    with transaction.atomic():
        for volunteer in volunteers:
            assignments.append(VolunteerActivityAssignment.objects.create(
                volunteer=volunteer,
                activity_name=activity_name,
                activity_type=activity_type,
                scheduled_date=scheduled_date,
                scheduled_time=scheduled_time,
                location=location,
                notes=notes,
                assigned_by=request.user,
            ))

            _create_in_app_notification(
                recipient=volunteer,
                actor=request.user,
                notification_type=CommunityNotification.TYPE_VOLUNTEER_ASSIGNMENT,
                message=f"You have been assigned to {activity_name} on {scheduled_date.strftime('%b %d, %Y')}.",
                target_url=reverse("volunteer_dashboard_tasks_ojt"),
            )
            _send_volunteer_assignment_email(volunteer, activity_name, scheduled_date)

    return JsonResponse({
        "message": "Activity assigned successfully.",
        "assigned_count": len(assignments),
    }, status=201)


@login_required(login_url="signin")
def beneficiaries(request):
    if not request.user.is_superuser:
        return redirect("user_dashboard")

    return render(request, "admin_dashboard/beneficiaries_admin.html", {
        "active_page": "beneficiaries",
        "dashboard_scope": "admin",
        "beneficiaries_data": _build_beneficiaries_payload(),
        "volunteer_options": _build_volunteer_options(),
        "assistance_tracking": _build_assistance_tracking_payload(),
        "assistance_feedbacks": _build_assistance_feedbacks_payload(),
        "pending_beneficiary_applications": [
            _serialize_pending_beneficiary_application(application)
            for application in _get_pending_role_applications(RoleApplication.ROLE_BENEFICIARY)
        ],
    })


@login_required(login_url="signin")
@require_GET
def beneficiaries_data_api(request):
    if not request.user.is_superuser:
        return JsonResponse({"error": "Only administrators can access this endpoint."}, status=403)

    return JsonResponse(_build_beneficiaries_dashboard_payload())


@login_required(login_url="signin")
@require_GET
def volunteers_data_api(request):
    if not request.user.is_superuser:
        return JsonResponse({"error": "Only administrators can access this endpoint."}, status=403)

    return JsonResponse(_build_volunteers_dashboard_payload())


@login_required(login_url="signin")
@require_POST
def record_beneficiary_assistance(request):
    if not request.user.is_superuser:
        return JsonResponse({"error": "Only administrators can record assistance."}, status=403)

    application_id = str(request.POST.get("beneficiary_application_id", "") or request.POST.get("beneficiaryId", "")).strip()
    application_ids_raw = str(request.POST.get("beneficiary_application_ids", "") or request.POST.get("beneficiaryApplicationIds", "")).strip()
    aid_type = str(request.POST.get("aid_type", "") or request.POST.get("aidType", "")).strip()
    quantity_or_amount = str(request.POST.get("quantity_or_amount", "") or request.POST.get("quantityOrAmount", "")).strip()
    assistance_date_value = str(request.POST.get("assistance_date", "") or request.POST.get("assistanceDate", "")).strip()
    volunteer_id = str(request.POST.get("assigned_volunteer_id", "") or request.POST.get("assignedVolunteerId", "")).strip()
    notes = str(request.POST.get("notes", "") or request.POST.get("note", "")).strip()

    application_ids = []
    if application_ids_raw:
        application_ids = [value.strip() for value in application_ids_raw.split(",") if value.strip()]
    elif application_id:
        application_ids = [application_id]

    if not application_ids:
        return JsonResponse({"error": "beneficiary_application_id is required."}, status=400)

    if not aid_type:
        return JsonResponse({"error": "aid_type is required."}, status=400)

    if not quantity_or_amount:
        return JsonResponse({"error": "quantity_or_amount is required."}, status=400)

    if not assistance_date_value:
        return JsonResponse({"error": "assistance_date is required."}, status=400)

    try:
        assistance_date = datetime.strptime(assistance_date_value, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({"error": "assistance_date must be in YYYY-MM-DD format."}, status=400)

    assigned_volunteer = None
    if volunteer_id:
        assigned_volunteer = get_object_or_404(
            User,
            id=volunteer_id,
            is_active=True,
            userprofile__account_role=UserProfile.ROLE_VOLUNTEER,
        )

    beneficiaries = list(
        RoleApplication.objects.filter(
            id__in=application_ids,
            role=RoleApplication.ROLE_BENEFICIARY,
            status=RoleApplication.STATUS_APPROVED,
        )
    )
    if len(beneficiaries) != len(application_ids):
        return JsonResponse({"error": "One or more beneficiaries could not be found."}, status=400)

    created_records = []
    with transaction.atomic():
        for beneficiary in beneficiaries:
            created_records.append(BeneficiaryAssistanceRecord.objects.create(
                beneficiary=beneficiary,
                aid_type=aid_type,
                quantity_or_amount=quantity_or_amount,
                assistance_date=assistance_date,
                assigned_volunteer=assigned_volunteer,
                notes=notes,
                recorded_by=request.user,
            ))

    payload = _build_beneficiaries_dashboard_payload()
    payload["message"] = "Assistance recorded successfully."
    if len(created_records) == 1:
        payload["record"] = _serialize_assistance_record(created_records[0])
    else:
        payload["records"] = [_serialize_assistance_record(record) for record in created_records]
    return JsonResponse(payload, status=201)


@login_required(login_url="signin")
@require_POST
def delete_beneficiary_assistance_bulk(request):
    if not request.user.is_superuser:
        return JsonResponse({"error": "Only administrators can delete assistance records."}, status=403)

    raw_ids = str(request.POST.get("record_ids", "") or "").strip()
    try:
        record_ids = [int(value) for value in raw_ids.split(",") if value.strip()]
    except ValueError:
        return JsonResponse({"error": "record_ids must contain valid record IDs."}, status=400)

    if not record_ids:
        return JsonResponse({"error": "Select at least one assistance record."}, status=400)

    deleted_count, _details = BeneficiaryAssistanceRecord.objects.filter(id__in=record_ids).delete()
    return JsonResponse({
        "deleted": deleted_count,
        "message": f"Deleted {deleted_count} assistance record(s).",
    })


@login_required(login_url="signin")
@require_POST
def update_beneficiary_profile(request):
    if not request.user.is_superuser:
        return JsonResponse({"error": "Only administrators can update beneficiary profiles."}, status=403)

    application_id = str(request.POST.get("beneficiary_application_id", "") or request.POST.get("applicationId", "")).strip()
    full_name = str(request.POST.get("full_name", "") or request.POST.get("fullName", "")).strip()
    contact_details = str(request.POST.get("contact_details", "") or request.POST.get("contactDetails", "")).strip()
    supporting_information = str(request.POST.get("supporting_information", "") or request.POST.get("supportingInformation", "")).strip()
    admin_notes = str(request.POST.get("admin_notes", "") or request.POST.get("notes", "")).strip()
    raw_status = str(request.POST.get("status", "") or "").strip().lower()

    if not application_id:
        return JsonResponse({"error": "beneficiary_application_id is required."}, status=400)

    beneficiary = get_object_or_404(
        RoleApplication,
        id=application_id,
        role=RoleApplication.ROLE_BENEFICIARY,
        status__in=[RoleApplication.STATUS_APPROVED, RoleApplication.STATUS_INACTIVE],
    )

    if not full_name:
        return JsonResponse({"error": "full_name is required."}, status=400)

    if not contact_details:
        return JsonResponse({"error": "contact_details is required."}, status=400)

    if raw_status in {"active", RoleApplication.STATUS_APPROVED}:
        status = RoleApplication.STATUS_APPROVED
    elif raw_status in {"inactive", RoleApplication.STATUS_INACTIVE}:
        status = RoleApplication.STATUS_INACTIVE
    else:
        status = beneficiary.status

    with transaction.atomic():
        previous_status = beneficiary.status
        beneficiary.full_name = full_name
        beneficiary.contact_details = contact_details
        beneficiary.supporting_information = supporting_information
        beneficiary.admin_notes = admin_notes
        beneficiary.status = status
        if beneficiary.status != previous_status:
            beneficiary.reviewed_at = timezone.now()
            beneficiary.reviewed_by = request.user
        beneficiary.save(update_fields=["full_name", "contact_details", "supporting_information", "admin_notes", "status", "reviewed_at", "reviewed_by", "updated_at"])

        if beneficiary.user_id:
            first_name, last_name = _split_full_name(full_name)
            contact_email, contact_phone = _split_contact_details(contact_details)
            user = beneficiary.user
            user.first_name = first_name
            user.last_name = last_name
            if contact_email:
                user.email = contact_email
            user.save(update_fields=["first_name", "last_name", "email"])

            profile = _get_or_create_user_profile(user)
            if contact_phone:
                profile.phone = contact_phone
            profile.address_line = supporting_information
            profile.account_role = UserProfile.ROLE_BENEFICIARY
            profile.save(update_fields=["phone", "address_line", "account_role", "updated_at"])

    payload = _build_beneficiaries_dashboard_payload()
    payload["message"] = "Beneficiary profile updated successfully."
    return JsonResponse(payload)


@login_required(login_url="signin")
@require_POST
def create_beneficiary(request):
    """Admin endpoint to create a beneficiary (RoleApplication).

    This endpoint creates an optional `User` (when `username` is provided) and a
    `RoleApplication` record with role=beneficiary. Returns JSON payload for UI.
    """
    if not request.user.is_superuser:
        return JsonResponse({"error": "Only administrators can create beneficiaries."}, status=403)

    full_name = str(request.POST.get("full_name", "") or request.POST.get("name", "") or "").strip()
    email = str(request.POST.get("email", "") or "").strip()
    phone = str(request.POST.get("phone", "") or "").strip()
    address = str(request.POST.get("address", "") or request.POST.get("supporting_information", "") or "").strip()
    raw_status = str(request.POST.get("status", "") or "Active").strip()
    username = str(request.POST.get("username", "") or "").strip()
    password = str(request.POST.get("password", "") or "").strip()

    # allow empty values for now (accept submissions with missing fields)
    status_map = {
        "active": RoleApplication.STATUS_APPROVED,
        "approved": RoleApplication.STATUS_APPROVED,
        "inactive": RoleApplication.STATUS_INACTIVE,
        "pending": RoleApplication.STATUS_PENDING,
    }
    status_key = status_map.get(raw_status.lower(), RoleApplication.STATUS_APPROVED)

    # Always create or reuse a user account so beneficiary data stays unique.
    user_obj = None
    generated_password = None
    if not username:
        # create a unique username
        base = (full_name or "beneficiary").strip().lower().replace(" ", "_") or "beneficiary"
        candidate = base
        suffix = 0
        while User.objects.filter(username=candidate).exists():
            suffix += 1
            candidate = f"{base}_{suffix}"
        username = candidate

    if not password:
        # generate a temporary password
        generated_password = secrets.token_urlsafe(8)
        password_to_set = generated_password
    else:
        password_to_set = password

    user_obj = User.objects.filter(username__iexact=username).first()
    if not user_obj and email:
        user_obj = User.objects.filter(email__iexact=email).first()

    is_new_user = user_obj is None

    if not user_obj:
        user_obj = User.objects.create(username=username, email=email, is_active=True)

    first_name, last_name = _split_full_name(full_name)
    user_obj.first_name = first_name
    user_obj.last_name = last_name
    user_obj.email = email
    if is_new_user:
        user_obj.set_password(password_to_set)
    user_obj.is_active = True
    user_obj.save()

    profile = _get_or_create_user_profile(user_obj)
    profile.phone = phone
    profile.address_line = address
    # set account role to beneficiary so they get beneficiary dashboard access
    profile.account_role = UserProfile.ROLE_BENEFICIARY
    profile.save()

    contact_details = email + (" / " + phone if email and phone else (phone or ""))

    application, _created = RoleApplication.objects.update_or_create(
        user=user_obj,
        role=RoleApplication.ROLE_BENEFICIARY,
        defaults={
            "status": status_key,
            "full_name": full_name,
            "contact_details": contact_details,
            "supporting_information": address,
        },
    )

    response_obj = {
        "applicationId": int(application.id),
        "name": application.full_name,
        "email": email,
        "phone": phone,
        "contactDetails": application.contact_details,
        "addressLine": application.supporting_information,
        "location": application.supporting_information[:100] if application.supporting_information else "To be determined",
        "status": "Inactive" if application.status == RoleApplication.STATUS_INACTIVE else "Active",
    }

    # include credentials when we generated a password or created a user
    if user_obj:
        response_obj["user"] = {"id": int(user_obj.id), "username": user_obj.username}
        if generated_password:
            response_obj["user"]["password"] = generated_password

    return JsonResponse({"message": "Beneficiary created.", "application": response_obj}, status=201)


@login_required(login_url="signin")
@require_POST
def deactivate_beneficiary(request):
    if not request.user.is_superuser:
        return JsonResponse({"error": "Only administrators can deactivate beneficiaries."}, status=403)

    application_id = str(request.POST.get("beneficiary_application_id", "") or request.POST.get("applicationId", "")).strip()
    if not application_id:
        return JsonResponse({"error": "beneficiary_application_id is required."}, status=400)

    beneficiary = get_object_or_404(
        RoleApplication,
        id=application_id,
        role=RoleApplication.ROLE_BENEFICIARY,
        status__in=[RoleApplication.STATUS_APPROVED, RoleApplication.STATUS_INACTIVE],
    )

    with transaction.atomic():
        beneficiary.status = RoleApplication.STATUS_REJECTED
        beneficiary.reviewed_at = timezone.now()
        beneficiary.reviewed_by = request.user
        beneficiary.save(update_fields=["status", "reviewed_at", "reviewed_by", "updated_at"])
        if beneficiary.user_id:
            profile = _get_or_create_user_profile(beneficiary.user)
            profile.account_role = UserProfile.ROLE_REGULAR
            profile.save(update_fields=["account_role", "updated_at"])

    payload = _build_beneficiaries_dashboard_payload()
    payload["message"] = f"{beneficiary.full_name} has been removed as beneficiary."
    return JsonResponse(payload)


@login_required(login_url="signin")
@require_POST
def review_role_application(request):
    if not request.user.is_superuser:
        return JsonResponse({"error": "Only administrators can review role applications."}, status=403)

    application_id = str(request.POST.get("application_id", "") or request.POST.get("applicationId", "")).strip()
    action = str(request.POST.get("action", "") or request.POST.get("status", "")).strip().lower()
    admin_notes = str(request.POST.get("admin_notes", "") or request.POST.get("adminNotes", "")).strip()

    if not application_id:
        return JsonResponse({"error": "application_id is required."}, status=400)

    if action == "approve":
        action = RoleApplication.STATUS_APPROVED
    elif action == "reject":
        action = RoleApplication.STATUS_REJECTED

    if action not in {RoleApplication.STATUS_APPROVED, RoleApplication.STATUS_REJECTED}:
        return JsonResponse({"error": "action must be approve or reject."}, status=400)

    application = get_object_or_404(RoleApplication, id=application_id)
    _review_role_application(application, status=action, reviewer=request.user, admin_notes=admin_notes)

    return _review_role_application_response(application, action)


@login_required(login_url="signin")
def activities(request):
    if not request.user.is_superuser:
        return redirect("user_dashboard")

    activities_qs = Activity.objects.prefetch_related("volunteer_assignments", "beneficiary_assignments").all().order_by("date", "title")
    today = timezone.localdate()
    upcoming_activities = list(
        activities_qs.filter(date__gte=today, status=Activity.STATUS_ACTIVE)
        .order_by("date", "start_time")[:5]
    )
    month_calendar = calendar.monthcalendar(today.year, today.month)
    activity_dates_current_month = sorted({
        a.day
        for a in activities_qs.filter(date__year=today.year, date__month=today.month, status=Activity.STATUS_ACTIVE).values_list("date", flat=True)
    })
    volunteer_options = _build_volunteer_options()
    beneficiary_options = _build_beneficiary_options()
    activity_volunteer_map = _build_activity_volunteer_map(activities_qs)
    activity_beneficiary_map = {
        str(activity.id): [assignment.beneficiary_id for assignment in activity.beneficiary_assignments.all()]
        for activity in activities_qs
    }

    # Build structured JSON for calendar filtering
    upcoming_activities_json = json.dumps([{
        'day': a.date.day,
        'month': a.date.month,
        'year': a.date.year,
        'month_name': a.date.strftime('%b'),
        'title': a.title,
        'time': a.start_time.strftime('%I:%M %p') if a.start_time else 'TBA',
        'location': a.location or 'TBA',
        'category': a.category,
        'category_display': a.get_category_display() or 'Uncategorized',
        'status': a.status,
        'status_display': a.get_status_display(),
    } for a in upcoming_activities])

    return render(request, "admin_dashboard/activities_admin.html", {
        "active_page": "activities",
        "activities": activities_qs,
        "upcoming_activities": upcoming_activities,
        "upcoming_activities_json": upcoming_activities_json,
        "volunteer_options": volunteer_options,
        "beneficiary_options": beneficiary_options,
        "activity_volunteer_map_json": activity_volunteer_map,
        "activity_beneficiary_map_json": activity_beneficiary_map,
        "today": today,
        "current_year": today.year,
        "current_month": today.month,
        "current_month_name": today.strftime("%B"),
        "month_calendar": month_calendar,
        "activity_dates_current_month": activity_dates_current_month,
        "activity_dates": activity_dates_current_month,
        "activity_dates_json": json.dumps(activity_dates_current_month),
        "activity_categories": Activity.CATEGORY_CHOICES,
    })


@login_required(login_url="signin")
@require_POST
def add_activity(request):
    if not request.user.is_superuser:
        return redirect("user_dashboard")

    activity_id = request.POST.get("activityId")
    title = str(request.POST.get("title", "")).strip()
    date_value = request.POST.get("date")
    time_value = request.POST.get("time")
    end_time_value = request.POST.get("end_time")
    location = str(request.POST.get("location", "")).strip()
    category_choice = str(request.POST.get("category", "")).strip()
    custom_category = str(request.POST.get("custom_category", "")).strip()
    description = str(request.POST.get("description", "")).strip()
    status = request.POST.get("status", Activity.STATUS_ACTIVE)
    volunteer_ids = _extract_activity_volunteer_ids(request.POST)
    beneficiary_ids = _extract_activity_beneficiary_ids(request.POST)
    activity_image = request.FILES.get("activity_image")
    remove_activity_image = request.POST.get("remove_activity_image") == "1"

    if status not in {Activity.STATUS_ACTIVE, Activity.STATUS_DRAFT, Activity.STATUS_CANCELLED, Activity.STATUS_COMPLETED}:
        status = Activity.STATUS_ACTIVE
    fixed_categories = {choice[0] for choice in Activity.CATEGORY_CHOICES if choice[0] != Activity.CATEGORY_OTHER}
    if category_choice == Activity.CATEGORY_OTHER:
        category = custom_category
    elif category_choice in fixed_categories:
        category = category_choice
    else:
        category = ""
    if not category:
        return HttpResponse("Category is required.", status=400)

    start_time = None
    if time_value:
        try:
            start_time = datetime.strptime(time_value, "%H:%M").time()
        except ValueError:
            start_time = None

    end_time = None
    if end_time_value:
        try:
            end_time = datetime.strptime(end_time_value, "%H:%M").time()
        except ValueError:
            end_time = None

    if start_time and end_time and end_time <= start_time:
        return HttpResponse("End time must be later than start time.", status=400)

    scheduled_date = _coerce_activity_date(date_value)

    activity = None
    if activity_id:
        try:
            activity = Activity.objects.get(pk=int(activity_id))
        except (ValueError, Activity.DoesNotExist):
            activity = None

    if title and scheduled_date:
        with transaction.atomic():
            if activity:
                activity.title = title
                activity.date = scheduled_date
                activity.start_time = start_time
                activity.end_time = end_time
                activity.location = location
                activity.category = category
                activity.description = description
                activity.status = status
                if activity_image:
                    if activity.image:
                        activity.image.delete(save=False)
                    activity.image = activity_image
                elif remove_activity_image and activity.image:
                    activity.image.delete(save=False)
                    activity.image = None
                activity.save()
            else:
                activity = Activity.objects.create(
                    title=title,
                    date=scheduled_date,
                    start_time=start_time,
                    end_time=end_time,
                    location=location,
                    category=category,
                    description=description,
                    status=status,
                    image=activity_image,
                )

            _sync_activity_volunteer_assignments(activity, volunteer_ids, request.user)
            _sync_activity_beneficiary_assignments(activity, beneficiary_ids, request.user)
            CommunityPost.objects.filter(activity=activity).delete()
            _sync_activity_announcement_notifications(activity, request.user)

    if request.POST.get("return_to") == "dashboard":
        return redirect("admin_dashboard")
    return redirect("activities")


@login_required(login_url="signin")
@require_POST
@require_POST
def delete_activity(request, activity_id):
    if not request.user.is_superuser:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    try:
        with transaction.atomic():
            activity = Activity.objects.get(pk=activity_id)
            activity.delete()
        return JsonResponse({"success": True})
    except Activity.DoesNotExist:
        return JsonResponse({"error": "Activity not found"}, status=404)
    except Exception as e:
        print('Delete error:', e)
        return JsonResponse({"error": str(e)}, status=500)


@login_required(login_url="signin")
def donations(request):
    if not request.user.is_superuser:
        return redirect("user_dashboard")

    _ensure_single_donation_template()

    donations = Donation.objects.all().order_by('-created_at')
    today = date.today()
    donations_data = [{
        'id': d.id,
        'ref': d.reference_number,
        'donor': d.donor_name or 'Anonymous',
        'amount': d.amount,
        'method': d.get_payment_method_display(),
        'status': d.status,
        'campaign': d.campaign,
        'notes': d.donor_message or '',
        'date': d.created_at.strftime('%Y-%m-%d'),
        'receipt': d.receipt.url if d.receipt else '',
        'receipt_url': d.receipt.url if d.receipt else '',
        'official_receipt_url': d.official_receipt_file.url if d.official_receipt_file else '',
        'official_receipt_number': d.official_receipt_number or '',
        'official_receipt_generated_at': d.official_receipt_generated_at.isoformat() if d.official_receipt_generated_at else '',
    } for d in donations]

    recent_activity = [
        {
            'title': f"{(d.donor_name or 'Anonymous').strip() or 'Anonymous'} donated PHP {d.amount:,.2f}",
            'note': _donation_status_label(d.status),
            'time': d.created_at.strftime('%b %d, %Y %I:%M %p'),
        }
        for d in donations[:5]
    ]

    pending_count = donations.filter(status=Donation.STATUS_PENDING).count()
    failed_count = donations.filter(status=Donation.STATUS_REJECTED).count()

    alerts_data = [
        {
            'title': 'Pending Verifications',
            'note': f"{pending_count} donation{'s' if pending_count != 1 else ''} still awaiting confirmation.",
            'tag': 'Verification',
        },
        {
            'title': 'Failed Transactions',
            'note': f"{failed_count} failed donation{'s' if failed_count != 1 else ''} require follow-up.",
            'tag': 'Failure',
        },
    ]

    context = {
        'donations_data': donations_data,
        'total_amount': donations.aggregate(Sum('amount'))['amount__sum'] or 0,
        'this_month': donations.filter(status=Donation.STATUS_VERIFIED, created_at__month=today.month, created_at__year=today.year).aggregate(Sum('amount'))['amount__sum'] or 0,
        'total_donors': donations.values('donor_name').distinct().count(),
        'pending_count': pending_count,
        'failed_count': failed_count,
        'pending_amount': donations.filter(status=Donation.STATUS_PENDING).aggregate(Sum('amount'))['amount__sum'] or 0,
        'verified_amount': donations.filter(status=Donation.STATUS_VERIFIED).aggregate(Sum('amount'))['amount__sum'] or 0,
        'completed_amount': donations.filter(status__in=[Donation.STATUS_VERIFIED, Donation.STATUS_COMPLETED]).aggregate(Sum('amount'))['amount__sum'] or 0,
        'average_donation': donations.aggregate(Avg('amount'))['amount__avg'] or 0,
        'alerts_data': alerts_data,
        'recent_activity': recent_activity,
        'active_page': 'donations',
    }

    return render(request, "admin_dashboard/donation_admin.html", context)


@login_required(login_url="signin")
@require_POST
def bulk_update_donations(request):
    if not request.user.is_superuser:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except ValueError:
        return JsonResponse({"error": "Invalid JSON payload."}, status=400)

    ids = payload.get("ids")
    status_key = str(payload.get("status", "")).strip().lower()
    impact_update = str(payload.get("impact_update", "") or "").strip()

    if not isinstance(ids, (list, tuple)) or not ids:
        return JsonResponse({"error": "Donation ids are required."}, status=400)

    parsed_ids = []
    for item in ids:
        try:
            parsed_ids.append(int(item))
        except (ValueError, TypeError):
            continue

    if not parsed_ids:
        return JsonResponse({"error": "Donation ids are invalid."}, status=400)

    status_map = {
        "verified": Donation.STATUS_VERIFIED,
        "completed": Donation.STATUS_COMPLETED,
        "failed": Donation.STATUS_REJECTED,
        "cancelled": Donation.STATUS_CANCELLED,
    }

    if status_key and status_key not in status_map:
        return JsonResponse({"error": "Invalid status."}, status=400)

    donations = list(Donation.objects.filter(id__in=parsed_ids))
    if status_key:
        Donation.objects.filter(id__in=parsed_ids).update(status=status_map[status_key])
    for donation in donations:
        if status_key:
            donation.status = status_map[status_key]
            if donation.status == Donation.STATUS_VERIFIED:
                donation.verified_at = timezone.now()
                donation.verified_by = request.user
            elif donation.status == Donation.STATUS_REJECTED:
                donation.verified_at = None
                donation.verified_by = None
            donation.save(update_fields=["status", "verified_at", "verified_by", "updated_at"])
        if impact_update:
            _send_donation_impact_update(donation, impact_update, actor=request.user)
        if donation.status in [Donation.STATUS_VERIFIED, Donation.STATUS_COMPLETED]:
            _generate_official_donation_receipt(donation)
            _send_donation_receipt_email(donation)
    return JsonResponse({"success": True})


@login_required(login_url="signin")
def export_donations_csv(request):
        if not request.user.is_superuser:
                return redirect("user_dashboard")

        donations = Donation.objects.all().order_by("-created_at")
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["Date", "Donor", "Amount", "Method", "Status", "Reference Number", "Receipt", "Campaign", "Notes"])

        for donation in donations:
                writer.writerow([
                        timezone.localtime(donation.created_at).strftime("%Y-%m-%d"),
                        (donation.donor_name or "Anonymous").strip() or "Anonymous",
                        donation.amount,
                        _donation_payment_method_label(donation.payment_method),
                        _donation_status_label(donation.status),
                        donation.reference_number,
                        donation.receipt.url if donation.receipt else "",
                        donation.campaign or "General Donation",
                        donation.donor_message or donation.review_notes or "",
                ])

        response = HttpResponse(buffer.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="donations.csv"'
        return response


@login_required(login_url="signin")
def export_donations_pdf(request):
    if not request.user.is_superuser:
        return redirect("user_dashboard")

    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    donations = Donation.objects.all().order_by("-created_at")
    
    # Prepare table data
    data = [["Date", "Donor", "Amount", "Method", "Status", "Reference #", "Campaign"]]
    for donation in donations:
        data.append([
            timezone.localtime(donation.created_at).strftime('%Y-%m-%d'),
            (donation.donor_name or 'Anonymous').strip() or 'Anonymous',
            f"PHP {donation.amount:,.2f}",
            _donation_payment_method_label(donation.payment_method),
            _donation_status_label(donation.status),
            donation.reference_number,
            donation.campaign or 'General Donation',
        ])

    # Create PDF in memory
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    # Build elements
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#14352d'),
        spaceAfter=12,
        alignment=TA_CENTER,
    )
    
    elements = [
        Paragraph("Donation Report", title_style),
        Spacer(1, 0.3*inch),
    ]
    
    # Create and style table
    table = Table(data, colWidths=[1*inch, 1.3*inch, 0.8*inch, 1*inch, 0.8*inch, 1.2*inch, 1.2*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#edf8f3')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#14352d')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#c9ddd6')),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fdfb')]),
    ]))
    elements.append(table)
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="donations.pdf"'
    return response

def _generate_official_donation_receipt(donation):
    if donation.official_receipt_file and donation.official_receipt_generated_at:
        return donation.official_receipt_file

    receipt_number = donation.official_receipt_number or f"HP-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
    donor_display = (donation.donor_name or "").strip() or (donation.user.get_full_name() if donation.user_id else "") or "Anonymous"
    donor_label = donor_display.strip() or "Anonymous"
    payment_label = _donation_payment_method_label(donation.payment_method)
    html = f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <title>Donation Receipt</title>
  <style>
    body {{ font-family: Arial, sans-serif; color: #123528; background: #f5faf7; margin: 0; padding: 24px; }}
    .receipt {{ max-width: 720px; margin: 0 auto; background: white; border: 1px solid #dfeae5; border-radius: 16px; padding: 32px; box-shadow: 0 12px 32px rgba(15, 118, 110, 0.08); }}
    .header {{ border-bottom: 1px solid #e3efe8; padding-bottom: 16px; margin-bottom: 24px; }}
    h1 {{ margin: 0; font-size: 28px; color: #0f766e; }}
    .meta {{ display: grid; grid-template-columns: repeat(2, minmax(180px, 1fr)); gap: 16px; margin-top: 18px; }}
    .meta div {{ background: #f2faf6; border-radius: 10px; padding: 12px 14px; }}
    .label {{ font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; color: #5d7c73; margin-bottom: 8px; display: block; }}
    .value {{ font-size: 16px; font-weight: 700; color: #15372d; }}
    .footer {{ margin-top: 22px; font-size: 12px; color: #5b726a; }}
  </style>
</head>
<body>
  <div class=\"receipt\">
    <div class=\"header\">
      <h1>HappYness Project</h1>
      <p style=\"margin: 8px 0 0; color: #5b726a;\">Donation Receipt</p>
    </div>
    <div class=\"meta\">
      <div><span class=\"label\">Receipt Number</span><span class=\"value\">{receipt_number}</span></div>
      <div><span class=\"label\">Date</span><span class=\"value\">{timezone.localtime(donation.created_at).strftime('%b %d, %Y')}</span></div>
      <div><span class=\"label\">Donor</span><span class=\"value\">{donor_label}</span></div>
      <div><span class=\"label\">Amount</span><span class=\"value\">PHP {donation.amount:,.2f}</span></div>
      <div><span class=\"label\">Payment Method</span><span class=\"value\">{payment_label}</span></div>
      <div><span class=\"label\">Reference</span><span class=\"value\">{donation.reference_number}</span></div>
    </div>
    <div class=\"footer\">
      <p>Thank you for supporting the HappYness Project. This receipt confirms your charitable donation.</p>
    </div>
  </div>
</body>
</html>"""

    donation.official_receipt_number = receipt_number
    donation.official_receipt_generated_at = timezone.now()
    donation.official_receipt_file.save(f"{receipt_number}.html", ContentFile(html.encode("utf-8")), save=False)
    donation.save(update_fields=["official_receipt_number", "official_receipt_file", "official_receipt_generated_at", "updated_at"])
    return donation.official_receipt_file


def _send_donation_receipt_email(donation):
    if not donation.donor_email:
        return False
    try:
        from django.conf import settings as _conf
        absolute_link = django_settings.BASE_URL if hasattr(django_settings, 'BASE_URL') else 'https://example.com'
        receipt_url = absolute_link.rstrip('/') + reverse('download_donation_receipt', args=[donation.reference_number]) + f"?email={urllib.parse.quote(donation.donor_email)}"
        html_body = f"""
        <html><body style=\"font-family:Arial,sans-serif; background:#f5faf7; padding:24px; color:#123528;\">
        <div style=\"max-width:620px; margin:0 auto; background:#fff; border:1px solid #dfeae5; border-radius:12px; padding:26px;\">
          <h2 style=\"color:#0f766e; margin-top:0;\">Thank you for your donation</h2>
          <p>Your donation has been confirmed. Your official donation receipt is ready.</p>
          <p><a href=\"{receipt_url}\" style=\"color:#0f766e; font-weight:700;\">Download your receipt</a></p>
          <p style=\"color:#5b726a; margin-top:18px; font-size:12px;\">Receipt Number: {donation.official_receipt_number or donation.reference_number}</p>
        </div>
        </body></html>
        """
        plain_body = (
            f"Hi {donation.donor_name or 'Donor'},\n\n"
            f"Your donation has been confirmed. Download your official receipt here:\n{receipt_url}\n\n"
            "Thank you for supporting HappYness Project."
        )
        msg = EmailMultiAlternatives(
            subject="Your donation receipt from HappYness Project",
            body=plain_body,
            from_email=_conf.DEFAULT_FROM_EMAIL,
            to=[donation.donor_email],
        )
        msg.attach_alternative(html_body, "text/html")
        msg.send()
        return True
    except Exception as exc:
        print(f"[donation_receipt_email] failed: {exc}")
        return False


@require_GET
def download_donation_receipt(request, reference_number):
    donation = get_object_or_404(Donation, reference_number=reference_number)
    is_owner = request.user.is_authenticated and donation.user_id and donation.user_id == request.user.id
    email_match = False
    if not is_owner:
        submitted_email = str(request.GET.get("email", "")).strip().lower()
        email_match = bool(submitted_email) and donation.donor_email and donation.donor_email.lower() == submitted_email
    if not (request.user.is_superuser or is_owner or email_match):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    if donation.official_receipt_file:
        filename = f"{donation.reference_number}-receipt.html"
        response = FileResponse(donation.official_receipt_file.open("rb"), as_attachment=True, filename=filename)
        return response

    if donation.status not in [Donation.STATUS_VERIFIED, Donation.STATUS_COMPLETED]:
        raise Http404("Receipt is not available until the donation is confirmed.")

    _generate_official_donation_receipt(donation)
    response = FileResponse(donation.official_receipt_file.open("rb"), as_attachment=True, filename=f"{donation.reference_number}-receipt.html")
    return response


@require_POST
def submit_donation(request):
    donor_name = str(request.POST.get("donor_name", "")).strip()
    donor_email = str(request.POST.get("donor_email", "")).strip()
    donor_message = str(request.POST.get("donor_message", "")).strip()
    campaign = str(request.POST.get("campaign", "")).strip() or "General Donation"
    payment_method = str(request.POST.get("payment_method", "")).strip()
    amount_raw = request.POST.get("amount", request.POST.get("custom_amount", ""))
    receipt = request.FILES.get("receipt") or request.FILES.get("donateReceipt") or request.FILES.get("payment_screenshot")
    requested_status = str(request.POST.get("status", "")).strip().lower()

    if payment_method not in {Donation.PAYMENT_GCASH, Donation.PAYMENT_BANK_TRANSFER}:
        return JsonResponse({"error": "Please choose a valid payment method."}, status=400)

    amount = _parse_non_negative_int(amount_raw, default=0)
    if amount <= 0:
        return JsonResponse({"error": "Please enter a valid donation amount."}, status=400)

    if not receipt:
        return JsonResponse({"error": "Please attach a receipt."}, status=400)

    max_receipt_size = getattr(django_settings, "DONATION_RECEIPT_MAX_SIZE_BYTES", 5 * 1024 * 1024)
    allowed_receipt_types = getattr(django_settings, "DONATION_RECEIPT_MIME_TYPES", {"application/pdf", "image/jpeg", "image/png", "image/webp"})
    if getattr(receipt, "size", 0) > max_receipt_size:
        return JsonResponse({"error": "The receipt must be 5 MB or smaller."}, status=400)
    receipt.seek(0)
    file_header = receipt.read(12)
    receipt.seek(0)
    if file_header.startswith(b"%PDF-"):
        detected_content_type = "application/pdf"
    elif file_header.startswith(b"\xff\xd8\xff"):
        detected_content_type = "image/jpeg"
    elif file_header.startswith(b"\x89PNG\r\n\x1a\n"):
        detected_content_type = "image/png"
    elif file_header.startswith(b"RIFF") and file_header[8:12] == b"WEBP":
        detected_content_type = "image/webp"
    else:
        detected_content_type = ""
    if detected_content_type not in allowed_receipt_types:
        return JsonResponse({"error": "The uploaded receipt is invalid."}, status=400)

    if not request.user.is_authenticated:
        donor_name = ""

    if request.user.is_authenticated and request.user.is_superuser and requested_status in dict(Donation.STATUS_CHOICES):
        status = requested_status
    else:
        status = Donation.STATUS_PENDING

    donation = Donation(
        user=request.user if request.user.is_authenticated else None,
        donor_name=donor_name,
        donor_email=donor_email or (request.user.email if request.user.is_authenticated else ""),
        donor_message=donor_message,
        campaign=campaign,
        amount=amount,
        payment_method=payment_method,
        status=status,
    )

    if receipt:
        donation.receipt = receipt

    try:
        donation.save()
    except ValidationError as exc:
        return JsonResponse({"error": "; ".join(exc.messages)}, status=400)
    except Exception as exc:
        print(f"Unexpected error saving Donation: {type(exc).__name__}: {exc}")
        return JsonResponse({"error": "Unable to save donation. Please try again."}, status=500)

    return JsonResponse({
        "message": "Donation received.",
        "donation": _serialize_donation(donation),
    }, status=201)




@login_required(login_url="signin")
def payment(request):
    if not request.user.is_superuser:
        return redirect("user_dashboard")

    _ensure_single_payment_template()

    inquiries = ProductInquiry.objects.all().order_by('-created_at')
    method_labels = dict(ProductInquiry.PAYMENT_METHOD_CHOICES)

    payments_json = [{
        'id': inq.id,
        'orderId': f"ORD-{inq.id:04d}",
        'customer': inq.full_name,
        'email': inq.email,
        'phone': inq.phone,
        'amount': inq.order_total,
        'method': method_labels.get(inq.payment_method, inq.payment_method),
        'status': inq.status.title(),
        'paymentDate': inq.created_at.strftime('%Y-%m-%d'),
        'reference': f"PI-{inq.id:05d}",
        'orderItems': inq.order_items,
        'screenshot': inq.payment_screenshot.url if inq.payment_screenshot else '',
        'delivery_street': inq.delivery_street or '',
        'delivery_city': inq.delivery_city or '',
        'delivery_province': inq.delivery_province or '',
        'delivery_zip': inq.delivery_zip or '',
        'delivery_country': inq.delivery_country or '',
        'details': [
            f"Items: {len(inq.order_items or [])} product(s)",
            f"Method: {method_labels.get(inq.payment_method, inq.payment_method)}",
        ],
        'logs': [f"Order submitted on {inq.created_at.strftime('%Y-%m-%d')}"],
    } for inq in inquiries]

    _confirmed_statuses = [ProductInquiry.STATUS_VERIFIED, ProductInquiry.STATUS_COMPLETED]
    _risk_statuses = [ProductInquiry.STATUS_FAILED, ProductInquiry.STATUS_REFUNDED, ProductInquiry.STATUS_CANCELLED]
    confirmed_count = inquiries.filter(status__in=_confirmed_statuses).count()
    pending_count = inquiries.filter(status=ProductInquiry.STATUS_PENDING).count()
    risk_count = inquiries.filter(status__in=_risk_statuses).count()
    total_revenue = inquiries.filter(status__in=_confirmed_statuses).aggregate(Sum('order_total'))['order_total__sum'] or 0

    return render(request, "admin_dashboard/payment_admin.html", {
        "active_page": "payment",
        "payments_json": payments_json,
        "pending_count": pending_count,
        "confirmed_count": confirmed_count,
        "risk_count": risk_count,
        "total_revenue": total_revenue,
    })


@login_required(login_url="signin")
@require_POST
def payment_verify(request, inquiry_id):
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Forbidden'}, status=403)
    inquiry = get_object_or_404(ProductInquiry, id=inquiry_id)
    ProductInquiry.objects.filter(id=inquiry_id).update(status=ProductInquiry.STATUS_VERIFIED)

    try:
        from django.conf import settings as _conf
        html_body = _build_order_confirmation_email_html(inquiry)
        plain_body = (
            f"Hi {inquiry.full_name},\n\n"
            f"Your order (ORD-{inquiry.id:04d} / PI-{inquiry.id:05d}) has been confirmed!\n\n"
            f"Payment Method: Cash on Delivery\n"
            f"Order Total: PHP {inquiry.order_total:,}\n\n"
            "Thank you for supporting Happy Nanays! Your order is now being prepared.\n\n"
            "— HappYness Project"
        )
        msg = EmailMultiAlternatives(
            subject="Your order has been confirmed! \U0001f389 - HappYness Project",
            body=plain_body,
            from_email=_conf.DEFAULT_FROM_EMAIL,
            to=[inquiry.email],
        )
        msg.attach_alternative(html_body, "text/html")
        msg.send()
    except Exception as exc:
        print(f"[payment_verify] Email send failed for inquiry {inquiry_id}: {exc}")

    return JsonResponse({'ok': True, 'status': 'Verified'})


@login_required(login_url="signin")
@require_POST
def payment_mark_paid(request, inquiry_id):
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Forbidden'}, status=403)
    updated = ProductInquiry.objects.filter(id=inquiry_id).update(status=ProductInquiry.STATUS_COMPLETED)
    if not updated:
        return JsonResponse({'error': 'Not found'}, status=404)
    return JsonResponse({'ok': True, 'status': 'Completed'})


@login_required(login_url="signin")
@require_POST
def payment_mark_failed(request, inquiry_id):
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Forbidden'}, status=403)
    updated = ProductInquiry.objects.filter(id=inquiry_id).update(status=ProductInquiry.STATUS_FAILED)
    if not updated:
        return JsonResponse({'error': 'Not found'}, status=404)
    return JsonResponse({'ok': True, 'status': 'Failed'})


@login_required(login_url="signin")
@require_POST
def payment_refund(request, inquiry_id):
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Forbidden'}, status=403)
    updated = ProductInquiry.objects.filter(id=inquiry_id).update(status=ProductInquiry.STATUS_REFUNDED)
    if not updated:
        return JsonResponse({'error': 'Not found'}, status=404)
    return JsonResponse({'ok': True, 'status': 'Refunded'})


@login_required(login_url="signin")
@require_POST
def payment_delete(request, inquiry_id):
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Forbidden'}, status=403)
    inquiry = get_object_or_404(ProductInquiry, id=inquiry_id)
    inquiry.delete()
    return JsonResponse({'ok': True})


@login_required(login_url="signin")
def inventory(request):
    if not request.user.is_superuser:
        return redirect("user_dashboard")

    _ensure_single_inventory_template()

    items = InventoryItem.objects.all().order_by('-updated_at', '-id')
    
    # Get recent stock movements for chart
    recent_movements = StockMovement.objects.select_related('item').order_by('-created_at')[:50]
    movement_data = []
    for movement in recent_movements:
        movement_data.append({
            'date': movement.created_at.strftime('%Y-%m-%d'),
            'item': movement.item.name,
            'action': movement.action,
            'quantity': movement.quantity,
            'reason': movement.reason or '',
        })
    
    inventory_data = [{
        'id': item.id,
        'sku': f"INV-{item.id:04d}",
        'name': item.name,
        'category': item.category,
        'sub_category': item.sub_category or '',
        'quantity': item.stock,
        'unit': item.unit,
        'status': item.status,
        'reorderLevel': item.low_stock_threshold,
        'lastUpdated': item.updated_at.strftime('%Y-%m-%d'),
        'price': float(item.price) if item.price else 0,
        'description': item.description or '',
        'movementHistory': [],
        'updateLogs': [],
    } for item in items]

    total_value = sum(
        (float(item.price) if item.price else 0) * item.stock
        for item in items
    )
    
    low_stock_count = sum(1 for item in items if item.status == 'low_stock')
    out_of_stock_count = sum(1 for item in items if item.status == 'out_of_stock')
    total_units = sum(item.stock for item in items)

    return render(request, "admin_dashboard/inventory_admin.html", {
        "active_page": "inventory",
        "inventory_data": inventory_data,
        "movement_data": movement_data,
        "total_items": items.count(),
        "total_value": int(total_value),
        "low_stock_count": low_stock_count,
        "out_of_stock_count": out_of_stock_count,
        "total_units": total_units,
    })


@login_required(login_url="signin")
@require_POST
def inventory_add(request):
    if not request.user.is_superuser:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except ValueError:
        return JsonResponse({"error": "Invalid JSON payload."}, status=400)

    name = str(payload.get("name", "")).strip()
    category = str(payload.get("category", "")).strip()
    sub_category = str(payload.get("sub_category", "")).strip()
    unit = str(payload.get("unit", "pcs")).strip()
    stock = _parse_non_negative_int(payload.get("stock"), default=0)
    low_stock_threshold = _parse_non_negative_int(payload.get("low_stock_threshold"), default=10)
    price = payload.get("price")
    description = str(payload.get("description", "")).strip()

    if not name:
        return JsonResponse({"error": "Item name is required."}, status=400)

    if category not in dict(InventoryItem.CATEGORY_CHOICES):
        return JsonResponse({"error": "Invalid category."}, status=400)

    if price is not None:
        try:
            price = float(price) if price else None
        except (ValueError, TypeError):
            price = None

    item = InventoryItem.objects.create(
        name=name,
        category=category,
        sub_category=sub_category or None,
        unit=unit,
        stock=stock,
        low_stock_threshold=low_stock_threshold,
        price=price,
        description=description,
    )

    return JsonResponse({
        "message": "Item added successfully.",
        "item": {
            "id": item.id,
            "sku": f"INV-{item.id:04d}",
            "name": item.name,
            "category": item.category,
            "sub_category": item.sub_category or '',
            "quantity": item.stock,
            "unit": item.unit,
            "status": item.status,
            "reorderLevel": item.low_stock_threshold,
            "lastUpdated": item.updated_at.strftime('%Y-%m-%d'),
            "price": float(item.price) if item.price else 0,
        },
    }, status=201)


@login_required(login_url="signin")
@require_POST
def inventory_edit(request, item_id):
    if not request.user.is_superuser:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    item = get_object_or_404(InventoryItem, pk=item_id)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except ValueError:
        return JsonResponse({"error": "Invalid JSON payload."}, status=400)

    name = str(payload.get("name", "")).strip()
    category = str(payload.get("category", "")).strip()
    sub_category = str(payload.get("sub_category", "")).strip()
    unit = str(payload.get("unit", "")).strip()
    low_stock_threshold = _parse_non_negative_int(payload.get("low_stock_threshold"))
    price = payload.get("price")
    description = str(payload.get("description", "")).strip()

    if name:
        item.name = name
    if category and category in dict(InventoryItem.CATEGORY_CHOICES):
        item.category = category
    if sub_category or sub_category == "":
        item.sub_category = sub_category or None
    if unit:
        item.unit = unit
    if low_stock_threshold is not None:
        item.low_stock_threshold = low_stock_threshold
    if price is not None:
        try:
            item.price = float(price) if price else None
        except (ValueError, TypeError):
            pass
    if description or description == "":
        item.description = description

    item.save()

    return JsonResponse({
        "message": "Item updated successfully.",
        "item": {
            "id": item.id,
            "sku": f"INV-{item.id:04d}",
            "name": item.name,
            "category": item.category,
            "sub_category": item.sub_category or '',
            "quantity": item.stock,
            "unit": item.unit,
            "status": item.status,
            "reorderLevel": item.low_stock_threshold,
            "lastUpdated": item.updated_at.strftime('%Y-%m-%d'),
            "price": float(item.price) if item.price else 0,
        },
    })


@login_required(login_url="signin")
@require_POST
def inventory_restock(request, item_id):
    if not request.user.is_superuser:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    item = get_object_or_404(InventoryItem, pk=item_id)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except ValueError:
        return JsonResponse({"error": "Invalid JSON payload."}, status=400)

    quantity = _parse_non_negative_int(payload.get("quantity"), default=0)
    if quantity <= 0:
        return JsonResponse({"error": "Quantity must be greater than zero."}, status=400)

    item.stock += quantity
    item.save()

    # Log the stock movement
    StockMovement.objects.create(
        item=item,
        action=StockMovement.ACTION_RESTOCK,
        quantity=quantity,
        reason=payload.get("reason", "").strip() or None,
    )

    return JsonResponse({
        "message": f"Item restocked with {quantity} units.",
        "item": {
            "id": item.id,
            "sku": f"INV-{item.id:04d}",
            "name": item.name,
            "category": item.category,
            "quantity": item.stock,
            "unit": item.unit,
            "status": item.status,
            "lastUpdated": item.updated_at.strftime('%Y-%m-%d'),
        },
    })


@login_required(login_url="signin")
@require_POST
def inventory_deduct(request, item_id):
    if not request.user.is_superuser:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    item = get_object_or_404(InventoryItem, pk=item_id)
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except ValueError:
        return JsonResponse({"error": "Invalid JSON payload."}, status=400)

    quantity = _parse_non_negative_int(payload.get("quantity"), default=0)
    if quantity <= 0:
        return JsonResponse({"error": "Quantity must be greater than zero."}, status=400)

    if quantity > item.stock:
        return JsonResponse({"error": "Quantity cannot exceed current stock."}, status=400)

    item.stock -= quantity
    item.save()

    # Log the stock movement
    StockMovement.objects.create(
        item=item,
        action=StockMovement.ACTION_DEDUCT,
        quantity=quantity,
        reason=payload.get("reason", "").strip() or None,
    )

    return JsonResponse({
        "message": f"Item deducted by {quantity} units.",
        "item": {
            "id": item.id,
            "sku": f"INV-{item.id:04d}",
            "name": item.name,
            "category": item.category,
            "quantity": item.stock,
            "unit": item.unit,
            "status": item.status,
            "lastUpdated": item.updated_at.strftime('%Y-%m-%d'),
        },
    })


@login_required(login_url="signin")
@require_POST
def inventory_delete(request, item_id):
    if not request.user.is_superuser:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    item = get_object_or_404(InventoryItem, pk=item_id)
    item_name = item.name
    item.delete()

    return JsonResponse({
        "message": f"Item '{item_name}' deleted successfully.",
        "deleted_item_id": item_id,
    })


@login_required(login_url="signin")
def announcements(request):
    if not request.user.is_superuser:
        return redirect("user_dashboard")

    _ensure_single_announcements_template()

    return render(request, "admin_dashboard/announcements_admin.html", {
        "active_page": "announcements",
    })


@login_required(login_url="signin")
def community_posts(request):
    if not request.user.is_superuser:
        return redirect("user_dashboard")

    _ensure_single_community_posts_template()

    return render(request, "admin_dashboard/community_posts_admin.html", {
        "active_page": "community_posts",
        "dashboard_scope": "admin",
        "base_template": "base.html",
    })


@login_required(login_url="signin")
def feedback(request):
    if not request.user.is_superuser:
        return redirect("user_dashboard")

    _ensure_single_feedback_template()

    return render(request, "admin_dashboard/feedback_admin.html", {
        "active_page": "feedback",
    })


@login_required(login_url="signin")
def moderation(request):
    if not request.user.is_superuser:
        return redirect("user_dashboard")

    _ensure_single_moderation_template()

    return render(request, "admin_dashboard/moderation_admin.html", {
        "active_page": "moderation",
    })


def _analytics_range_window(range_key):
    today = timezone.now().date()
    if range_key == "90d":
        start = today - timedelta(days=89)
    elif range_key == "12m":
        month_index = today.year * 12 + today.month - 12
        start_year, start_month = divmod(month_index, 12)
        start = date(start_year, start_month + 1, 1)
    else:
        start = today - timedelta(days=29)
    return start, today


def _reports_account_role_rows():
    active_members = User.objects.filter(is_active=True, is_staff=False, is_superuser=False)
    regular_users = active_members.filter(
        Q(userprofile__account_role=UserProfile.ROLE_REGULAR)
        | Q(userprofile__account_role__isnull=True)
        | Q(userprofile__account_role="")
    ).count()
    beneficiaries = active_members.filter(userprofile__account_role=UserProfile.ROLE_BENEFICIARY).count()
    volunteers = active_members.filter(userprofile__account_role=UserProfile.ROLE_VOLUNTEER).count()
    return [
        ("Regular users", regular_users),
        ("Beneficiaries", beneficiaries),
        ("Volunteers", volunteers),
    ]


def _analytics_previous_window(range_key):
    start, end = _analytics_range_window(range_key)
    duration = (end - start).days + 1
    previous_end = start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=duration - 1)
    return previous_start, previous_end


def _analytics_bucket_labels(range_key):
    start, end = _analytics_range_window(range_key)
    if range_key == "12m":
        return [
            f"{calendar.month_abbr[(start.month - 1 + offset) % 12 + 1]} {str(start.year + (start.month - 1 + offset) // 12)[-2:]}"
            for offset in range(12)
        ]

    bucket_days = 30 if range_key == "90d" else 7
    bucket_count = 3 if range_key == "90d" else 5
    labels = []
    for index in range(bucket_count):
        bucket_start = start + timedelta(days=index * bucket_days)
        bucket_end = min(bucket_start + timedelta(days=bucket_days - 1), end)
        labels.append(f"{bucket_start:%b %d}–{bucket_end:%b %d}")
    return labels


def _analytics_bucket_index(range_key, bucket_date):
    start, end = _analytics_range_window(range_key)
    delta = (bucket_date - start).days
    if range_key == "90d":
        return min(max(delta // 30, 0), 2)
    if range_key == "12m":
        return min(max((bucket_date.year - start.year) * 12 + bucket_date.month - start.month, 0), 11)
    return min(max(delta // 7, 0), 4)


def _serialize_reports_record(date_obj, category, metric, detail, value):
    return {
        "date": date_obj.isoformat() if hasattr(date_obj, "isoformat") else str(date_obj),
        "category": category,
        "metric": metric,
        "detail": detail,
        "value": value,
    }


def _reports_category_metadata():
    return {
        "all": "All record types",
        "donation": "Donations",
        "volunteer": "Volunteer attendance",
        "activity": "Activities",
        "assistance": "Beneficiary assistance",
    }


def _reports_analytics_payload(range_key="30d", category="all", campaign="", record_limit=25):
    if range_key not in {"30d", "90d", "12m"}:
        range_key = "30d"
    if category not in {"all", "donation", "volunteer", "activity", "assistance"}:
        category = "all"

    start, end = _analytics_range_window(range_key)
    labels = _analytics_bucket_labels(range_key)
    records = []

    all_donations = Donation.objects.filter(
        created_at__date__gte=start,
        created_at__date__lte=end,
        status__in=[Donation.STATUS_VERIFIED, Donation.STATUS_COMPLETED],
    )
    campaign_options = all_donations.values_list("campaign", flat=True).distinct().order_by("campaign")
    donations = all_donations
    if category not in {"all", "donation"}:
        donations = donations.none()
    if campaign:
        donations = donations.filter(campaign=campaign)

    volunteer_attendance = VolunteerAttendanceRecord.objects.filter(
        status=VolunteerAttendanceRecord.STATUS_CONFIRMED,
        time_out__isnull=False,
        time_out__date__gte=start,
        time_out__date__lte=end,
    )
    if category not in {"all", "volunteer"}:
        volunteer_attendance = volunteer_attendance.none()

    activities = Activity.objects.filter(
        date__gte=start,
        date__lte=end,
        status=Activity.STATUS_COMPLETED,
    )
    if category not in {"all", "activity"}:
        activities = activities.none()

    assistance_records = BeneficiaryAssistanceRecord.objects.filter(
        assistance_date__gte=start,
        assistance_date__lte=end,
    )
    if category not in {"all", "assistance"}:
        assistance_records = assistance_records.none()

    for donation in donations.select_related("user").order_by("-created_at"):
        payment_label = dict(Donation.PAYMENT_METHOD_CHOICES).get(donation.payment_method, donation.payment_method)
        status_label = dict(Donation.STATUS_CHOICES).get(donation.status, donation.status)
        records.append(_serialize_reports_record(
            donation.created_at.date(),
            "donation",
            donation.campaign.strip() or "No campaign recorded",
            f"{payment_label} · {status_label}",
            f"₱{donation.amount:,.0f}",
        ))

    for attendance in volunteer_attendance.select_related("volunteer", "assignment").order_by("-time_out"):
        volunteer_name = (
            f"{attendance.volunteer.first_name} {attendance.volunteer.last_name}".strip()
            or attendance.volunteer.username
        )
        records.append(_serialize_reports_record(
            attendance.time_out.date(),
            "volunteer",
            attendance.assignment.activity_name or "Volunteer assignment",
            volunteer_name,
            f"{(attendance.duration_minutes or 0) / 60:.1f} hours",
        ))

    activity_categories = dict(Activity.CATEGORY_CHOICES)
    for activity in activities.order_by("-date", "title"):
        category_label = activity_categories.get(activity.category, activity.category or "Uncategorized")
        records.append(_serialize_reports_record(
            activity.date,
            "activity",
            activity.title,
            f"{category_label} · Completed",
            f"{activity.volunteer_count} {'volunteer' if activity.volunteer_count == 1 else 'volunteers'}",
        ))

    for record in assistance_records.select_related("beneficiary").order_by("-assistance_date", "-created_at"):
        records.append(_serialize_reports_record(
            record.assistance_date,
            "assistance",
            record.aid_type,
            record.beneficiary.full_name or "Beneficiary",
            record.quantity_or_amount,
        ))

    records.sort(key=lambda item: item["date"], reverse=True)
    donations_per_bucket = {label: 0 for label in labels}
    volunteer_minutes_per_bucket = {label: 0 for label in labels}
    volunteer_records_per_bucket = {label: 0 for label in labels}
    activities_per_bucket = {label: 0 for label in labels}
    assistance_per_bucket = {label: 0 for label in labels}

    for donation in donations:
        label = labels[_analytics_bucket_index(range_key, donation.created_at.date())]
        donations_per_bucket[label] += donation.amount
    for attendance in volunteer_attendance:
        label = labels[_analytics_bucket_index(range_key, attendance.time_out.date())]
        volunteer_minutes_per_bucket[label] += attendance.duration_minutes or 0
        volunteer_records_per_bucket[label] += 1
    for activity in activities:
        label = labels[_analytics_bucket_index(range_key, activity.date)]
        activities_per_bucket[label] += 1
    for record in assistance_records:
        label = labels[_analytics_bucket_index(range_key, record.assistance_date)]
        assistance_per_bucket[label] += 1

    donation_total = donations.aggregate(total=Sum("amount"))["total"] or 0
    volunteer_minutes = volunteer_attendance.aggregate(total=Sum("duration_minutes"))["total"] or 0
    volunteer_count = volunteer_attendance.values("volunteer_id").distinct().count()
    activity_count = activities.count()
    assistance_count = assistance_records.count()
    account_role_rows = _reports_account_role_rows()

    previous_start, previous_end = _analytics_previous_window(range_key)
    previous_donations = Donation.objects.filter(
        created_at__date__gte=previous_start,
        created_at__date__lte=previous_end,
        status__in=[Donation.STATUS_VERIFIED, Donation.STATUS_COMPLETED],
    )
    previous_volunteers = VolunteerAttendanceRecord.objects.filter(
        status=VolunteerAttendanceRecord.STATUS_CONFIRMED,
        time_out__isnull=False,
        time_out__date__gte=previous_start,
        time_out__date__lte=previous_end,
    )
    previous_activities = Activity.objects.filter(
        date__gte=previous_start,
        date__lte=previous_end,
        status=Activity.STATUS_COMPLETED,
    )
    previous_assistance = BeneficiaryAssistanceRecord.objects.filter(
        assistance_date__gte=previous_start,
        assistance_date__lte=previous_end,
    )

    if category not in {"all", "donation"}:
        previous_donations = previous_donations.none()
    if category not in {"all", "volunteer"}:
        previous_volunteers = previous_volunteers.none()
    if category not in {"all", "activity"}:
        previous_activities = previous_activities.none()
    if category not in {"all", "assistance"}:
        previous_assistance = previous_assistance.none()
    if campaign:
        previous_donations = previous_donations.filter(campaign=campaign)

    def percent_change(current, previous):
        if not previous:
            return None
        return round(((current - previous) / previous) * 100, 1)

    donor_summary = donations.values("donor_name", "user__username").annotate(
        total=Sum("amount")
    ).order_by("-total").first()
    top_donor = {"name": "No verified donations", "meta": "No finalized donation records in this period"}
    if donor_summary:
        donor_name = donor_summary["donor_name"] or donor_summary["user__username"] or "Anonymous donor"
        top_donor = {"name": donor_name, "meta": f"₱{donor_summary['total']:,.0f} in finalized donations"}

    top_ojt_volunteer = {
        "name": "No OJT progress recorded",
        "meta": "No active volunteer has logged OJT hours",
    }
    top_ojt_progress = 0
    active_volunteer_profiles = UserProfile.objects.filter(
        account_role=UserProfile.ROLE_VOLUNTEER,
        user__is_active=True,
        user__is_staff=False,
        user__is_superuser=False,
    ).select_related("user")
    for profile in active_volunteer_profiles:
        ojt_hours = float(profile.ojt_hours or 0)
        required_hours = float(profile.required_ojt_hours or 80)
        if ojt_hours <= 0 or required_hours <= 0:
            continue
        progress = ojt_hours / required_hours
        if progress <= top_ojt_progress:
            continue

        volunteer_name = (
            f"{profile.user.first_name or ''} {profile.user.last_name or ''}".strip()
            or profile.user.username
        )
        if ojt_hours >= required_hours:
            progress_label = f"{ojt_hours:.1f} of {required_hours:.1f} OJT hours · target reached"
        else:
            progress_label = f"{ojt_hours:.1f} of {required_hours:.1f} OJT hours · {progress * 100:.1f}% complete"
        top_ojt_volunteer = {"name": volunteer_name, "meta": progress_label}
        top_ojt_progress = progress

    payment_methods = dict(Donation.PAYMENT_METHOD_CHOICES)
    chart_payment_methods = (Donation.PAYMENT_GCASH, Donation.PAYMENT_BANK_TRANSFER)
    distribution = {
        "labels": [payment_methods[method] for method in chart_payment_methods],
        "values": [donations.filter(payment_method=method).count() for method in chart_payment_methods],
    }
    series = {
        "labels": labels,
        "donations": [donations_per_bucket[label] for label in labels],
        "volunteerHours": [round(volunteer_minutes_per_bucket[label] / 60, 1) for label in labels],
        "operationalRecords": [
            volunteer_records_per_bucket[label] + activities_per_bucket[label] + assistance_per_bucket[label]
            for label in labels
        ],
        "activities": [activities_per_bucket[label] for label in labels],
        "assistance": [assistance_per_bucket[label] for label in labels],
        "kpis": {
            "totalDonations": {
                "value": donation_total,
                "count": donations.count(),
                "change": percent_change(donation_total, previous_donations.aggregate(total=Sum("amount"))["total"] or 0),
            },
            "volunteerHours": {
                "value": round(volunteer_minutes / 60, 1),
                "volunteers": volunteer_count,
                "change": percent_change(volunteer_minutes, previous_volunteers.aggregate(total=Sum("duration_minutes"))["total"] or 0),
            },
            "completedActivities": {
                "value": activity_count,
                "change": percent_change(activity_count, previous_activities.count()),
            },
            "assistanceRecords": {
                "value": assistance_count,
                "change": percent_change(assistance_count, previous_assistance.count()),
            },
        },
        "insights": {"topDonor": top_donor, "topOjtVolunteer": top_ojt_volunteer},
    }

    return {
        "series": {range_key: series},
        "distribution": distribution,
        "records": records if record_limit is None else records[:record_limit],
        "recordCount": len(records),
        "accounts": {
            "labels": [label for label, _count in account_role_rows],
            "values": [count for _label, count in account_role_rows],
        },
        "campaigns": [
            {"value": value, "label": value.strip() or "No campaign recorded"}
            for value in campaign_options
        ],
    }


@require_GET
@login_required(login_url="signin")
def reports_data_api(request):
    if not request.user.is_superuser:
        return JsonResponse({"error": "Only administrators can access the analytics data."}, status=403)

    range_key = request.GET.get("range", "30d")
    category = request.GET.get("category", "all")
    campaign = request.GET.get("campaign", "")
    payload = _reports_analytics_payload(range_key, category, campaign)
    payload["categories"] = [
        {"value": key, "label": label}
        for key, label in _reports_category_metadata().items()
    ]
    return JsonResponse(payload)


def _analytics_export_sections(payload, range_key, category, campaign):
    series = payload["series"][range_key]
    period_labels = {"30d": "Last 30 days", "90d": "Last 90 days", "12m": "Last 12 months"}
    category_label = _reports_category_metadata().get(category, "All record types")
    filter_label = campaign if campaign and category in {"all", "donation"} else category_label
    return period_labels[range_key], filter_label, [
        ("Summary", ["Metric", "Value", "Notes"], [
            ["Finalized donations", f"PHP {series['kpis']['totalDonations']['value']:,.2f}", f"{series['kpis']['totalDonations']['count']} records"],
            ["Volunteer hours", f"{series['kpis']['volunteerHours']['value']:.1f}", f"{series['kpis']['volunteerHours']['volunteers']} volunteers with confirmed check-outs"],
            ["Completed activities", series["kpis"]["completedActivities"]["value"], ""],
            ["Beneficiary assistance", series["kpis"]["assistanceRecords"]["value"], "Dated assistance records"],
        ]),
        ("Active accounts by role", ["Account type", "Active accounts"], [
            [label, value]
            for label, value in zip(payload["accounts"]["labels"], payload["accounts"]["values"])
        ]),
        ("Trend", ["Period", "Donations (PHP)", "Managed service records"], [
            [label, f"PHP {series['donations'][index]:,.2f}", series["operationalRecords"][index]]
            for index, label in enumerate(series["labels"])
        ]),
        ("Payment methods", ["Method", "Finalized donations"], [
            [label, value]
            for label, value in zip(payload["distribution"]["labels"], payload["distribution"]["values"])
        ]),
        ("Filtered records", ["Date", "Record type", "Record", "Details", "Value"], [
            [record["date"], record["category"], record["metric"], record["detail"], record["value"]]
            for record in payload["records"]
        ]),
    ]


@login_required(login_url="signin")
@require_POST
def reports_export(request):
    if not request.user.is_superuser:
        return JsonResponse({"error": "Only administrators can export analytics reports."}, status=403)

    range_key = request.POST.get("range", "30d")
    category = request.POST.get("category", "all")
    campaign = request.POST.get("campaign", "")
    output_format = request.POST.get("format", "csv").lower()
    if range_key not in {"30d", "90d", "12m"}:
        return JsonResponse({"error": "Choose a valid reporting period."}, status=400)
    if category not in {"all", "donation", "volunteer", "activity", "assistance"}:
        return JsonResponse({"error": "Choose a valid record type."}, status=400)
    if output_format not in {"csv", "pdf"}:
        return JsonResponse({"error": "Choose CSV or PDF format."}, status=400)

    if category not in {"all", "donation"}:
        campaign = ""
    payload = _reports_analytics_payload(range_key, category, campaign, record_limit=None)
    period_label, filter_label, sections = _analytics_export_sections(payload, range_key, category, campaign)
    filename = f"analytics_{range_key}_{timezone.localdate().isoformat()}.{output_format}"

    if output_format == "csv":
        buffer = io.StringIO(newline="")
        writer = csv.writer(buffer)
        writer.writerow(["Analytics report", period_label])
        writer.writerow(["Selected filters", filter_label])
        for section_title, headers, rows in sections:
            writer.writerow([section_title])
            writer.writerow(headers)
            writer.writerows([_csv_safe_value(value) for value in row] for row in rows)
        response = HttpResponse(buffer.getvalue().encode("utf-8-sig"), content_type="text/csv; charset=utf-8")
    else:
        response = HttpResponse(
            _export_analytics_pdf(period_label, filter_label, sections),
            content_type="application/pdf",
        )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required(login_url="signin")
def reports(request):
    if not request.user.is_superuser:
        return redirect("user_dashboard")

    return render(request, "admin_dashboard/reports_admin.html", {
        "active_page": "reports",
    })


@login_required(login_url="signin")
def reports2(request):
    if not request.user.is_superuser:
        return redirect("user_dashboard")

    return render(request, "admin_dashboard/reports2_admin.html", {
        "active_page": "reports",
    })


@login_required(login_url="signin")
def exports(request):
    if not request.user.is_superuser:
        return redirect("user_dashboard")

    _ensure_single_exports_template()

    return render(request, "admin_dashboard/exports_admin.html", {
        "active_page": "exports",
    })


def _csv_safe_value(value):
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def _export_analytics_pdf(period_label, filter_label, sections):
    from xml.sax.saxutils import escape

    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buffer = io.BytesIO()
    page_size = landscape(letter)
    document = SimpleDocTemplate(
        buffer,
        pagesize=page_size,
        leftMargin=0.35 * inch,
        rightMargin=0.35 * inch,
        topMargin=0.45 * inch,
        bottomMargin=0.45 * inch,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("AnalyticsTitle", parent=styles["Heading1"], fontSize=17, textColor=colors.HexColor("#14352d"), alignment=TA_CENTER, spaceAfter=5)
    metadata_style = ParagraphStyle("AnalyticsMetadata", parent=styles["BodyText"], fontSize=9, leading=12, textColor=colors.HexColor("#4b635a"))
    section_style = ParagraphStyle("AnalyticsSection", parent=styles["Heading2"], fontSize=11, leading=14, textColor=colors.HexColor("#14352d"), spaceBefore=8, spaceAfter=3)
    body_style = ParagraphStyle("AnalyticsBody", parent=styles["BodyText"], fontSize=8, leading=10)
    header_style = ParagraphStyle("AnalyticsHeader", parent=body_style, fontName="Helvetica-Bold", textColor=colors.HexColor("#14352d"))

    def pdf_text(value):
        return escape(str(value if value is not None else "").replace("₱", "PHP "))

    elements = [
        Paragraph("Analytics report", title_style),
        Paragraph(f"<b>Period:</b> {pdf_text(period_label)}", metadata_style),
        Paragraph(f"<b>Filters:</b> {pdf_text(filter_label)}", metadata_style),
        Spacer(1, 0.08 * inch),
    ]
    usable_width = page_size[0] - 0.7 * inch
    for section_title, headers, rows in sections:
        elements.append(Paragraph(escape(section_title), section_style))
        if not rows:
            elements.append(Paragraph("No records for this section.", body_style))
            continue

        table_data = [[Paragraph(pdf_text(value), header_style) for value in headers]]
        table_data.extend([
            [Paragraph(pdf_text(value), body_style) for value in row]
            for row in rows
        ])
        if section_title == "Summary":
            ratios = [0.34, 0.22, 0.44]
        elif section_title == "Trend":
            ratios = [0.34, 0.30, 0.36]
        elif section_title == "Filtered records":
            ratios = [0.12, 0.16, 0.20, 0.36, 0.16]
        else:
            ratios = [1 / len(headers)] * len(headers)
        table = Table(table_data, colWidths=[usable_width * ratio for ratio in ratios], repeatRows=1, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#edf8f3")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d7e7e0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fbf9")]),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(table)
    document.build(elements)
    return buffer.getvalue()


@login_required(login_url="signin")
def settings(request):
    if not request.user.is_superuser:
        return redirect("user_dashboard")

    settings_record = AdminSystemSettings.objects.filter(pk="global").first()
    saved_settings = settings_record.settings if settings_record and isinstance(settings_record.settings, dict) else {}
    admin_system_settings = dict(ADMIN_SYSTEM_SETTINGS_DEFAULTS)
    admin_system_settings.update({key: value for key, value in saved_settings.items() if key in ADMIN_SYSTEM_SETTINGS_DEFAULTS})
    preferences_record = AdminUserPreferences.objects.filter(user=request.user).first()
    saved_preferences = preferences_record.preferences if preferences_record and isinstance(preferences_record.preferences, dict) else {}
    admin_user_preferences = dict(ADMIN_USER_PREFERENCE_DEFAULTS)
    admin_user_preferences.update({key: value for key, value in saved_preferences.items() if key in ADMIN_USER_PREFERENCE_DEFAULTS})

    return render(request, "admin_dashboard/settings_saas_admin.html", {
        "active_page": "settings",
        "dashboard_scope": "admin",
        "admin_system_settings": admin_system_settings,
        "admin_user_preferences": admin_user_preferences,
    })


@login_required(login_url="signin")
@require_POST
def admin_system_settings_update(request):
    if not request.user.is_superuser:
        return JsonResponse({"error": "Only administrators can update system settings."}, status=403)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid settings payload."}, status=400)

    proposed_settings = payload.get("settings") if isinstance(payload, dict) else None
    if not isinstance(proposed_settings, dict):
        return JsonResponse({"error": "Settings must be an object."}, status=400)
    if set(proposed_settings) - set(ADMIN_SYSTEM_SETTINGS_DEFAULTS):
        return JsonResponse({"error": "Unsupported settings were included."}, status=400)

    cleaned_settings = {}
    for key, value in proposed_settings.items():
        if key in ADMIN_SYSTEM_SETTINGS_BOOLEAN_KEYS:
            if not isinstance(value, bool):
                return JsonResponse({"error": f"{key} must be true or false."}, status=400)
            cleaned_settings[key] = value
            continue
        if key in ADMIN_SYSTEM_SETTINGS_INTEGER_LIMITS:
            if type(value) is not int:
                return JsonResponse({"error": f"{key} must be a whole number."}, status=400)
            minimum, maximum = ADMIN_SYSTEM_SETTINGS_INTEGER_LIMITS[key]
            if not minimum <= value <= maximum:
                return JsonResponse({"error": f"{key} is outside the supported range."}, status=400)
            cleaned_settings[key] = value
            continue
        if not isinstance(value, str):
            return JsonResponse({"error": f"{key} must be text."}, status=400)

        value = value.strip()
        if len(value) > (4096 if key == "ip_allowlist" else 255):
            return JsonResponse({"error": f"{key} is too long."}, status=400)
        if key == "system_name" and not value:
            return JsonResponse({"error": "System name cannot be blank."}, status=400)
        if key in ADMIN_SYSTEM_SETTINGS_CHOICES and value not in ADMIN_SYSTEM_SETTINGS_CHOICES[key]:
            return JsonResponse({"error": f"{key} has an unsupported value."}, status=400)
        if key == "support_email" and value:
            try:
                validate_email(value)
            except ValidationError:
                return JsonResponse({"error": "Enter a valid support email address."}, status=400)
        if key in {"quiet_hours_start", "quiet_hours_end"}:
            try:
                datetime.strptime(value, "%H:%M")
            except ValueError:
                return JsonResponse({"error": f"{key} must be a valid 24-hour time."}, status=400)
        cleaned_settings[key] = value

    AdminSystemSettings.objects.get_or_create(key="global")
    with transaction.atomic():
        record = AdminSystemSettings.objects.select_for_update().get(pk="global")
        current_settings = record.settings if isinstance(record.settings, dict) else {}
        next_settings = dict(current_settings)
        next_settings.update(cleaned_settings)
        record.settings = next_settings
        record.save(update_fields=["settings", "updated_at"])

    return JsonResponse({"message": "System settings saved.", "settings": next_settings})


@login_required(login_url="signin")
@require_POST
def admin_user_preferences_update(request):
    if not request.user.is_superuser:
        return JsonResponse({"error": "Only administrators can update interface preferences."}, status=403)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid preferences payload."}, status=400)

    proposed_preferences = payload.get("preferences") if isinstance(payload, dict) else None
    if not isinstance(proposed_preferences, dict):
        return JsonResponse({"error": "Preferences must be an object."}, status=400)
    if set(proposed_preferences) != set(ADMIN_USER_PREFERENCE_DEFAULTS):
        return JsonResponse({"error": "All supported interface preferences are required."}, status=400)

    cleaned_preferences = {}
    for key, value in proposed_preferences.items():
        if key in ADMIN_USER_PREFERENCE_BOOLEAN_KEYS:
            if not isinstance(value, bool):
                return JsonResponse({"error": f"{key} must be true or false."}, status=400)
        elif not isinstance(value, str) or value not in ADMIN_USER_PREFERENCE_CHOICES[key]:
            return JsonResponse({"error": f"{key} has an unsupported value."}, status=400)
        cleaned_preferences[key] = value

    preference_record, _ = AdminUserPreferences.objects.get_or_create(user=request.user)
    preference_record.preferences = cleaned_preferences
    preference_record.save(update_fields=["preferences", "updated_at"])
    return JsonResponse({"message": "Interface preferences saved.", "preferences": cleaned_preferences})


@login_required(login_url="signin")
def audit_logs(request):
    if not request.user.is_superuser:
        return redirect("user_dashboard")

    _ensure_single_audit_logs_template()

    return render(request, "admin_dashboard/audit_logs_admin.html", {
        "active_page": "audit_logs",
    })


def logout_view(request):
    clear_two_factor_state(request)
    logout(request)
    return redirect("signin")
