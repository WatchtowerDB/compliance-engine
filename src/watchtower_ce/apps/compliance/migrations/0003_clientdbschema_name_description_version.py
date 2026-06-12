from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("compliance", "0002_seed_compliance_frameworks"),
    ]

    operations = [
        migrations.AddField(
            model_name="clientdbschema",
            name="name",
            field=models.CharField(default="", max_length=200),
        ),
        migrations.AddField(
            model_name="clientdbschema",
            name="description",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="clientdbschema",
            name="internal_version",
            field=models.PositiveIntegerField(default=1),
        ),
    ]
