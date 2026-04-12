from django.db import models
from accounts.models import Player


class Build(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='builds')
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.player} - {self.name}"


class BuildModifier(models.Model):

    MODIFIER_TYPES = [
        ('min_bpm', 'Minimum BPM'),
        ('max_ar', 'Maximum AR'),
        ('min_ar', 'Minimum AR'),
        ('min_accuracy', 'Minimum Accuracy'),
        ('mod_includes', 'Mod Includes'),
        ('min_star_rating', 'Minimum Star Rating'),
        ('max_star_rating', 'Maximum Star Rating'),
    ]

    build = models.ForeignKey(Build, on_delete=models.CASCADE, related_name='modifiers')
    modifier_type = models.CharField(max_length=50, choices=MODIFIER_TYPES)

    # threshold value — interpreted differently per modifier_type
    # e.g. min_bpm: 240.0 | mod_includes: stored as string "DT"
    modifier_value = models.CharField(max_length=100)

    bonus_multiplier = models.FloatField()

    # order determines diminishing returns calculation
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.build.name} - {self.modifier_type} ({self.bonus_multiplier}x)"