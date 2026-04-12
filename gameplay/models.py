from django.db import models
from accounts.models import Player


class Beatmap(models.Model):
    # osu! identity
    beatmap_id = models.IntegerField(unique=True)
    beatmapset_id = models.IntegerField()

    # song info
    title = models.CharField(max_length=255)
    artist = models.CharField(max_length=255)
    mapper = models.CharField(max_length=255)

    # difficulty info
    star_rating = models.FloatField()
    bpm = models.FloatField()
    length_seconds = models.IntegerField()
    ar = models.FloatField()  # approach rate
    od = models.FloatField()  # overall difficulty
    cs = models.FloatField()  # circle size

    # timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.artist} - {self.title} [{self.star_rating}★]"


class Play(models.Model):
    # osu! identity
    osu_score_id = models.BigIntegerField(unique=True)

    # relations
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='plays')
    beatmap = models.ForeignKey(Beatmap, on_delete=models.CASCADE, related_name='plays')

    # performance
    accuracy = models.FloatField()
    score = models.BigIntegerField()
    max_combo = models.IntegerField()
    passed = models.BooleanField()

    # mods stored as a list of strings e.g. ["HD", "DT"]
    mods = models.JSONField(default=list)

    # star rating adjusted for mods (osu! API provides this)
    adjusted_star_rating = models.FloatField()

    # timestamps
    played_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.player} on {self.beatmap} ({self.accuracy:.2f}%)"