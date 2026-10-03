from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from webapp.models import (
    Activity,
    CommunityNotification,
    VolunteerAttendanceRecord,
    VolunteerActivityAssignment,
)

User = get_user_model()


class Command(BaseCommand):
    help = "Send in-app reminders to volunteers 30 minutes before activities end."

    def handle(self, *args, **options):
        now = timezone.localtime()
        current_timezone = timezone.get_current_timezone()
        sent_count = 0
        completed_count = 0
        timed_out_count = 0

        activities = Activity.objects.filter(
            end_time__isnull=False,
            status=Activity.STATUS_ACTIVE,
        ).prefetch_related("volunteer_assignments__volunteer")

        for activity in activities:
            end_at = timezone.make_aware(
                datetime.combine(activity.date, activity.end_time),
                current_timezone,
            )

            if end_at <= now:
                active_assignments = activity.volunteer_assignments.filter(
                    status__in=[
                        VolunteerActivityAssignment.STATUS_TIME_IN,
                        VolunteerActivityAssignment.STATUS_IN_PROGRESS,
                    ],
                )
                for assignment in active_assignments:
                    time_in = assignment.attendance_started_at or end_at
                    duration_minutes = int(max(1, (end_at - time_in).total_seconds() // 60))
                    assignment.attendance_ended_at = end_at
                    assignment.status = VolunteerActivityAssignment.STATUS_AWAITING_CONFIRMATION
                    assignment.save(update_fields=["status", "attendance_ended_at", "updated_at"])
                    VolunteerAttendanceRecord.objects.create(
                        assignment=assignment,
                        volunteer=assignment.volunteer,
                        time_in=time_in,
                        time_out=end_at,
                        duration_minutes=duration_minutes,
                    )
                    timed_out_count += 1

                activity.status = Activity.STATUS_COMPLETED
                activity.save(update_fields=["status", "updated_at"])
                completed_count += 1
                continue

            if not end_at - timedelta(minutes=30) <= now < end_at:
                continue

            time_label = end_at.strftime("%I:%M %p").lstrip("0")
            message = (
                f"Reminder: {activity.title} ends at {time_label} on "
                f"{activity.date.strftime('%b %d, %Y')}. Please remember to time out."
            )
            assignments = activity.volunteer_assignments.exclude(
                status__in=[
                    VolunteerActivityAssignment.STATUS_COMPLETED,
                    VolunteerActivityAssignment.STATUS_CANCELLED,
                    VolunteerActivityAssignment.STATUS_MISSED,
                ],
            )

            for assignment in assignments:
                volunteer = assignment.volunteer
                actor = assignment.assigned_by or User.objects.filter(is_superuser=True).first()
                if not actor or not volunteer or volunteer.id == actor.id:
                    continue

                already_sent = CommunityNotification.objects.filter(
                    recipient=volunteer,
                    notification_type=CommunityNotification.TYPE_ACTIVITY_END_REMINDER,
                    message=message,
                ).exists()
                if already_sent:
                    continue

                CommunityNotification.objects.create(
                    recipient=volunteer,
                    actor=actor,
                    notification_type=CommunityNotification.TYPE_ACTIVITY_END_REMINDER,
                    message=message,
                    target_url=reverse("volunteer_dashboard_tasks_ojt"),
                )
                sent_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Completed {completed_count} activity(ies); timed out {timed_out_count} volunteer session(s); "
            f"sent {sent_count} activity end reminder(s)."
        ))
