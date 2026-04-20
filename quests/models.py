from django.db import models
from accounts.models import Player
from gameplay.models import Play


class Quest(models.Model):

    QUEST_TYPES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('progression', 'Progression'),
    ]

    QUEST_CATEGORIES = [
        ('performance', 'Performance'),
        ('consistency', 'Consistency'),
        ('exploration', 'Exploration'),
        ('challenge', 'Challenge'),
    ]

    CONDITION_TYPES = [
        ('min_star_rating', 'Minimum Star Rating'),
        ('min_accuracy', 'Minimum Accuracy'),
        ('map_passed', 'Map Passed'),
        ('unique_mapper', 'Unique Mapper'),
        ('above_skill_baseline', 'Above Skill Baseline'),
        ('below_skill_baseline', 'Below Skill Baseline'),
        ('min_score', 'Minimum Score'),
        ('min_pp', 'Minimum PP'),
        ('beatmap_personal_best_pp', 'Beatmap Personal Best PP'),
        ('mod_includes', 'Mod Includes'),
        ('min_bpm', 'Minimum BPM'),
    ]

    OPERATORS = [
        ('gte', 'Greater than or equal'),
        ('lte', 'Less than or equal'),
        ('eq', 'Equal to'),
        ('gt', 'Greater than'),
        ('lt', 'Less than'),
    ]

    TIMEFRAMES = [
        ('daily', 'Today'),
        ('weekly', 'This week'),
        ('alltime', 'All time'),
    ]

    # identity
    name = models.CharField(max_length=255)
    description = models.TextField()

    # classification
    quest_type = models.CharField(max_length=20, choices=QUEST_TYPES)
    category = models.CharField(max_length=20, choices=QUEST_CATEGORIES)

    # condition
    condition_type = models.CharField(max_length=50, choices=CONDITION_TYPES)
    condition_value = models.CharField(max_length=100)
    condition_operator = models.CharField(max_length=10, choices=OPERATORS)

    # completion requirements
    required_count = models.PositiveIntegerField(default=1)
    timeframe = models.CharField(max_length=20, choices=TIMEFRAMES)

    # scaling
    scales_with_baseline = models.BooleanField(default=False)
    is_repeatable = models.BooleanField(default=False)

    # reward
    xp_reward = models.PositiveIntegerField()

    # visibility
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class QuestProgress(models.Model):

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('expired', 'Expired'),
        ('failed', 'Failed'),
    ]

    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='quest_progresses')
    quest = models.ForeignKey(Quest, on_delete=models.CASCADE, related_name='progresses')

    current_count = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    # archiving instead of deleting
    is_archived = models.BooleanField(default=False)

    # qualifying plays that counted toward this quest
    qualifying_plays = models.ManyToManyField(
        Play,
        through='QuestProgressPlay',
        related_name='quest_progresses'
    )

    assigned_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        # prevent duplicate active progress records for same player+quest
        constraints = [
            models.UniqueConstraint(
                fields=['player', 'quest'],
                condition=models.Q(is_archived=False),
                name='unique_active_quest_progress'
            )
        ]

    def __str__(self):
        return f"{self.player} - {self.quest} ({self.status})"


class QuestProgressPlay(models.Model):
    quest_progress = models.ForeignKey(QuestProgress, on_delete=models.CASCADE)
    play = models.ForeignKey(Play, on_delete=models.CASCADE)
    counted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['quest_progress', 'play']

    def __str__(self):
        return f"{self.quest_progress} - play {self.play.id}"