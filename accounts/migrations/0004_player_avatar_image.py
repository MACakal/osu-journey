from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_player_profile_image_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='player',
            name='avatar_image',
            field=models.ImageField(blank=True, null=True, upload_to='avatars/'),
        ),
    ]
