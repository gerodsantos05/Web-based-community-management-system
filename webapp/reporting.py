from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q, Sum
from django.utils import timezone

from .models import (
    Activity,
    BeneficiaryAssistanceRecord,
    Donation,
    ItemPledge,
    ProductInquiry,
    UserProfile,
    VolunteerAttendanceRecord,
)


REPORTS = {
    "donations": ("Donations", "Finalized cash donations and received in-kind gifts."),
    "volunteer-hours": ("Volunteer hours", "Confirmed volunteer attendance with recorded check-outs."),
    "activities": ("Completed activities", "Activities marked completed in the selected period."),
    "assistance": ("Assistance records", "Recorded beneficiary assistance in the selected period."),
    "product-sales": ("Product sales", "Completed product orders ranked by quantity sold."),
    "accounts": ("Active accounts", "Current active member accounts and profile breakdown."),
    "all-records": ("All records", "A date-ordered list of finalized and managed records."),
}

REPORT_TYPES = {
    "donation": "Donations",
    "volunteer": "Volunteer attendance",
    "activity": "Activities",
    "assistance": "Assistance",
    "product_sale": "Product sales",
}

PAGE_SIZE = 25
ACCOUNT_PAGE_SIZE = 10
GENDER_FILTERS = {"all", "male", "female", "other", "prefer_not", "unknown"}
ROLE_FILTERS = {"all", "regular", "beneficiary", "volunteer"}
AGE_GROUP_FILTERS = {"all", "under_18", "18_24", "25_39", "40_59", "60_plus"}
DONATION_TYPES = {"all", "cash", "gcash", "bank", "in_kind"}
VOLUNTEER_TYPES = {"all", UserProfile.VOLUNTEER_TYPE_OJT, UserProfile.VOLUNTEER_TYPE_COMMUNITY}
RECORD_TYPES = {"all", *REPORT_TYPES}


def _date_range(filters):
    today = timezone.localdate()
    range_key = filters.get("range", "30d")
    if range_key == "all":
        first_dates = [
            Donation.objects.filter(status=Donation.STATUS_COMPLETED).dates("created_at", "day").first(),
            ItemPledge.objects.filter(status=ItemPledge.STATUS_RECEIVED).dates("updated_at", "day").first(),
            VolunteerAttendanceRecord.objects.filter(
                status=VolunteerAttendanceRecord.STATUS_CONFIRMED,
                time_out__isnull=False,
            ).dates("time_out", "day").first(),
            Activity.objects.filter(status=Activity.STATUS_COMPLETED).dates("date", "day").first(),
            BeneficiaryAssistanceRecord.objects.dates("assistance_date", "day").first(),
            ProductInquiry.objects.filter(
                payment_status=ProductInquiry.PAYMENT_STATUS_PAID,
            ).dates("created_at", "day").first(),
        ]
        return min((first for first in first_dates if first), default=today), today, "All time"
    if range_key == "7d":
        return today - timedelta(days=6), today, "Last 7 days"
    if range_key == "30d":
        return today - timedelta(days=29), today, "Last 30 days"
    if range_key == "90d":
        return today - timedelta(days=89), today, "Last 90 days"
    if range_key != "custom":
        raise ValueError("Choose a valid reporting period.")
    try:
        start = date.fromisoformat(filters.get("start", ""))
        end = date.fromisoformat(filters.get("end", ""))
    except (TypeError, ValueError):
        raise ValueError("Choose both dates for the custom reporting period.")
    if start > end:
        raise ValueError("The start date must be on or before the end date.")
    return start, end, f"{start.isoformat()} to {end.isoformat()}"


def _buckets(start, end):
    days = (end - start).days + 1
    size = 1 if days <= 7 else 7 if days <= 31 else 30
    buckets = []
    bucket_start = start
    while bucket_start <= end:
        bucket_end = min(bucket_start + timedelta(days=size - 1), end)
        if size == 1:
            label = bucket_start.strftime("%b %d")
        else:
            label = f"{bucket_start:%b %d}–{bucket_end:%b %d}"
        buckets.append((label, bucket_start, bucket_end))
        bucket_start = bucket_end + timedelta(days=1)
    return buckets


def _bucket_index(day, buckets):
    for index, (_label, start, end) in enumerate(buckets):
        if start <= day <= end:
            return index
    return None


def _age(birthdate, today):
    if not birthdate:
        return None
    return today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))


def _age_group(age):
    if age is None:
        return "unknown"
    if age < 18:
        return "under_18"
    if age <= 24:
        return "18_24"
    if age <= 39:
        return "25_39"
    if age <= 59:
        return "40_59"
    return "60_plus"


def _profile_for(user):
    try:
        return user.userprofile
    except ObjectDoesNotExist:
        return None


def _member_role(profile):
    if profile and profile.account_role in ROLE_FILTERS - {"all"}:
        return profile.account_role
    return UserProfile.ROLE_REGULAR


def _role_label(role):
    return {
        UserProfile.ROLE_REGULAR: "Regular user",
        UserProfile.ROLE_BENEFICIARY: "Beneficiary",
        UserProfile.ROLE_VOLUNTEER: "Volunteer",
    }.get(role, "Regular user")


def _age_group_label(key):
    return {
        "under_18": "Under 18",
        "18_24": "18–24",
        "25_39": "25–39",
        "40_59": "40–59",
        "60_plus": "60+",
        "unknown": "Not provided",
    }.get(key, key)


def _format_date(value):
    return value.isoformat() if value else ""


def _format_hours(minutes):
    return f"{(minutes or 0) / 60:.1f} hours"


def _record_rows(rows, page, page_size, export_all):
    count = len(rows)
    if export_all:
        selected = rows
        page = 1
    else:
        page = min(max(page, 1), max((count + page_size - 1) // page_size, 1))
        selected = rows[(page - 1) * page_size:page * page_size]
    return {
        "rows": selected,
        "count": count,
        "page": page,
        "page_size": page_size,
        "pages": max((count + page_size - 1) // page_size, 1),
    }


def _base_payload(report, start, end, period_label, filters, columns, rows, stats, trend_title,
                  trend_label, trend_values, buckets, distribution_title, distribution_labels,
                  distribution_values, empty_message, page, page_size, export_all=False,
                  totals=None, options=None, distribution_type="doughnut"):
    selected = _record_rows(rows, page, page_size, export_all)
    return {
        "report": report,
        "title": REPORTS[report][0],
        "subtitle": REPORTS[report][1],
        "period": period_label,
        "filters": filters,
        "stats": stats,
        "totals": totals or {},
        "trend": {
            "title": trend_title,
            "note": {
                "donations": "Items received by day" if trend_label == "Items received" else "Finalized cash donation value",
                "volunteer-hours": "Hours per day",
                "activities": "Completed per day",
                "assistance": "Records per day",
                "product-sales": "Quantity sold per week",
                "accounts": "Not affected by the period filter",
                "all-records": "Records per day",
            }[report],
            "labels": [bucket[0] for bucket in buckets],
            "values": trend_values,
            "series_label": trend_label,
        },
        "distribution": {
            "title": distribution_title,
            "note": {
                "donations": "Received items by name" if trend_label == "Items received" else "GCash and Bank Transfer",
                "volunteer-hours": "Confirmed attendance hours by volunteer",
                "activities": "Completed in period",
                "assistance": "Quantity or amount given",
                "product-sales": "Share of quantity sold",
                "accounts": "Follows the selected filters",
                "all-records": "Share of records by type",
            }[report],
            "labels": distribution_labels,
            "values": distribution_values,
            "type": distribution_type,
        },
        "columns": columns,
        "rows": selected["rows"],
        "row_count": selected["count"],
        "page": selected["page"],
        "page_size": selected["page_size"],
        "pages": selected["pages"],
        "empty_message": empty_message,
        "options": options or {},
    }


def _build_donations(filters, start, end, period_label, page, export_all):
    donation_type = filters.get("donation_type", "all")
    campaign = filters.get("campaign", "")
    if donation_type not in DONATION_TYPES:
        raise ValueError("Choose a valid donation type.")

    financial_donations = Donation.objects.filter(
        status=Donation.STATUS_COMPLETED,
        created_at__date__range=(start, end),
    )
    cash = financial_donations
    payment_method_filter = {
        "cash": Donation.PAYMENT_CASH,
        "gcash": Donation.PAYMENT_GCASH,
        "bank": Donation.PAYMENT_BANK_TRANSFER,
    }.get(donation_type)
    if payment_method_filter:
        cash = cash.filter(payment_method=payment_method_filter)
    elif donation_type == "in_kind":
        cash = cash.none()
    if campaign == "__none__":
        cash = cash.filter(campaign="")
    elif campaign:
        cash = cash.filter(campaign=campaign)

    pledges = ItemPledge.objects.filter(
        status=ItemPledge.STATUS_RECEIVED,
        updated_at__date__range=(start, end),
    ).select_related("user")
    if donation_type not in {"all", "in_kind"} or campaign:
        pledges = []

    rows = []
    received_by_type = {}
    received_items = 0
    for donation in cash.order_by("-created_at", "-id"):
        method = donation.get_payment_method_display()
        donation_label = {
            Donation.PAYMENT_CASH: "Cash",
            Donation.PAYMENT_GCASH: "GCash",
            Donation.PAYMENT_BANK_TRANSFER: "Bank",
        }.get(donation.payment_method, method)
        rows.append([
            _format_date(timezone.localtime(donation.created_at).date()),
            donation_label,
            donation.campaign.strip() or "No campaign recorded",
            f"{donation.donor_name or 'Anonymous donor'} · {method}",
            f"₱{donation.amount:,.0f}",
        ])
    for pledge in pledges:
        pledge_date = timezone.localtime(pledge.updated_at).date()
        received_items += pledge.quantity
        received_by_type[pledge.item_name] = received_by_type.get(pledge.item_name, 0) + pledge.quantity
        donor = "Anonymous donor" if pledge.is_anonymous else (pledge.donor_name or "Donor not named")
        rows.append([
            _format_date(pledge_date),
            "In-kind",
            "—",
            f"{pledge.item_name} · {donor}",
            f"{pledge.quantity} items",
        ])
    rows.sort(key=lambda row: row[0], reverse=True)

    cash_total = cash.aggregate(total=Sum("amount"))["total"] or 0
    cash_count = cash.count()
    in_kind_count = len(pledges)
    largest = cash.values("donor_name", "user__username").annotate(
        total=Sum("amount")
    ).order_by("-total").first()
    largest_donor = "No completed donations"
    largest_total = 0
    if largest:
        largest_donor = largest["donor_name"] or largest["user__username"] or "Anonymous donor"
        largest_total = largest["total"] or 0

    if donation_type == "in_kind":
        stats = [
            {"label": "In-kind donations", "value": in_kind_count, "note": "Received pledges"},
            {"label": "Items received", "value": received_items, "note": "Across matching pledges"},
        ]
    elif donation_type in {"cash", "gcash", "bank"}:
        payment_label = {
            "cash": "Cash",
            "gcash": "GCash",
            "bank": "Bank",
        }[donation_type]
        stats = [
            {"label": f"Total {payment_label} amount", "value": f"₱{cash_total:,.0f}", "note": period_label},
            {"label": f"{payment_label} donations", "value": cash_count, "note": "Finalized donations"},
        ]
    else:
        stats = [
            {"label": "Total donation amount", "value": f"₱{cash_total:,.0f}", "note": period_label},
            {"label": "Financial donations", "value": cash_count, "note": "Finalized donations"},
            {"label": "In-kind donations", "value": in_kind_count, "note": "Received pledges"},
            {"label": "Items received", "value": received_items, "note": "Across matching pledges"},
        ]

    buckets = _buckets(start, end)
    trend_values = [0] * len(buckets)
    for donation in cash:
        index = _bucket_index(timezone.localtime(donation.created_at).date(), buckets)
        if index is not None:
            trend_values[index] += donation.amount
    in_kind_trend = [0] * len(buckets)
    for pledge in pledges:
        index = _bucket_index(timezone.localtime(pledge.updated_at).date(), buckets)
        if index is not None:
            in_kind_trend[index] += pledge.quantity

    if donation_type == "in_kind":
        trend_values = in_kind_trend
        trend_label = "Items received"
        distribution_title = "Received items by name"
        distribution_labels = sorted(received_by_type)
        distribution_values = [received_by_type[label] for label in distribution_labels]
    else:
        trend_label = "Financial donation amount (₱)"
        distribution_title = "Donations by type" if donation_type == "all" else "Donations by payment method"
        distribution_labels = ["Cash", "GCash", "Bank", "Other methods"]
        distribution_values = [
            cash.filter(payment_method=Donation.PAYMENT_CASH).count(),
            cash.filter(payment_method=Donation.PAYMENT_GCASH).count(),
            cash.filter(payment_method=Donation.PAYMENT_BANK_TRANSFER).count(),
            cash.exclude(payment_method__in=[
                Donation.PAYMENT_CASH,
                Donation.PAYMENT_GCASH,
                Donation.PAYMENT_BANK_TRANSFER,
            ]).count(),
        ]
        if donation_type == "all":
            distribution_labels.append("In-kind")
            distribution_values.append(in_kind_count)

    campaigns = [
        {
            "value": value if value else "__none__",
            "label": value.strip() or "No campaign recorded",
        }
        for value in Donation.objects.filter(
            status=Donation.STATUS_COMPLETED,
            created_at__date__range=(start, end),
        ).values_list("campaign", flat=True).distinct().order_by("campaign")
    ]
    donation_type_options = [
        {"value": value, "label": label}
        for value, label in (
            ("all", "All"),
            ("cash", "Cash"),
            ("gcash", "GCash"),
            ("bank", "Bank"),
            ("in_kind", "In-kind"),
        )
    ]
    return _base_payload(
        "donations", start, end, period_label, filters,
        ["Date", "Type", "Campaign", "Details", "Value"], rows, stats,
        "Donations over time", trend_label, trend_values, buckets,
        distribution_title, distribution_labels, distribution_values,
        "No donations in this period.", page, PAGE_SIZE, export_all,
        totals={
            "cash_amount": cash_total,
            "cash_count": cash_count,
            "in_kind_count": in_kind_count,
            "items_received": received_items,
            "largest_donor": largest_donor,
            "largest_total": largest_total,
        },
        options={"donation_types": donation_type_options, "campaigns": campaigns},
    )


def _build_volunteer_hours(filters, start, end, period_label, page, export_all):
    volunteer_type = filters.get("volunteer_type", "all")
    if volunteer_type not in VOLUNTEER_TYPES:
        raise ValueError("Choose a valid volunteer type.")
    attendance = VolunteerAttendanceRecord.objects.filter(
        status=VolunteerAttendanceRecord.STATUS_CONFIRMED,
        time_out__isnull=False,
        time_out__date__range=(start, end),
    ).select_related("volunteer", "assignment").order_by("-time_out", "-id")
    volunteer_types = dict(UserProfile.objects.filter(
        account_role=UserProfile.ROLE_VOLUNTEER,
    ).values_list("user_id", "volunteer_type"))
    if volunteer_type != "all":
        attendance = [
            record for record in attendance
            if volunteer_types.get(record.volunteer_id, UserProfile.VOLUNTEER_TYPE_OJT) == volunteer_type
        ]
    rows = []
    minutes_per_bucket = [0] * len(_buckets(start, end))
    buckets = _buckets(start, end)
    volunteer_ids = set()
    total_minutes = 0
    volunteer_minutes = {}
    volunteer_names = {}
    for record in attendance:
        day = timezone.localtime(record.time_out).date()
        volunteer_ids.add(record.volunteer_id)
        minutes = record.duration_minutes or 0
        total_minutes += minutes
        volunteer_minutes[record.volunteer_id] = volunteer_minutes.get(record.volunteer_id, 0) + minutes
        name = f"{record.volunteer.first_name} {record.volunteer.last_name}".strip() or record.volunteer.username
        volunteer_names[record.volunteer_id] = name
        index = _bucket_index(day, buckets)
        if index is not None:
            minutes_per_bucket[index] += minutes
        rows.append([
            _format_date(day),
            name,
            record.assignment.activity_name or "Volunteer assignment",
            f"{minutes / 60:.1f}",
        ])

    active_profiles = UserProfile.objects.filter(
        account_role=UserProfile.ROLE_VOLUNTEER,
        user__is_active=True,
        user__is_staff=False,
        user__is_superuser=False,
    ).select_related("user")
    ojt_volunteer_count = 0
    ojt_total = 0.0
    required_total = 0.0
    for profile in active_profiles:
        if profile.volunteer_type == UserProfile.VOLUNTEER_TYPE_COMMUNITY:
            continue
        hours = float(profile.ojt_hours or 0)
        required = float(profile.required_ojt_hours or 80)
        if required <= 0:
            continue
        ojt_volunteer_count += 1
        ojt_total += min(hours, required)
        required_total += required

    total_hours = total_minutes / 60
    volunteer_summaries = sorted(
        volunteer_minutes,
        key=lambda volunteer_id: (-volunteer_minutes[volunteer_id], volunteer_names[volunteer_id].lower()),
    )
    volunteer_labels = [
        f"{volunteer_names[volunteer_id]} ({'Community' if volunteer_types.get(volunteer_id) == UserProfile.VOLUNTEER_TYPE_COMMUNITY else 'OJT'})"
        for volunteer_id in volunteer_summaries
    ]
    volunteer_hour_values = [round(volunteer_minutes[volunteer_id] / 60, 1) for volunteer_id in volunteer_summaries]
    stats = [
        {"label": "Total hours", "value": f"{total_hours:.1f}h", "note": period_label},
        {"label": "Volunteers", "value": len(volunteer_ids), "note": "With confirmed attendance"},
    ]
    if volunteer_type != UserProfile.VOLUNTEER_TYPE_COMMUNITY:
        stats.append({
            "label": "OJT progress",
            "value": f"{ojt_total:.1f}h",
            "note": f"of {required_total:.1f}h across {ojt_volunteer_count} active OJT volunteers",
        })
    return _base_payload(
        "volunteer-hours", start, end, period_label, filters,
        ["Date", "Volunteer", "Assignment", "Hours"], rows, stats,
        "Volunteer hours over time", "Hours", [round(value / 60, 1) for value in minutes_per_bucket],
        buckets, "Volunteer hours by volunteer", volunteer_labels, volunteer_hour_values,
        "No confirmed volunteer attendance in this period.", page, PAGE_SIZE, export_all,
        totals={
            "hours": round(total_hours, 1),
            "volunteers": len(volunteer_ids),
            "ojt_completed_hours": round(ojt_total, 1),
            "ojt_required_hours": round(required_total, 1),
            "ojt_volunteers": ojt_volunteer_count,
        },
        options={"volunteer_types": [
            {"value": "all", "label": "All"},
            {"value": UserProfile.VOLUNTEER_TYPE_OJT, "label": "OJT Volunteer"},
            {"value": UserProfile.VOLUNTEER_TYPE_COMMUNITY, "label": "Community Volunteer"},
        ]},
        distribution_type="bar",
    )


def _build_activities(filters, start, end, period_label, page, export_all):
    activities = Activity.objects.filter(
        status=Activity.STATUS_COMPLETED,
        date__range=(start, end),
    ).order_by("-date", "title")
    category_labels = dict(Activity.CATEGORY_CHOICES)
    rows = []
    buckets = _buckets(start, end)
    trend_values = [0] * len(buckets)
    categories = {}
    for activity in activities:
        index = _bucket_index(activity.date, buckets)
        if index is not None:
            trend_values[index] += 1
        category = category_labels.get(activity.category, activity.category or "Uncategorized")
        categories[category] = categories.get(category, 0) + 1
        rows.append([
            _format_date(activity.date),
            activity.title,
            category,
            str(activity.volunteer_count),
        ])
    count = len(rows)
    stats = [
        {"label": "Completed activities", "value": count, "note": period_label},
        {"label": "Categories", "value": len(categories), "note": "Represented in this period"},
    ]
    labels = sorted(categories)
    return _base_payload(
        "activities", start, end, period_label, filters,
        ["Date", "Activity", "Category", "Volunteers"], rows, stats,
        "Completed activities over time", "Activities", trend_values, buckets,
        "Activities by category", labels, [categories[label] for label in labels],
        "No completed activities in this period.", page, PAGE_SIZE, export_all,
        totals={"completed": count, "categories": len(categories)},
    )


def _build_assistance(filters, start, end, period_label, page, export_all):
    records = BeneficiaryAssistanceRecord.objects.filter(
        assistance_date__range=(start, end),
    ).select_related("beneficiary").order_by("-assistance_date", "-created_at", "-id")
    rows = []
    buckets = _buckets(start, end)
    trend_values = [0] * len(buckets)
    aid_types = {}
    for record in records:
        index = _bucket_index(record.assistance_date, buckets)
        if index is not None:
            trend_values[index] += 1
        aid_types[record.aid_type] = aid_types.get(record.aid_type, 0) + 1
        rows.append([
            _format_date(record.assistance_date),
            record.aid_type,
            record.beneficiary.full_name or "Beneficiary",
            record.quantity_or_amount,
        ])
    count = len(rows)
    labels = sorted(aid_types)
    stats = [{"label": "Record count", "value": count, "note": period_label}]
    return _base_payload(
        "assistance", start, end, period_label, filters,
        ["Date", "Aid type", "Beneficiary", "Quantity/amount"], rows, stats,
        "Assistance records over time", "Records", trend_values, buckets,
        "Records by aid type", labels, [aid_types[label] for label in labels],
        "No assistance records in this period.", page, PAGE_SIZE, export_all,
        totals={"count": count},
    )


def _paid_product_orders(start=None, end=None):
    orders = ProductInquiry.objects.filter(payment_status=ProductInquiry.PAYMENT_STATUS_PAID)
    if start and end:
        orders = orders.filter(created_at__date__range=(start, end))
    return orders.order_by("-created_at", "-id")


def _product_lines(orders):
    for order in orders:
        if not isinstance(order.order_items, list):
            continue
        for item in order.order_items:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            category = str(item.get("category", "")).strip()
            try:
                quantity = int(item.get("quantity", 0))
                price = float(item.get("unit_price", 0) or 0)
            except (TypeError, ValueError):
                continue
            if not name or quantity <= 0:
                continue
            yield order, item, name, category or "Uncategorized", quantity, price


def _build_product_sales(filters, start, end, period_label, page, export_all):
    selected_category = filters.get("category", "all")
    all_categories = sorted({
        category
        for _order, _item, _name, category, _quantity, _price in _product_lines(_paid_product_orders())
    })
    if selected_category != "all" and selected_category not in all_categories:
        raise ValueError("Choose a valid product category.")
    orders = _paid_product_orders(start, end)
    product_totals = {}
    category_totals = {}
    trend_values = [0] * len(_buckets(start, end))
    buckets = _buckets(start, end)
    rows_by_product = {}
    total_revenue = Decimal("0.00")
    for order, _item, name, category, quantity, price in _product_lines(orders):
        if selected_category != "all" and category != selected_category:
            continue
        total_revenue += Decimal(str(price)) * quantity
        key = (name, category)
        product = product_totals.setdefault(key, {"quantity": 0, "price": price})
        product["quantity"] += quantity
        if "latest" not in product or order.created_at > product["latest"]:
            product["price"] = price
            product["latest"] = order.created_at
        category_totals[category] = category_totals.get(category, 0) + quantity
        index = _bucket_index(timezone.localtime(order.created_at).date(), buckets)
        if index is not None:
            trend_values[index] += quantity

    ranked = sorted(product_totals.items(), key=lambda entry: (-entry[1]["quantity"], entry[0][0].lower()))
    for rank, ((name, category), info) in enumerate(ranked, start=1):
        rows_by_product[(name, category)] = rank
    rows = [
        [
            str(rows_by_product[(name, category)]),
            name,
            category,
            f"₱{info['price']:,.2f}",
            str(info["quantity"]),
        ]
        for (name, category), info in ranked
    ]
    product_count = len(product_totals)
    total_quantity = sum(item["quantity"] for item in product_totals.values())
    top_name = ranked[0][0][0] if ranked else "No completed sales"
    stats = [
        {"label": "Top product", "value": top_name, "note": f"{ranked[0][1]['quantity']} sold" if ranked else "No completed sales in this period"},
        {"label": "Quantity sold", "value": total_quantity, "note": period_label},
        {"label": "Products sold", "value": product_count, "note": "Distinct product/category pairs"},
    ]
    distribution_labels = sorted(category_totals)
    return _base_payload(
        "product-sales", start, end, period_label, filters,
        ["Rank", "Product", "Category", "Price", "Quantity sold"], rows, stats,
        "Product sales over time", "Items sold", trend_values, buckets,
        "Sales by category", distribution_labels,
        [category_totals[label] for label in distribution_labels],
        "No product sales in this period.", page, PAGE_SIZE, export_all,
        totals={
            "top_product": top_name,
            "quantity_sold": total_quantity,
            "products_sold": product_count,
            "revenue": f"₱{total_revenue:,.2f}",
        },
        options={"categories": [{"value": "all", "label": "All categories"}] + [
            {"value": value, "label": value} for value in all_categories
        ]},
    )


def _build_accounts(filters, page, export_all):
    role = filters.get("role", "all")
    gender = filters.get("gender", "all")
    age_group = filters.get("age_group", "all")
    if role not in ROLE_FILTERS:
        raise ValueError("Choose a valid account role.")
    if gender not in GENDER_FILTERS:
        raise ValueError("Choose a valid gender.")
    if age_group not in AGE_GROUP_FILTERS:
        raise ValueError("Choose a valid age group.")

    users = User.objects.filter(
        is_active=True,
        is_staff=False,
        is_superuser=False,
    ).select_related("userprofile").order_by("username", "id")
    today = timezone.localdate()
    filtered = []
    role_counts = {key: 0 for key in ("regular", "beneficiary", "volunteer")}
    chart_age_counts = {key: 0 for key in ("under_18", "18_24", "25_39", "40_59", "60_plus", "unknown")}
    chart_gender_counts = {key: 0 for key in ("male", "female", "other", "prefer_not", "unknown")}
    ages = []
    gender_counts = {"female": 0, "male": 0}
    for user in users:
        profile = _profile_for(user)
        user_role = _member_role(profile)
        user_gender = profile.gender if profile and profile.gender else "unknown"
        user_age = _age(profile.birthdate if profile else None, today)
        user_age_group = _age_group(user_age)
        role_counts[user_role] = role_counts.get(user_role, 0) + 1
        chart_age_counts[user_age_group] += 1
        chart_gender_counts[user_gender if user_gender in chart_gender_counts else "unknown"] += 1

        if role != "all" and user_role != role:
            continue
        if gender != "all" and user_gender != gender:
            continue
        if age_group != "all" and user_age_group != age_group:
            continue
        filtered.append((user, user_role, user_gender, user_age, user_age_group))
        if user_age is not None:
            ages.append(user_age)
        if user_gender in gender_counts:
            gender_counts[user_gender] += 1

    if role != "all" or gender != "all" or age_group != "all":
        selected_age_groups = {}
        selected_genders = {}
        for _user, _role, selected_gender, selected_age, selected_age_group in filtered:
            selected_age_groups[selected_age_group] = selected_age_groups.get(selected_age_group, 0) + 1
            selected_genders[selected_gender] = selected_genders.get(selected_gender, 0) + 1
        chart_age_counts = {key: selected_age_groups.get(key, 0) for key in chart_age_counts}
        chart_gender_counts = {key: selected_genders.get(key, 0) for key in chart_gender_counts}

    labels = {
        "male": "Male",
        "female": "Female",
        "other": "Other",
        "prefer_not": "Prefer not to say",
        "unknown": "Not provided",
    }
    rows = []
    for user, user_role, user_gender, user_age, user_age_group in filtered:
        name = f"{user.first_name} {user.last_name}".strip() or user.username
        rows.append([
            name,
            _role_label(user_role),
            labels.get(user_gender, "Not provided"),
            str(user_age) if user_age is not None else "—",
            _age_group_label(user_age_group),
        ])
    stats = [
        {"label": "Matching accounts", "value": len(filtered), "note": "Active member accounts"},
        {"label": "Female", "value": gender_counts["female"], "note": "Matching filters"},
        {"label": "Male", "value": gender_counts["male"], "note": "Matching filters"},
        {"label": "Average age", "value": f"{sum(ages) / len(ages):.1f}" if ages else "—", "note": "Accounts with birthdates"},
    ]
    age_keys = ("under_18", "18_24", "25_39", "40_59", "60_plus", "unknown")
    gender_keys = ("female", "male", "other", "prefer_not", "unknown")
    start, end = timezone.localdate(), timezone.localdate()
    buckets = [(timezone.localdate().strftime("%b %d"), start, end)]
    return _base_payload(
        "accounts", start, end, "Not affected by the reporting period", filters,
        ["Account", "Role", "Gender", "Age", "Age group"], rows, stats,
        "Accounts by age group", "Accounts", [chart_age_counts[key] for key in age_keys],
        buckets, "Accounts by gender", [labels[key] for key in gender_keys],
        [chart_gender_counts[key] for key in gender_keys],
        "No active accounts match these filters.", page, ACCOUNT_PAGE_SIZE, export_all,
        totals={
            "accounts": len(filtered),
            "female": gender_counts["female"],
            "male": gender_counts["male"],
            "average_age": sum(ages) / len(ages) if ages else None,
            "role_counts": role_counts,
        },
        options={
            "roles": [
                {"value": "all", "label": "All roles"},
                {"value": "regular", "label": "Regular users"},
                {"value": "beneficiary", "label": "Beneficiaries"},
                {"value": "volunteer", "label": "Volunteers"},
            ],
            "genders": [
                {"value": "all", "label": "All genders"},
                {"value": "female", "label": "Female"},
                {"value": "male", "label": "Male"},
                {"value": "other", "label": "Other"},
                {"value": "prefer_not", "label": "Prefer not to say"},
                {"value": "unknown", "label": "Not provided"},
            ],
            "age_groups": [
                {"value": "all", "label": "All age groups"},
                {"value": "under_18", "label": "Under 18"},
                {"value": "18_24", "label": "18–24"},
                {"value": "25_39", "label": "25–39"},
                {"value": "40_59", "label": "40–59"},
                {"value": "60_plus", "label": "60+"},
            ],
            "role_counts": [
                {"label": _role_label(key), "value": value}
                for key, value in role_counts.items()
            ],
        },
    )


def _build_all_records(filters, start, end, period_label, page, export_all):
    record_type = filters.get("record_type", "all")
    if record_type not in RECORD_TYPES:
        raise ValueError("Choose a valid record type.")
    records = []
    subreports = ("donations", "volunteer-hours", "activities", "assistance")
    for subreport in subreports:
        if record_type != "all" and record_type != {
            "donations": "donation",
            "volunteer-hours": "volunteer",
            "activities": "activity",
            "assistance": "assistance",
            "product-sales": "product_sale",
        }[subreport]:
            continue
        payload = _build_report_data(subreport, filters, start, end, period_label, 1, True)
        for row in payload["rows"]:
            if subreport == "donations":
                entry_type = "Donations"
                record = row[3].split(" · ")[0]
                details = f"{row[1]} · {row[2]} · {row[3].split(' · ')[-1]}"
                value = row[4]
            elif subreport == "volunteer-hours":
                entry_type = "Volunteer attendance"
                record = row[1]
                details = row[2]
                value = f"{row[3]} hours"
            elif subreport == "activities":
                entry_type = "Activities"
                record = row[1]
                details = f"{row[2]} · {row[3]} volunteers"
                value = row[3]
            elif subreport == "assistance":
                entry_type = "Assistance"
                record = row[1]
                details = row[2]
                value = row[3]
            records.append([row[0], entry_type, record, details, value])
    if record_type in {"all", "product_sale"}:
        for order, _item, name, category, quantity, price in _product_lines(
            _paid_product_orders(start, end)
        ):
            records.append([
                _format_date(timezone.localtime(order.created_at).date()),
                "Product sales",
                name,
                category,
                f"{quantity} sold · ₱{price * quantity:,.2f}",
            ])
    records.sort(key=lambda row: row[0], reverse=True)
    buckets = _buckets(start, end)
    trend_values = [0] * len(buckets)
    distributions = {label: 0 for label in REPORT_TYPES.values()}
    for row in records:
        try:
            day = date.fromisoformat(row[0])
        except ValueError:
            continue
        index = _bucket_index(day, buckets)
        if index is not None:
            trend_values[index] += 1
        distributions[row[1]] += 1
    labels = list(REPORT_TYPES.values())
    return _base_payload(
        "all-records", start, end, period_label, filters,
        ["Date", "Type", "Record", "Details", "Value"], records,
        [{"label": "Records shown", "value": len(records), "note": period_label}],
        "Records over time", "Records", trend_values, buckets,
        "Records by type", labels, [distributions[label] for label in labels],
        "No records of this type in this period.", page, PAGE_SIZE, export_all,
        totals={"records": len(records)},
        options={"record_types": [
            {"value": "all", "label": "All record types"},
            {"value": "donation", "label": "Donations"},
            {"value": "activity", "label": "Activities"},
            {"value": "volunteer", "label": "Volunteer attendance"},
            {"value": "assistance", "label": "Assistance"},
            {"value": "product_sale", "label": "Product sales"},
        ]},
    )


def _build_report_data(report, filters, start, end, period_label, page, export_all=False):
    if report == "donations":
        return _build_donations(filters, start, end, period_label, page, export_all)
    if report == "volunteer-hours":
        return _build_volunteer_hours(filters, start, end, period_label, page, export_all)
    if report == "activities":
        return _build_activities(filters, start, end, period_label, page, export_all)
    if report == "assistance":
        return _build_assistance(filters, start, end, period_label, page, export_all)
    if report == "product-sales":
        return _build_product_sales(filters, start, end, period_label, page, export_all)
    if report == "accounts":
        return _build_accounts(filters, page, export_all)
    if report == "all-records":
        return _build_all_records(filters, start, end, period_label, page, export_all)
    raise ValueError("Choose a valid report.")


def _overview():
    today = timezone.localdate()
    start = today - timedelta(days=29)
    donation_records = Donation.objects.filter(
        status=Donation.STATUS_COMPLETED,
        created_at__date__range=(start, today),
    )
    cash_amount = donation_records.aggregate(total=Sum("amount"))["total"] or 0
    cash_count = donation_records.count()
    received_pledges = ItemPledge.objects.filter(
        status=ItemPledge.STATUS_RECEIVED,
        updated_at__date__range=(start, today),
    )
    in_kind_count = received_pledges.count()
    attendance = VolunteerAttendanceRecord.objects.filter(
        status=VolunteerAttendanceRecord.STATUS_CONFIRMED,
        time_out__isnull=False,
        time_out__date__range=(start, today),
    )
    volunteer_minutes = attendance.aggregate(total=Sum("duration_minutes"))["total"] or 0
    volunteer_count = attendance.values("volunteer_id").distinct().count()
    completed_activities = Activity.objects.filter(
        status=Activity.STATUS_COMPLETED,
        date__range=(start, today),
    ).count()
    assistance_count = BeneficiaryAssistanceRecord.objects.filter(
        assistance_date__range=(start, today),
    ).count()
    products = {}
    for _order, _item, name, category, quantity, _price in _product_lines(
        _paid_product_orders(start, today)
    ):
        key = (name, category)
        products[key] = products.get(key, 0) + quantity
    top_product = min(products, key=lambda key: (-products[key], key[0].lower()))[0] if products else "No completed sales"
    active_members = User.objects.filter(is_active=True, is_staff=False, is_superuser=False)
    role_counts = {
        "regular": active_members.filter(
            Q(userprofile__account_role=UserProfile.ROLE_REGULAR)
            | Q(userprofile__account_role__isnull=True)
            | Q(userprofile__account_role="")
        ).count(),
        "beneficiary": active_members.filter(userprofile__account_role=UserProfile.ROLE_BENEFICIARY).count(),
        "volunteer": active_members.filter(userprofile__account_role=UserProfile.ROLE_VOLUNTEER).count(),
    }
    account_count = sum(role_counts.values())
    account_breakdown = " · ".join(
        f"{_role_label(role)}: {count}" for role, count in role_counts.items()
    )
    cards = [
        {
            "title": "Finalized donations",
            "value": f"₱{cash_amount:,.0f}",
            "note": f"{cash_count} cash · {in_kind_count} in-kind donations · Last 30 days",
            "action": "View donations →",
            "url": "/reports/donations/",
        },
        {
            "title": "Volunteer hours",
            "value": f"{volunteer_minutes / 60:.1f}h",
            "note": f"{volunteer_count} volunteers · Last 30 days",
            "action": "View volunteers →",
            "url": "/reports/volunteer-hours/",
        },
        {
            "title": "Completed activities",
            "value": completed_activities,
            "note": "Last 30 days",
            "action": "View activities →",
            "url": "/reports/activities/",
        },
        {
            "title": "Assistance records",
            "value": assistance_count,
            "note": "Last 30 days",
            "action": "View assistance →",
            "url": "/reports/assistance/",
        },
        {
            "title": "Product sales",
            "value": top_product,
            "note": f"Top-selling product · Last 30 days",
            "action": "View ranking →",
            "url": "/reports/product-sales/",
        },
        {
            "title": "Active accounts",
            "value": account_count,
            "note": f"Current accounts · {account_breakdown}",
            "action": "View accounts →",
            "url": "/reports/accounts/",
        },
        {
            "title": "All records",
            "note": "Every record type in one list: donations, activities, volunteer hours, assistance and product sales",
            "action": "View all records →",
            "is_all_records": True,
            "url": "/reports/all-records/",
        },
    ]
    return {"cards": cards}


def reports_payload(report, params, export_all=False):
    if report == "overview":
        return _overview()
    filters = {key: params.get(key, "") for key in (
        "range", "start", "end", "donation_type", "volunteer_type", "campaign", "category", "role",
        "gender", "age_group", "record_type",
    )}
    if not filters["range"]:
        filters["range"] = "30d"
    if not filters["donation_type"]:
        filters["donation_type"] = "all"
    if not filters["volunteer_type"]:
        filters["volunteer_type"] = "all"
    if not filters["category"]:
        filters["category"] = "all"
    if not filters["role"]:
        filters["role"] = "all"
    if not filters["gender"]:
        filters["gender"] = "all"
    if not filters["age_group"]:
        filters["age_group"] = "all"
    if not filters["record_type"]:
        filters["record_type"] = "all"
    try:
        page = int(params.get("page", "1"))
    except (TypeError, ValueError):
        raise ValueError("Choose a valid page number.")
    if page < 1:
        raise ValueError("Choose a valid page number.")
    if report == "accounts":
        start, end = timezone.localdate(), timezone.localdate()
        period_label = "Not affected by the reporting period"
    else:
        start, end, period_label = _date_range(filters)
    return _build_report_data(report, filters, start, end, period_label, page, export_all)
