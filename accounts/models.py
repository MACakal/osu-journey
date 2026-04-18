from django.db import models
from django.contrib.auth.models import User


class Player(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='player')
    
    # osu! identity
    osu_id = models.IntegerField(unique=True)
    osu_username = models.CharField(max_length=255)
    profile_image_url = models.URLField(max_length=500, null=True, blank=True)
    avatar_image = models.ImageField(upload_to='avatars/', null=True, blank=True)
    
    # OAuth tokens
    access_token = models.TextField()
    refresh_token = models.TextField()
    token_expires_at = models.DateTimeField()
    
    # osu!journey progression
    xp = models.PositiveIntegerField(default=0)
    level = models.PositiveIntegerField(default=1)
    
    # skill baseline (average star rating of top plays, recalculated periodically)
    skill_baseline = models.FloatField(default=0.0)
    
    # active build (nullable, set after player creates one)
    active_build = models.ForeignKey(
        'builds.Build',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='active_for_players'
    )
    
    # timestamps
    joined_at = models.DateTimeField(auto_now_add=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)

    @property
    def avatar_url(self):
        if self.avatar_image:
            return self.avatar_image.url
        if self.profile_image_url:
            return self.profile_image_url
        return 'https://osu.ppy.sh/images/layout/avatar-guest.png'

    def __str__(self):
        return self.osu_username