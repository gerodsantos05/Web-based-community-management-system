import os
import uuid

from django import VERSION as DJANGO_VERSION
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models


ALLOWED_UPLOAD_EXTENSIONS = {
	"pdf",
	"doc",
	"docx",
	"xls",
	"xlsx",
	"csv",
	"png",
	"jpg",
	"jpeg",
	"jfif",
	"gif",
	"webp",
	"bmp",
	"svg",
	"heic",
	"heif",
	"mp3",
	"wav",
	"m4a",
	"aac",
	"ogg",
	"mp4",
	"mov",
	"avi",
	"mkv",
	"webm",
}

ALLOWED_UPLOAD_MIME_TYPES = {
	"application/pdf",
	"application/msword",
	"application/vnd.openxmlformats-officedocument.wordprocessingml.document",
	"application/vnd.ms-excel",
	"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
	"text/csv",
	"image/png",
	"image/jpeg",
	"image/jpg",
	"image/pjpeg",
	"image/gif",
	"image/webp",
	"image/bmp",
	"image/svg+xml",
	"image/heic",
	"image/heif",
	"image/heic-sequence",
	"image/heif-sequence",
	"audio/mpeg",
	"audio/wav",
	"audio/x-wav",
	"audio/mp4",
	"audio/aac",
	"audio/ogg",
	"video/mp4",
	"video/quicktime",
	"video/x-msvideo",
	"video/x-matroska",
	"video/webm",
}


def _attendance_target_constraint():
	condition = models.Q(assignment__isnull=False) | models.Q(duty_date__isnull=False)
	argument = "condition" if DJANGO_VERSION >= (5, 1) else "check"
	return models.CheckConstraint(**{argument: condition, "name": "vol_attendance_target"})

MAX_UPLOAD_FILE_SIZE_BYTES = 25 * 1024 * 1024


def skill_learning_topic_cover_upload_to(instance, filename):
	extension = os.path.splitext(filename)[1].lower()
	random_name = f"{uuid.uuid4().hex}{extension}"
	topic_id = getattr(instance, "id", None) or uuid.uuid4().hex
	return f"skill_learning/topics/{topic_id}/{random_name}"


def skill_learning_material_upload_to(instance, filename):
	extension = os.path.splitext(filename)[1].lower()
	random_name = f"{uuid.uuid4().hex}{extension}"
	topic_id = getattr(instance, "topic_id", None) or "unassigned"
	return f"skill_learning/materials/topic_{topic_id}/{random_name}"


def resource_library_upload_to(instance, filename):
	extension = os.path.splitext(filename)[1].lower()
	random_name = f"{uuid.uuid4().hex}{extension}"
	return f"resource_library/{random_name}"


def material_submission_upload_to(instance, filename):
	extension = os.path.splitext(filename)[1].lower()
	random_name = f"{uuid.uuid4().hex}{extension}"
	return f"material_submissions/user_{instance.submission.user_id}/{instance.submission.id}/{random_name}"


def user_avatar_upload_to(instance, filename):
	extension = os.path.splitext(filename)[1].lower()
	random_name = f"{uuid.uuid4().hex}{extension}"
	return f"profile_avatars/user_{instance.user_id}/{random_name}"


def community_post_attachment_upload_to(instance, filename):
	extension = os.path.splitext(filename)[1].lower()
	random_name = f"{uuid.uuid4().hex}{extension}"
	return f"community_posts/user_{instance.post.user_id}/{instance.post.id}/{random_name}"


def volunteer_admin_attachment_upload_to(instance, filename):
	extension = os.path.splitext(filename)[1].lower()
	random_name = f"{uuid.uuid4().hex}{extension}"
	return f"volunteer_admin_chat/user_{instance.message.thread_user_id}/{random_name}"


def volunteer_certificate_upload_to(instance, filename):
	extension = os.path.splitext(filename)[1].lower() or ".pdf"
	random_name = f"{uuid.uuid4().hex}{extension}"
	return f"certificates/volunteer_{instance.volunteer_id}/{random_name}"


def activity_cover_upload_to(instance, filename):
	extension = os.path.splitext(filename)[1].lower()
	random_name = f"{uuid.uuid4().hex}{extension}"
	return f"activities/{instance.id or 'new'}/{random_name}"


class MaterialSubmission(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="material_submissions")
	topic_id = models.CharField(max_length=120)
	topic_title = models.CharField(max_length=255, blank=True)
	material_id = models.CharField(max_length=120)
	material_title = models.CharField(max_length=255, blank=True)
	note = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		indexes = [
			models.Index(fields=["user", "topic_id", "material_id"]),
			models.Index(fields=["-created_at"]),
		]
		ordering = ["-created_at"]

	def __str__(self):
		return f"{self.user_id}:{self.topic_id}:{self.material_id}"


class MaterialSubmissionFile(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	submission = models.ForeignKey(MaterialSubmission, on_delete=models.CASCADE, related_name="files")
	file = models.FileField(upload_to=material_submission_upload_to)
	original_name = models.CharField(max_length=255)
	mime_type = models.CharField(max_length=120, blank=True)
	size_bytes = models.PositiveBigIntegerField(default=0)
	uploaded_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["uploaded_at"]

	def clean(self):
		if not self.file:
			raise ValidationError("A file is required.")

		name = getattr(self.file, "name", "") or ""
		extension = os.path.splitext(name)[1].lower().lstrip(".")
		if extension not in ALLOWED_UPLOAD_EXTENSIONS:
			raise ValidationError("This file type is not allowed.")

		content_type = str(getattr(self.file, "content_type", "") or "").lower()
		if content_type and content_type not in ALLOWED_UPLOAD_MIME_TYPES and content_type != "application/octet-stream":
			raise ValidationError("Unsupported file content type.")

		file_size = getattr(self.file, "size", 0) or 0
		if file_size > MAX_UPLOAD_FILE_SIZE_BYTES:
			raise ValidationError("Each file must be 25 MB or smaller.")

	def save(self, *args, **kwargs):
		if self.file:
			if not self.original_name:
				self.original_name = os.path.basename(getattr(self.file, "name", ""))
			self.mime_type = str(getattr(self.file, "content_type", "") or "").lower()
			self.size_bytes = getattr(self.file, "size", 0) or 0
		self.full_clean()
		super().save(*args, **kwargs)


class SkillLearningTopic(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	title = models.CharField(max_length=255)
	description = models.TextField()
	badge_label = models.CharField(max_length=120)
	filter_tags = models.JSONField(default=list, blank=True)
	cover_image = models.ImageField(upload_to=skill_learning_topic_cover_upload_to, blank=True, null=True)
	cover_image_url = models.URLField(blank=True)
	is_recommended = models.BooleanField(default=False)
	popularity_score = models.PositiveIntegerField(default=0)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-is_recommended", "-popularity_score", "-created_at", "-id"]

	def __str__(self):
		return self.title

	def delete(self, *args, **kwargs):
		for material in list(self.materials.all()):
			material.delete()
		if self.cover_image:
			self.cover_image.delete(save=False)
		super().delete(*args, **kwargs)

	@property
	def cover_image_src(self):
		if self.cover_image:
			try:
				return self.cover_image.url
			except ValueError:
				return self.cover_image_url or ""
		return self.cover_image_url or ""

	@property
	def primary_filter_tag(self):
		tags = self.filter_tags if isinstance(self.filter_tags, list) else []
		for tag in ("Community", "Children", "New", "Popular"):
			if tag in tags:
				return tag
		return "Community"


class SkillLearningMaterial(models.Model):
	TYPE_DOCUMENT = "document"
	TYPE_VIDEO = "video"
	TYPE_REFERENCE_GUIDE = "reference_guide"
	TYPE_CHOICES = (
		(TYPE_DOCUMENT, "Document"),
		(TYPE_VIDEO, "Video"),
		(TYPE_REFERENCE_GUIDE, "Reference Guide"),
	)

	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	topic = models.ForeignKey(SkillLearningTopic, on_delete=models.CASCADE, related_name="materials")
	material_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
	title = models.CharField(max_length=255)
	description = models.TextField(blank=True)
	file_upload = models.FileField(upload_to=skill_learning_material_upload_to, blank=True, null=True)
	external_url = models.URLField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["created_at", "id"]

	def __str__(self):
		return self.title

	def delete(self, *args, **kwargs):
		if self.file_upload:
			self.file_upload.delete(save=False)
		super().delete(*args, **kwargs)

	@property
	def source_url(self):
		if self.file_upload:
			try:
				return self.file_upload.url
			except ValueError:
				return self.external_url or ""
		return self.external_url or ""

	@property
	def source_name(self):
		if self.file_upload:
			return os.path.basename(getattr(self.file_upload, "name", ""))
		return self.external_url or ""


class ResourceLibraryMaterial(models.Model):
	CATEGORY_RAG_MAKING = "rag-making"
	CATEGORY_TEACHING_KIDS = "teaching-kids"
	CATEGORY_PLANTING = "planting"
	CATEGORY_OUTREACH = "outreach"
	CATEGORY_OTHER = "other"
	CATEGORY_CHOICES = (
		(CATEGORY_RAG_MAKING, "Rag-making"),
		(CATEGORY_TEACHING_KIDS, "Teaching Kids"),
		(CATEGORY_PLANTING, "Planting"),
		(CATEGORY_OUTREACH, "Outreach"),
		(CATEGORY_OTHER, "Other"),
	)

	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	title = models.CharField(max_length=255)
	description = models.TextField(blank=True)
	category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
	custom_category = models.CharField(max_length=80, blank=True)
	file_upload = models.FileField(upload_to=resource_library_upload_to, blank=True, null=True)
	external_url = models.URLField(blank=True)
	is_published = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-created_at", "title"]

	def __str__(self):
		return self.title

	def clean(self):
		super().clean()
		if self.category == self.CATEGORY_OTHER:
			if not self.custom_category.strip():
				raise ValidationError({"custom_category": "Enter a name for this category."})
		elif self.custom_category:
			self.custom_category = ""

		if bool(self.file_upload) == bool(self.external_url):
			raise ValidationError("Provide either an uploaded file or an external link.")

		if self.file_upload:
			name = getattr(self.file_upload, "name", "") or ""
			extension = os.path.splitext(name)[1].lower().lstrip(".")
			if extension not in ALLOWED_UPLOAD_EXTENSIONS:
				raise ValidationError({"file_upload": "This file type is not allowed."})

			content_type = str(getattr(self.file_upload, "content_type", "") or "").lower()
			if content_type and content_type not in ALLOWED_UPLOAD_MIME_TYPES and content_type != "application/octet-stream":
				raise ValidationError({"file_upload": "Unsupported file content type."})

			if (getattr(self.file_upload, "size", 0) or 0) > MAX_UPLOAD_FILE_SIZE_BYTES:
				raise ValidationError({"file_upload": "The file must be 25 MB or smaller."})

	def save(self, *args, **kwargs):
		self.full_clean()
		super().save(*args, **kwargs)

	def delete(self, *args, **kwargs):
		if self.file_upload:
			self.file_upload.delete(save=False)
		super().delete(*args, **kwargs)

	@property
	def source_url(self):
		if self.file_upload:
			try:
				return self.file_upload.url
			except ValueError:
				return self.external_url or ""
		return self.external_url or ""

	@property
	def file_type_label(self):
		if self.external_url:
			return "LINK"
		extension = os.path.splitext(getattr(self.file_upload, "name", ""))[1].lower().lstrip(".")
		if extension in {"mp4", "mov", "avi", "mkv", "webm"}:
			return "VIDEO"
		return extension.upper() or "FILE"

	@property
	def preview_kind(self):
		if self.external_url:
			return "link"
		extension = os.path.splitext(getattr(self.file_upload, "name", ""))[1].lower().lstrip(".")
		if extension == "pdf":
			return "pdf"
		if extension in {"png", "jpg", "jpeg", "jfif", "gif", "webp", "bmp", "svg"}:
			return "image"
		if extension in {"mp4", "mov", "avi", "mkv", "webm"}:
			return "video"
		if extension in {"mp3", "wav", "m4a", "aac", "ogg"}:
			return "audio"
		return "document"

	@property
	def resource_type(self):
		return self.file_type_label

	@property
	def category_label(self):
		if self.category == self.CATEGORY_OTHER and self.custom_category.strip():
			return self.custom_category.strip()
		return self.get_category_display()


class SkillLearningTopicEngagement(models.Model):
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="skill_learning_topic_engagements")
	topic = models.ForeignKey(SkillLearningTopic, on_delete=models.CASCADE, related_name="engagements")
	page_open_count = models.PositiveIntegerField(default=0)
	last_accessed_at = models.DateTimeField(null=True, blank=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=["user", "topic"], name="unique_skill_topic_user_engagement"),
		]


class SkillLearningMaterialEngagement(models.Model):
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="skill_learning_material_engagements")
	material = models.ForeignKey(SkillLearningMaterial, on_delete=models.CASCADE, related_name="engagements")
	view_count = models.PositiveIntegerField(default=0)
	completed_at = models.DateTimeField(null=True, blank=True)
	last_accessed_at = models.DateTimeField(null=True, blank=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=["user", "material"], name="unique_skill_material_user_engagement"),
		]


class UserProfile(models.Model):
	ROLE_REGULAR = "regular"
	ROLE_BENEFICIARY = "beneficiary"
	ROLE_VOLUNTEER = "volunteer"
	ROLE_CHOICES = (
		(ROLE_REGULAR, "Regular User"),
		(ROLE_BENEFICIARY, "Beneficiary"),
		(ROLE_VOLUNTEER, "Volunteer"),
	)

	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="userprofile")
	account_role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_REGULAR)
	avatar = models.ImageField(upload_to=user_avatar_upload_to, blank=True, null=True)
	settings_state = models.JSONField(default=dict, blank=True)
	phone = models.CharField(max_length=50, blank=True)
	birthdate = models.DateField(blank=True, null=True)
	civil_status = models.CharField(max_length=30, blank=True)
	address_line = models.CharField(max_length=255, blank=True)
	barangay = models.CharField(max_length=120, blank=True)
	city_municipality = models.CharField(max_length=120, blank=True)
	emergency_contact_name = models.CharField(max_length=150, blank=True)
	emergency_contact_relationship = models.CharField(max_length=80, blank=True)
	emergency_contact_phone = models.CharField(max_length=50, blank=True)
	volunteer_role = models.CharField(max_length=80, blank=True)
	assigned_chapter_area = models.CharField(max_length=150, blank=True)
	ojt_hours = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	required_ojt_hours = models.DecimalField(max_digits=10, decimal_places=2, default=80)
	ojt_supervisor = models.CharField(max_length=150, blank=True)
	ojt_program = models.CharField(max_length=150, blank=True)
	ojt_next_check_in = models.DateField(blank=True, null=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f"profile:{self.user_id}"


class AdminSystemSettings(models.Model):
	key = models.CharField(max_length=32, primary_key=True, default="global", editable=False)
	settings = models.JSONField(default=dict, blank=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f"admin-settings:{self.key}"


class AdminUserPreferences(models.Model):
	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="admin_ui_preferences")
	preferences = models.JSONField(default=dict, blank=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f"admin-preferences:{self.user_id}"


class VolunteerOjtSchedule(models.Model):
	volunteer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ojt_schedules")
	effective_from = models.DateField()
	effective_until = models.DateField(blank=True, null=True)
	weekdays = models.JSONField(default=list, blank=True)
	daily_times = models.JSONField(default=dict, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["effective_from", "id"]
		constraints = [
			models.UniqueConstraint(fields=["volunteer", "effective_from"], name="uniq_vol_ojt_start"),
		]

	def __str__(self):
		return f"ojt-schedule:{self.volunteer_id}:{self.effective_from}"


class RoleApplication(models.Model):
	ROLE_BENEFICIARY = "beneficiary"
	ROLE_VOLUNTEER = "volunteer"
	ROLE_CHOICES = (
		(ROLE_BENEFICIARY, "Beneficiary"),
		(ROLE_VOLUNTEER, "Volunteer"),
	)

	STATUS_PENDING = "pending"
	STATUS_APPROVED = "approved"
	STATUS_INACTIVE = "inactive"
	STATUS_REJECTED = "rejected"
	STATUS_CHOICES = (
		(STATUS_PENDING, "Pending"),
		(STATUS_APPROVED, "Approved"),
		(STATUS_INACTIVE, "Inactive"),
		(STATUS_REJECTED, "Rejected"),
	)

	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="role_applications", null=True, blank=True)
	role = models.CharField(max_length=20, choices=ROLE_CHOICES)
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
	full_name = models.CharField(max_length=150)
	contact_details = models.TextField()
	reason_for_assistance = models.TextField(blank=True)
	supporting_information = models.TextField(blank=True)
	skills = models.TextField(blank=True)
	availability = models.TextField(blank=True)
	areas_of_interest = models.TextField(blank=True)
	reviewed_at = models.DateTimeField(blank=True, null=True)
	reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name="reviewed_role_applications")
	admin_notes = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-created_at", "-id"]
		indexes = [
			models.Index(fields=["user", "role", "status"]),
			models.Index(fields=["-created_at"]),
		]

	def __str__(self):
		return f"role-application:{self.user_id}:{self.role}:{self.status}"


class BeneficiaryAssistanceRecord(models.Model):
	beneficiary = models.ForeignKey(RoleApplication, on_delete=models.CASCADE, related_name="assistance_records")
	aid_type = models.CharField(max_length=150)
	quantity_or_amount = models.CharField(max_length=120)
	assistance_date = models.DateField()
	assigned_volunteer = models.ForeignKey(
		User,
		on_delete=models.SET_NULL,
		blank=True,
		null=True,
		related_name="beneficiary_assistance_records",
	)
	notes = models.TextField(blank=True)
	recorded_by = models.ForeignKey(
		User,
		on_delete=models.SET_NULL,
		blank=True,
		null=True,
		related_name="recorded_beneficiary_assistance",
	)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-assistance_date", "-created_at", "-id"]
		indexes = [
			models.Index(fields=["beneficiary", "-assistance_date"]),
			models.Index(fields=["assigned_volunteer", "-assistance_date"]),
		]

	def __str__(self):
		return f"beneficiary-assistance:{self.beneficiary_id}:{self.assistance_date}:{self.id}"


class BeneficiaryAssistanceFeedback(models.Model):
	assistance_record = models.OneToOneField(
		BeneficiaryAssistanceRecord,
		on_delete=models.CASCADE,
		related_name="feedback",
	)
	beneficiary = models.ForeignKey(
		RoleApplication,
		on_delete=models.CASCADE,
		related_name="assistance_feedback",
	)
	user = models.ForeignKey(
		User,
		on_delete=models.CASCADE,
		related_name="beneficiary_assistance_feedback",
	)
	rating = models.PositiveSmallIntegerField(default=0)
	comment = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=["assistance_record"], name="unique_feedback_per_assistance_record"),
		]
		ordering = ["-created_at", "-id"]

	def __str__(self):
		return f"beneficiary-assistance-feedback:{self.assistance_record_id}:{self.rating}"


class BeneficiaryActivityFeedback(models.Model):
	activity = models.ForeignKey(
		"Activity",
		on_delete=models.CASCADE,
		related_name="beneficiary_feedback",
	)
	beneficiary = models.ForeignKey(
		RoleApplication,
		on_delete=models.CASCADE,
		related_name="activity_feedback",
	)
	user = models.ForeignKey(
		User,
		on_delete=models.CASCADE,
		related_name="beneficiary_activity_feedback",
	)
	rating = models.PositiveSmallIntegerField(default=0)
	comment = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=["activity", "beneficiary"], name="unique_feedback_per_beneficiary_activity"),
		]
		ordering = ["-created_at", "-id"]

	def __str__(self):
		return f"beneficiary-activity-feedback:{self.activity_id}:{self.beneficiary_id}:{self.rating}"


class Activity(models.Model):
	CATEGORY_OTHER = "other"
	CATEGORY_CHOICES = (
		("rag-making", "Rag-making"),
		("teaching-kids", "Teaching Kids"),
		("pagtatanim", "Planting"),
		("outreach", "Outreach"),
		(CATEGORY_OTHER, "Other"),
	)
	STATUS_ACTIVE = "active"
	STATUS_DRAFT = "draft"
	STATUS_CANCELLED = "cancelled"
	STATUS_COMPLETED = "completed"
	STATUS_CHOICES = (
		(STATUS_ACTIVE, "Active"),
		(STATUS_DRAFT, "Draft"),
		(STATUS_CANCELLED, "Cancelled"),
		(STATUS_COMPLETED, "Completed"),
	)

	title = models.CharField(max_length=255)
	description = models.TextField(blank=True)
	date = models.DateField()
	start_time = models.TimeField(blank=True, null=True)
	end_time = models.TimeField(blank=True, null=True)
	location = models.CharField(max_length=255, blank=True)
	category = models.CharField(max_length=120, choices=CATEGORY_CHOICES, default="")
	image = models.ImageField(upload_to=activity_cover_upload_to, blank=True, null=True)
	volunteer_count = models.PositiveIntegerField(default=0)
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["date", "title"]
		indexes = [
			models.Index(fields=["date"]),
			models.Index(fields=["status"]),
		]

	def __str__(self):
		return self.title

	@property
	def time_label(self):
		if self.start_time and self.end_time:
			return f"{self.start_time.strftime('%I:%M %p').lstrip('0')} – {self.end_time.strftime('%I:%M %p').lstrip('0')}"
		if self.start_time:
			return self.start_time.strftime('%I:%M %p').lstrip('0')
		return "TBA"


class ActivityBeneficiaryAssignment(models.Model):
	activity = models.ForeignKey("Activity", on_delete=models.CASCADE, related_name="beneficiary_assignments")
	beneficiary = models.ForeignKey(User, on_delete=models.CASCADE, related_name="activity_beneficiary_assignments")
	assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name="assigned_activity_beneficiaries")
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=["activity", "beneficiary"], name="unique_activity_beneficiary_assignment"),
		]
		ordering = ["beneficiary__first_name", "beneficiary__last_name", "beneficiary_id"]

	def __str__(self):
		return f"activity-beneficiary:{self.activity_id}:{self.beneficiary_id}"


class BeneficiaryActivityAttendance(models.Model):
	STATUS_PENDING = "pending"
	STATUS_CONFIRMED = "confirmed"
	STATUS_REJECTED = "rejected"
	STATUS_CHOICES = (
		(STATUS_PENDING, "Pending"),
		(STATUS_CONFIRMED, "Confirmed"),
		(STATUS_REJECTED, "Rejected"),
	)

	activity = models.ForeignKey("Activity", on_delete=models.CASCADE, related_name="beneficiary_attendance_records")
	beneficiary = models.ForeignKey(User, on_delete=models.CASCADE, related_name="beneficiary_activity_attendance_records")
	volunteer = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name="beneficiary_attendance_confirmations")
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
	confirmed_at = models.DateTimeField(blank=True, null=True)
	reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name="reviewed_beneficiary_attendance")
	reviewed_at = models.DateTimeField(blank=True, null=True)
	notes = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=["activity", "beneficiary", "volunteer"], name="unique_activity_beneficiary_volunteer_attendance"),
		]
		ordering = ["-confirmed_at", "-created_at", "-id"]

	def __str__(self):
		return f"beneficiary-attendance:{self.activity_id}:{self.beneficiary_id}:{self.volunteer_id}:{self.status}"


class VolunteerActivityAssignment(models.Model):
	STATUS_UPCOMING = "upcoming"
	STATUS_TIME_IN = "time_in"
	STATUS_IN_PROGRESS = "in_progress"
	STATUS_AWAITING_CONFIRMATION = "awaiting_confirmation"
	STATUS_COMPLETED = "completed"
	STATUS_MISSED = "missed"
	STATUS_CANCELLED = "cancelled"
	STATUS_PENDING = "pending"
	STATUS_CHOICES = (
		(STATUS_UPCOMING, "Upcoming"),
		(STATUS_TIME_IN, "Time In"),
		(STATUS_IN_PROGRESS, "In Progress"),
		(STATUS_AWAITING_CONFIRMATION, "Awaiting Confirmation"),
		(STATUS_COMPLETED, "Completed"),
		(STATUS_MISSED, "Missed"),
		(STATUS_CANCELLED, "Cancelled"),
		(STATUS_PENDING, "Pending"),
	)

	activity = models.ForeignKey("Activity", on_delete=models.SET_NULL, related_name="volunteer_assignments", blank=True, null=True)
	volunteer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="volunteer_activity_assignments")
	activity_name = models.CharField(max_length=255)
	activity_type = models.CharField(max_length=80, blank=True)
	scheduled_date = models.DateField()
	scheduled_time = models.TimeField(blank=True, null=True)
	location = models.CharField(max_length=255, blank=True)
	notes = models.TextField(blank=True)
	status = models.CharField(max_length=24, choices=STATUS_CHOICES, default=STATUS_PENDING)
	attendance_started_at = models.DateTimeField(blank=True, null=True)
	attendance_ended_at = models.DateTimeField(blank=True, null=True)
	assigned_by = models.ForeignKey(
		User,
		on_delete=models.SET_NULL,
		blank=True,
		null=True,
		related_name="assigned_volunteer_activities",
	)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["scheduled_date", "scheduled_time", "activity_name"]
		indexes = [
			models.Index(fields=["volunteer", "scheduled_date"]),
			models.Index(fields=["status", "scheduled_date"]),
		]

	def __str__(self):
		return f"assignment:{self.volunteer_id}:{self.activity_name}:{self.scheduled_date}"

	@property
	def current_status_label(self):
		return dict(self.STATUS_CHOICES).get(self.status, self.status.replace("_", " ").title())


class VolunteerAttendanceRecord(models.Model):
	STATUS_ACTIVE = "active"
	STATUS_PENDING = "pending"
	STATUS_CONFIRMED = "confirmed"
	STATUS_REJECTED = "rejected"
	STATUS_CHOICES = (
		(STATUS_ACTIVE, "Active"),
		(STATUS_PENDING, "Pending"),
		(STATUS_CONFIRMED, "Confirmed"),
		(STATUS_REJECTED, "Rejected"),
	)

	assignment = models.ForeignKey(VolunteerActivityAssignment, on_delete=models.CASCADE, related_name="attendance_records", blank=True, null=True)
	volunteer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="volunteer_attendance_records")
	duty_schedule = models.ForeignKey(VolunteerOjtSchedule, on_delete=models.SET_NULL, related_name="attendance_records", blank=True, null=True)
	duty_date = models.DateField(blank=True, null=True)
	time_in = models.DateTimeField(blank=True, null=True)
	time_out = models.DateTimeField(blank=True, null=True)
	duration_minutes = models.PositiveIntegerField(default=0)
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
	auto_closed = models.BooleanField(default=False)
	reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name="reviewed_volunteer_attendance")
	reviewed_at = models.DateTimeField(blank=True, null=True)
	notes = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-time_out", "-time_in", "-created_at", "-id"]
		indexes = [
			models.Index(fields=["volunteer", "status", "time_out"]),
			models.Index(fields=["assignment", "status"]),
		]
		constraints = [
			_attendance_target_constraint(),
			models.UniqueConstraint(fields=["volunteer", "duty_date"], condition=models.Q(duty_date__isnull=False), name="uniq_vol_duty_date"),
		]

	def __str__(self):
		return f"attendance:{self.volunteer_id}:{self.assignment_id}:{self.status}"

	@property
	def duration_hours(self):
		return round(self.duration_minutes / 60, 2) if self.duration_minutes else 0


class VolunteerCertificate(models.Model):
	volunteer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="volunteer_certificates")
	issued_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="issued_volunteer_certificates")
	recipient_name = models.CharField(max_length=255)
	reason = models.TextField()
	pdf_file = models.FileField(upload_to=volunteer_certificate_upload_to, blank=True, null=True)
	issued_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["-issued_at", "-id"]

	def __str__(self):
		return f"certificate:{self.volunteer_id}:{self.recipient_name}"


class CommunityPost(models.Model):
	POST_TYPES = (
		("discussions", "Discussions"),
		("tips", "Tips"),
		("announcements", "Announcements"),
	)

	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="community_posts")
	activity = models.OneToOneField("Activity", on_delete=models.CASCADE, related_name="community_post", blank=True, null=True)
	content = models.TextField()
	post_type = models.CharField(max_length=30, choices=POST_TYPES, default="discussions")
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["-created_at"]

	def __str__(self):
		return f"community:{self.user_id}:{self.id}"


class CommunityPostReport(models.Model):
	REASON_SPAM = "spam"
	REASON_INAPPROPRIATE = "inappropriate_content"
	REASON_HARASSMENT = "harassment_or_bullying"
	REASON_FALSE_INFORMATION = "false_information"
	REASON_OTHER = "other"
	REASON_CHOICES = (
		(REASON_SPAM, "Spam"),
		(REASON_INAPPROPRIATE, "Inappropriate content"),
		(REASON_HARASSMENT, "Harassment or bullying"),
		(REASON_FALSE_INFORMATION, "False information"),
		(REASON_OTHER, "Other"),
	)

	post = models.ForeignKey("CommunityPost", on_delete=models.CASCADE, related_name="reports")
	reported_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="community_post_reports")
	reason = models.CharField(max_length=40, choices=REASON_CHOICES)
	details = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-created_at", "-id"]
		indexes = [
			models.Index(fields=["post", "reported_by"]),
		]

	def __str__(self):
		return f"community-report:{self.post_id}:{self.reported_by_id}:{self.reason}"


class CommunityPostAttachment(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	post = models.ForeignKey(CommunityPost, on_delete=models.CASCADE, related_name="attachments")
	file = models.FileField(upload_to=community_post_attachment_upload_to)
	original_name = models.CharField(max_length=255)
	mime_type = models.CharField(max_length=120, blank=True)
	size_bytes = models.PositiveBigIntegerField(default=0)
	uploaded_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["uploaded_at"]

	def clean(self):
		if not self.file:
			raise ValidationError("A file is required.")

		name = getattr(self.file, "name", "") or ""
		extension = os.path.splitext(name)[1].lower().lstrip(".")
		if extension not in ALLOWED_UPLOAD_EXTENSIONS:
			raise ValidationError("This file type is not allowed.")

		content_type = str(getattr(self.file, "content_type", "") or "").lower()
		if content_type and content_type not in ALLOWED_UPLOAD_MIME_TYPES and content_type != "application/octet-stream":
			raise ValidationError("Unsupported file content type.")

		file_size = getattr(self.file, "size", 0) or 0
		if file_size > MAX_UPLOAD_FILE_SIZE_BYTES:
			raise ValidationError("Each file must be 25 MB or smaller.")

	def save(self, *args, **kwargs):
		if self.file:
			if not self.original_name:
				self.original_name = os.path.basename(getattr(self.file, "name", ""))
			self.mime_type = str(getattr(self.file, "content_type", "") or "").lower()
			self.size_bytes = getattr(self.file, "size", 0) or 0
		self.full_clean()
		super().save(*args, **kwargs)


class CommunityPostLike(models.Model):
	post = models.ForeignKey(CommunityPost, on_delete=models.CASCADE, related_name="likes")
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="community_post_likes")
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=["post", "user"], name="webapp_unique_post_like"),
		]
		ordering = ["-created_at"]

	def __str__(self):
		return f"community-like:{self.post_id}:{self.user_id}"


class CommunityPostComment(models.Model):
	post = models.ForeignKey(CommunityPost, on_delete=models.CASCADE, related_name="comments")
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="community_post_comments")
	parent = models.ForeignKey("self", on_delete=models.CASCADE, related_name="replies", null=True, blank=True)
	content = models.TextField()
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["created_at", "id"]
		indexes = [
			models.Index(fields=["post", "created_at"]),
			models.Index(fields=["post", "parent", "created_at"]),
		]

	def clean(self):
		if self.parent_id and self.parent_id == self.id:
			raise ValidationError("A comment cannot reply to itself.")

		if self.parent_id and self.parent and self.parent.post_id != self.post_id:
			raise ValidationError("Replies must belong to the same post.")

	def save(self, *args, **kwargs):
		self.full_clean()
		super().save(*args, **kwargs)

	def __str__(self):
		return f"community-comment:{self.post_id}:{self.user_id}:{self.id}"


class CommunityPostCommentLike(models.Model):
	comment = models.ForeignKey(CommunityPostComment, on_delete=models.CASCADE, related_name="likes")
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="community_post_comment_likes")
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=["comment", "user"], name="webapp_unique_comment_like"),
		]
		ordering = ["-created_at"]

	def __str__(self):
		return f"community-comment-like:{self.comment_id}:{self.user_id}"


def product_inquiry_screenshot_upload_to(instance, filename):
	extension = os.path.splitext(filename)[1].lower()
	random_name = f"{uuid.uuid4().hex}{extension}"
	return f"product_inquiries/user_{instance.user_id or 'anonymous'}/{random_name}"


def donation_receipt_upload_to(instance, filename):
	random_name = uuid.uuid4().hex
	return f"donations/user_{instance.user_id or 'anonymous'}/{random_name}"


def donation_official_receipt_upload_to(instance, filename):
	extension = os.path.splitext(filename)[1].lower()
	random_name = f"{uuid.uuid4().hex}{extension}"
	return f"donation_receipts/user_{instance.user_id or 'anonymous'}/{random_name}"


class ProductInquiry(models.Model):
	PAYMENT_GCASH = "gcash"
	PAYMENT_BANK_TRANSFER = "bank_transfer"
	PAYMENT_COD = "cod"
	PAYMENT_CARD = "card"
	PAYMENT_METHOD_CHOICES = (
		(PAYMENT_GCASH, "GCash"),
		(PAYMENT_BANK_TRANSFER, "Bank Transfer"),
		(PAYMENT_COD, "Cash on Delivery"),
		(PAYMENT_CARD, "Card"),
	)

	STATUS_PENDING = "pending"
	STATUS_VERIFIED = "verified"
	STATUS_COMPLETED = "completed"
	STATUS_FAILED = "failed"
	STATUS_REFUNDED = "refunded"
	STATUS_CANCELLED = "cancelled"
	STATUS_CHOICES = (
		(STATUS_PENDING, "Pending"),
		(STATUS_VERIFIED, "Verified"),
		(STATUS_COMPLETED, "Completed"),
		(STATUS_FAILED, "Failed"),
		(STATUS_REFUNDED, "Refunded"),
		(STATUS_CANCELLED, "Cancelled"),
	)

	user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name="product_inquiries")
	full_name = models.CharField(max_length=150)
	email = models.EmailField()
	phone = models.CharField(max_length=50)
	country_code = models.CharField(max_length=10, default="+63")
	message = models.TextField(blank=True)
	payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
	payment_screenshot = models.ImageField(upload_to=product_inquiry_screenshot_upload_to, blank=True, null=True)
	order_items = models.JSONField(default=list)
	order_total = models.PositiveIntegerField(default=0)
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
	delivery_street = models.CharField(max_length=255, blank=True)
	delivery_city = models.CharField(max_length=150, blank=True)
	delivery_province = models.CharField(max_length=150, blank=True)
	delivery_zip = models.CharField(max_length=20, blank=True)
	delivery_country = models.CharField(max_length=100, default='Philippines')
	admin_notification = models.TextField()
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-created_at", "-id"]
		indexes = [
			models.Index(fields=["payment_method", "-created_at"]),
			models.Index(fields=["-created_at"]),
		]

	def clean(self):
		return

	def save(self, *args, **kwargs):
		self.full_clean()
		super().save(*args, **kwargs)

	def __str__(self):
		return f"product-inquiry:{self.full_name}:{self.payment_method}:{self.id}"


class Donation(models.Model):
	PAYMENT_GCASH = "gcash"
	PAYMENT_BANK_TRANSFER = "bank_transfer"
	PAYMENT_CASH = "cash"
	PAYMENT_CARD = "card"
	PAYMENT_EWALLET = "ewallet"
	PAYMENT_METHOD_CHOICES = (
		(PAYMENT_GCASH, "GCash"),
		(PAYMENT_BANK_TRANSFER, "Bank Transfer"),
		(PAYMENT_CASH, "Cash"),
		(PAYMENT_CARD, "Credit Card"),
		(PAYMENT_EWALLET, "E-wallet"),
	)

	STATUS_PENDING = "pending"
	STATUS_VERIFIED = "verified"
	STATUS_COMPLETED = "completed"
	STATUS_REJECTED = "rejected"
	STATUS_CANCELLED = "cancelled"
	STATUS_CHOICES = (
		(STATUS_PENDING, "Pending"),
		(STATUS_VERIFIED, "Verified"),
		(STATUS_COMPLETED, "Completed"),
		(STATUS_REJECTED, "Rejected"),
		(STATUS_CANCELLED, "Cancelled"),
	)

	user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name="donations")
	reference_number = models.CharField(max_length=32, unique=True)
	donor_name = models.CharField(max_length=150, blank=True)
	donor_email = models.EmailField(blank=True, null=True)
	donor_message = models.TextField(blank=True)
	campaign = models.CharField(max_length=150, default="General Donation")
	amount = models.PositiveIntegerField(default=0)
	payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
	receipt = models.FileField(upload_to=donation_receipt_upload_to, blank=True, null=True)
	official_receipt_number = models.CharField(max_length=64, blank=True, null=True, unique=True)
	official_receipt_file = models.FileField(upload_to=donation_official_receipt_upload_to, blank=True, null=True)
	official_receipt_generated_at = models.DateTimeField(blank=True, null=True)
	impact_update = models.TextField(blank=True)
	impact_update_sent_at = models.DateTimeField(blank=True, null=True)
	verified_at = models.DateTimeField(blank=True, null=True)
	verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name="verified_donations")
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
	review_notes = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-created_at", "-id"]
		indexes = [
			models.Index(fields=["status", "-created_at"]),
			models.Index(fields=["payment_method", "-created_at"]),
			models.Index(fields=["-created_at"]),
		]

	def clean(self):
		if self.amount <= 0:
			raise ValidationError("Donation amount must be greater than zero.")
		if self.payment_method in {self.PAYMENT_GCASH, self.PAYMENT_BANK_TRANSFER} and not self.receipt:
			raise ValidationError("A receipt is required for this payment method.")
		if self.receipt:
			file_size = getattr(self.receipt, "size", 0) or 0
			if file_size > 5 * 1024 * 1024:
				raise ValidationError("The receipt must be 5 MB or smaller.")
			content_type = str(getattr(self.receipt, "content_type", "") or "").lower()
			if content_type and content_type not in {"application/pdf", "image/jpeg", "image/jpg", "image/png", "image/webp"}:
				raise ValidationError("Receipt must be a PDF, JPEG, PNG, or WebP image.")

	def save(self, *args, **kwargs):
		if not self.reference_number:
			self.reference_number = f"D-{uuid.uuid4().hex[:10].upper()}"
		self.full_clean()
		super().save(*args, **kwargs)

	def __str__(self):
		return f"donation:{self.reference_number}:{self.amount}:{self.status}"


class CommunityNotification(models.Model):
	TYPE_POST_LIKE = "post_like"
	TYPE_POST_COMMENT = "post_comment"
	TYPE_COMMENT_REPLY = "comment_reply"
	TYPE_ROLE_APPLICATION = "role_application"
	TYPE_BENEFICIARY_APPLICATION_DECISION = "beneficiary_application_decision"
	TYPE_VOLUNTEER_APPLICATION_DECISION = "volunteer_application_decision"
	TYPE_VOLUNTEER_ASSIGNMENT = "volunteer_assignment"
	TYPE_ACTIVITY_END_REMINDER = "activity_end_reminder"
	TYPE_ACTIVITY_ANNOUNCEMENT = "activity_announcement"
	TYPE_DONATION_IMPACT = "donation_impact"
	NOTIFICATION_TYPES = (
		(TYPE_POST_LIKE, "Post like"),
		(TYPE_POST_COMMENT, "Post comment"),
		(TYPE_COMMENT_REPLY, "Comment reply"),
		(TYPE_ROLE_APPLICATION, "Role application"),
		(TYPE_BENEFICIARY_APPLICATION_DECISION, "Beneficiary application decision"),
		(TYPE_VOLUNTEER_APPLICATION_DECISION, "Volunteer application decision"),
		(TYPE_VOLUNTEER_ASSIGNMENT, "Volunteer assignment"),
		(TYPE_ACTIVITY_END_REMINDER, "Activity end reminder"),
		(TYPE_ACTIVITY_ANNOUNCEMENT, "Activity announcement"),
		(TYPE_DONATION_IMPACT, "Donation impact update"),
	)

	recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="community_notifications")
	actor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="community_notification_events")
	notification_type = models.CharField(max_length=40, choices=NOTIFICATION_TYPES)
	post = models.ForeignKey(CommunityPost, on_delete=models.CASCADE, related_name="notifications", null=True, blank=True)
	comment = models.ForeignKey(CommunityPostComment, on_delete=models.CASCADE, related_name="notifications", null=True, blank=True)
	message = models.CharField(max_length=255)
	target_url = models.CharField(max_length=255, default="/user-dashboard/community/")
	is_read = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["-created_at"]
		indexes = [
			models.Index(fields=["recipient", "-created_at"]),
			models.Index(fields=["recipient", "is_read", "-created_at"]),
		]

	def clean(self):
		if self.recipient_id and self.actor_id and self.recipient_id == self.actor_id:
			raise ValidationError("Actor and recipient must be different users.")

	def __str__(self):
		return f"community-notification:{self.recipient_id}:{self.notification_type}:{self.id}"


class VolunteerAdminMessage(models.Model):
	sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="volunteer_admin_sent_messages")
	thread_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="volunteer_admin_thread_messages")
	reply_to = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="replies")
	message = models.TextField()
	is_read = models.BooleanField(default=False)
	is_edited = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["created_at"]
		indexes = [
			models.Index(fields=["thread_user", "-created_at"]),
			models.Index(fields=["sender", "-created_at"]),
		]

	def __str__(self):
		return f"volunteer-admin-message:{self.thread_user_id}:{self.sender_id}:{self.id}"


class VolunteerAdminMessageAttachment(models.Model):
	message = models.OneToOneField(VolunteerAdminMessage, on_delete=models.CASCADE, related_name="attachment")
	file = models.FileField(upload_to=volunteer_admin_attachment_upload_to)
	original_name = models.CharField(max_length=255)
	mime_type = models.CharField(max_length=120, blank=True)
	size_bytes = models.PositiveBigIntegerField(default=0)

	def save(self, *args, **kwargs):
		if self.file:
			self.original_name = self.original_name or os.path.basename(getattr(self.file, "name", ""))
			self.mime_type = str(getattr(self.file, "content_type", "") or "").lower()
			self.size_bytes = getattr(self.file, "size", 0) or 0
		if self.size_bytes > 5 * 1024 * 1024:
			raise ValidationError("Chat attachments must be 5 MB or smaller.")
		super().save(*args, **kwargs)


class InventoryItem(models.Model):
	CATEGORY_STORE_PRODUCT = "store_product"
	CATEGORY_RELIEF_GOODS = "relief_goods"
	CATEGORY_HYGIENE_KIT = "hygiene_kit"
	CATEGORY_SCHOOL_SUPPLIES = "school_supplies"
	CATEGORY_OTHER = "other"
	CATEGORY_CHOICES = (
		(CATEGORY_STORE_PRODUCT, "Store Product"),
		(CATEGORY_RELIEF_GOODS, "Relief Goods"),
		(CATEGORY_HYGIENE_KIT, "Hygiene Kit"),
		(CATEGORY_SCHOOL_SUPPLIES, "School Supplies"),
		(CATEGORY_OTHER, "Other"),
	)

	name = models.CharField(max_length=150)
	category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
	sub_category = models.CharField(max_length=150, blank=True, null=True)
	unit = models.CharField(max_length=50, default="pcs")
	stock = models.PositiveIntegerField(default=0)
	low_stock_threshold = models.PositiveIntegerField(default=10)
	price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
	description = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-created_at", "-id"]
		indexes = [
			models.Index(fields=["category", "-created_at"]),
			models.Index(fields=["-created_at"]),
		]

	@property
	def status(self):
		if self.stock == 0:
			return "out_of_stock"
		elif self.stock <= self.low_stock_threshold:
			return "low_stock"
		else:
			return "in_stock"

	def __str__(self):
		return f"inventory:{self.name}:{self.category}:{self.stock}"


class StockMovement(models.Model):
	ACTION_RESTOCK = "restock"
	ACTION_DEDUCT = "deduct"
	ACTION_CHOICES = (
		(ACTION_RESTOCK, "Restock"),
		(ACTION_DEDUCT, "Deduct"),
	)

	item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name="movements")
	action = models.CharField(max_length=20, choices=ACTION_CHOICES)
	quantity = models.PositiveIntegerField()
	reason = models.CharField(max_length=100, blank=True, null=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["-created_at"]
		indexes = [
			models.Index(fields=["item", "-created_at"]),
			models.Index(fields=["-created_at"]),
		]

	def __str__(self):
		return f"movement:{self.item.name}:{self.action}:{self.quantity}"