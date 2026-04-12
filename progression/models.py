from django.db import models
from accounts.models import Player
from gameplay.models import Play
from quests.models import Quest


class Region(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    lore_text = models.TextField()

    # sequence order
    order = models.PositiveIntegerField(unique=True)

    # skill focus for context, not enforcement
    skill_focus = models.CharField(max_length=100)

    # soft entry gate
    minimum_level = models.PositiveIntegerField(default=1)

    is_final = models.BooleanField(default=False)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.order}. {self.name}"


class RegionQuest(models.Model):
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name='region_quests')
    quest = models.ForeignKey(Quest, on_delete=models.CASCADE, related_name='region_quests')

    is_required = models.BooleanField(default=True)

    # sequence within the region
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ['order']
        unique_together = ['region', 'quest']

    def __str__(self):
        return f"{self.region.name} - {self.quest.name} (required: {self.is_required})"


class PlayerRegion(models.Model):

    STATUS_CHOICES = [
        ('locked', 'Locked'),
        ('active', 'Active'),
        ('completed', 'Completed'),
    ]

    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='player_regions')
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name='player_regions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='locked')

    entered_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['player', 'region']

    def __str__(self):
        return f"{self.player} - {self.region.name} ({self.status})"


class BossChallenge(models.Model):
    region = models.OneToOneField(Region, on_delete=models.CASCADE, related_name='boss_challenge')

    name = models.CharField(max_length=255)
    description = models.TextField()
    lore_text = models.TextField()

    xp_reward = models.PositiveIntegerField()

    # null means unlimited attempts
    attempts_allowed = models.PositiveIntegerField(null=True, blank=True)

    scales_with_baseline = models.BooleanField(default=True)

    def __str__(self):
        return f"Boss: {self.name} ({self.region.name})"


class BossChallengeCondition(models.Model):

    CONDITION_TYPES = [
        ('min_star_rating', 'Minimum Star Rating'),
        ('min_accuracy', 'Minimum Accuracy'),
        ('map_passed', 'Map Passed'),
        ('above_skill_baseline', 'Above Skill Baseline'),
        ('min_score', 'Minimum Score'),
        ('mod_includes', 'Mod Includes'),
        ('min_combo', 'Minimum Combo'),
    ]

    OPERATORS = [
        ('gte', 'Greater than or equal'),
        ('lte', 'Less than or equal'),
        ('eq', 'Equal to'),
        ('gt', 'Greater than'),
        ('lt', 'Less than'),
    ]

    boss_challenge = models.ForeignKey(
        BossChallenge,
        on_delete=models.CASCADE,
        related_name='conditions'
    )

    condition_type = models.CharField(max_length=50, choices=CONDITION_TYPES)
    condition_value = models.CharField(max_length=100)
    condition_operator = models.CharField(max_length=10, choices=OPERATORS)

    # all conditions must be met on the same play
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.boss_challenge.name} - {self.condition_type} {self.condition_operator} {self.condition_value}"


class PlayerBossChallenge(models.Model):

    STATUS_CHOICES = [
        ('locked', 'Locked'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='boss_challenges')
    boss_challenge = models.ForeignKey(BossChallenge, on_delete=models.CASCADE, related_name='player_attempts')

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='locked')
    attempt_count = models.PositiveIntegerField(default=0)

    # the play that completed the boss, null until completed
    completion_play = models.ForeignKey(
        Play,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='boss_completions'
    )

    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['player', 'boss_challenge']

    def __str__(self):
        return f"{self.player} - {self.boss_challenge.name} ({self.status})"


class XPLog(models.Model):

    SOURCE_TYPES = [
        ('play', 'Play'),
        ('quest', 'Quest'),
        ('boss', 'Boss Challenge'),
    ]

    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='xp_logs')
    active_build = models.ForeignKey(
        'builds.Build',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='xp_logs'
    )

    # how much XP was awarded
    base_xp = models.PositiveIntegerField()
    final_xp = models.PositiveIntegerField()

    # what triggered this XP gain
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES)
    source_id = models.PositiveIntegerField()

    # full breakdown of modifiers applied, stored as JSON
    # e.g. [{"modifier": "min_bpm", "multiplier": 1.3}, {"modifier": "mod_includes", "multiplier": 1.18}]
    modifier_breakdown = models.JSONField(default=list)

    earned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-earned_at']

    def __str__(self):
        return f"{self.player} +{self.final_xp} XP ({self.source_type}:{self.source_id})"