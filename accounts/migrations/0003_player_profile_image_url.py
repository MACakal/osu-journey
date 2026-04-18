from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='player',
            name='profile_image_url',
            field=models.URLField(blank=True, max_length=500, null=True),
        ),
    ]
