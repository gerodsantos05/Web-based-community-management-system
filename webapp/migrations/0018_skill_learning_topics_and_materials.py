from django.db import migrations, models
import django.db.models.deletion
import webapp.models


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
                "material_type": "document",
                "external_url": "https://drive.google.com/file/d/1ZUATmwz5XSHJabA0qnFPbn6tIIeB6WUm/preview?usp=embed",
            },
            {
                "title": "Water Smart Routines",
                "description": "Set up a simple watering plan that saves time and water.",
                "material_type": "video",
                "external_url": "https://drive.google.com/file/d/1lhoyxiTt25SScLMfJUZOmGZFkpdalsWr/preview?usp=embed",
            },
            {
                "title": "Planting Calendar Guide",
                "description": "Filipino seasonal planting guide for year-round harvests.",
                "material_type": "reference_guide",
                "external_url": "https://example.com/planting-calendar-guide",
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
                "material_type": "document",
                "external_url": "https://example.com/material-selection.pdf",
            },
            {
                "title": "Cutting and Layering",
                "description": "Practice the first shaping steps for a finished product.",
                "material_type": "video",
                "external_url": "https://example.com/cutting-and-layering.mp4",
            },
            {
                "title": "Weaving Patterns Guide",
                "description": "Traditional Philippine weaving patterns for ragmaking.",
                "material_type": "reference_guide",
                "external_url": "https://example.com/weaving-patterns",
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
                "material_type": "document",
                "external_url": "https://example.com/starter-planning.pdf",
            },
            {
                "title": "Budget Basics",
                "description": "Estimate low-risk costs for first runs.",
                "material_type": "reference_guide",
                "external_url": "https://example.com/budget-basics",
            },
            {
                "title": "Pricing Your Products",
                "description": "Calculate fair prices that cover costs and generate profit.",
                "material_type": "video",
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
                "material_type": "reference_guide",
                "external_url": "https://example.com/letter-sounds",
            },
            {
                "title": "Story Time Session",
                "description": "Read along with a short story and prompts.",
                "material_type": "video",
                "external_url": "https://example.com/story-time.mp4",
            },
            {
                "title": "Practice Sheets",
                "description": "Printable sheets for at-home practice.",
                "material_type": "document",
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
                "material_type": "document",
                "external_url": "https://example.com/counting-daily-life.pdf",
            },
            {
                "title": "Money Skills Workshop",
                "description": "Count and manage money in real-world situations.",
                "material_type": "video",
                "external_url": "https://example.com/money-skills.mp4",
            },
            {
                "title": "Number Practice Cards",
                "description": "Printable cards for quick drills.",
                "material_type": "reference_guide",
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
                "material_type": "reference_guide",
                "external_url": "https://example.com/story-seeds",
            },
            {
                "title": "Drawing Techniques",
                "description": "Learn basic shapes and shading methods.",
                "material_type": "video",
                "external_url": "https://example.com/drawing-techniques.mp4",
            },
            {
                "title": "Creative Journal",
                "description": "A template for weekly creative moments.",
                "material_type": "document",
                "external_url": "https://example.com/creative-journal.pdf",
            },
        ],
    },
]


def seed_skill_learning_content(apps, schema_editor):
    SkillLearningTopic = apps.get_model("webapp", "SkillLearningTopic")
    SkillLearningMaterial = apps.get_model("webapp", "SkillLearningMaterial")

    if SkillLearningTopic.objects.exists():
        return

    for topic_data in SKILL_LEARNING_DEFAULT_TOPICS:
        materials_data = topic_data["materials"]
        topic_fields = {key: value for key, value in topic_data.items() if key != "materials"}
        topic = SkillLearningTopic.objects.create(**topic_fields)
        for material_data in materials_data:
            SkillLearningMaterial.objects.create(topic=topic, **material_data)


class Migration(migrations.Migration):

    dependencies = [
        ("webapp", "0017_alter_roleapplication_status"),
    ]

    operations = [
        migrations.CreateModel(
            name="SkillLearningTopic",
            fields=[
                ("id", models.UUIDField(default=webapp.models.uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField()),
                ("badge_label", models.CharField(max_length=120)),
                ("filter_tags", models.JSONField(blank=True, default=list)),
                ("cover_image", models.ImageField(blank=True, null=True, upload_to=webapp.models.skill_learning_topic_cover_upload_to)),
                ("cover_image_url", models.URLField(blank=True)),
                ("is_recommended", models.BooleanField(default=False)),
                ("popularity_score", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["-is_recommended", "-popularity_score", "-created_at", "-id"],
            },
        ),
        migrations.CreateModel(
            name="SkillLearningMaterial",
            fields=[
                ("id", models.UUIDField(default=webapp.models.uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("material_type", models.CharField(choices=[("document", "Document"), ("video", "Video"), ("reference_guide", "Reference Guide")], max_length=30)),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("file_upload", models.FileField(blank=True, null=True, upload_to=webapp.models.skill_learning_material_upload_to)),
                ("external_url", models.URLField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("topic", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="materials", to="webapp.skilllearningtopic")),
            ],
            options={
                "ordering": ["created_at", "id"],
            },
        ),
        migrations.RunPython(seed_skill_learning_content, migrations.RunPython.noop),
    ]
