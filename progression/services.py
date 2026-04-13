from django.utils import timezone
from .models import XPLog

BASE_MULTIPLIER = 75

XP_BASE = 100
XP_EXPONENT = 2.5
MAX_LEVEL = 500


def calculate_accuracy_multiplier(accuracy):
    if accuracy >= 85:
        return 0.5 + (accuracy - 85) / 30
    else:
        return ((accuracy / 85) ** 3) * 0.5


def calculate_difficulty_multiplier(adjusted_star_rating, skill_baseline):
    if skill_baseline <= 0:
        ratio = adjusted_star_rating / 4.0
    else:
        ratio = adjusted_star_rating / skill_baseline

    multiplier = ratio ** 2
    multiplier = max(multiplier, 0.05)
    multiplier = min(multiplier, 1.5)
    return multiplier


def calculate_repeat_multiplier(player, beatmap, current_accuracy):
    from gameplay.models import Play
    from datetime import timedelta

    previous_plays = Play.objects.filter(
        player=player,
        beatmap=beatmap,
        passed=True,
    ).order_by('-accuracy')

    if not previous_plays.exists():
        return 1.0, True

    best_accuracy = previous_plays.first().accuracy

    recent_cutoff = timezone.now() - timedelta(hours=2)
    recent_plays_count = Play.objects.filter(
        player=player,
        beatmap=beatmap,
        played_at__gte=recent_cutoff,
    ).count()

    if recent_plays_count >= 3:
        return 0.1, False

    is_personal_best = current_accuracy > best_accuracy + 1.0

    if is_personal_best:
        return 0.85, True

    return 0.4, False


def calculate_base_xp(play, skill_baseline):
    accuracy_mult = calculate_accuracy_multiplier(play.accuracy)
    difficulty_mult = calculate_difficulty_multiplier(play.adjusted_star_rating, skill_baseline)
    repeat_mult, is_personal_best = calculate_repeat_multiplier(
        play.player,
        play.beatmap,
        play.accuracy,
    )

    xp = BASE_MULTIPLIER * accuracy_mult * difficulty_mult * repeat_mult

    if not play.passed:
        xp *= 0.25

    xp = max(1, round(xp))

    return xp, is_personal_best


def xp_for_level(level):
    if level <= 1:
        return 0
    return round(XP_BASE * (level ** XP_EXPONENT))

def get_level_for_xp(xp):
    level = 1
    while level < MAX_LEVEL:
        if xp >= xp_for_level(level + 1):
            level += 1
        else:
            break
    return level



def get_next_level_threshold(current_level):
    if current_level >= MAX_LEVEL:
        return None
    return xp_for_level(current_level + 1)


def get_level_progress(player):
    current_threshold = xp_for_level(player.level)
    next_threshold = get_next_level_threshold(player.level)
    if next_threshold is None:
        return 100
    xp_into_level = player.xp - current_threshold
    xp_needed = next_threshold - current_threshold
    return round((xp_into_level / xp_needed) * 100)

def award_xp(player, play, base_xp, is_personal_best):
    modifier_breakdown = []
    final_xp = base_xp

    XPLog.objects.create(
        player=player,
        active_build=player.active_build,
        base_xp=base_xp,
        final_xp=final_xp,
        source_type='play',
        source_id=play.id,
        modifier_breakdown=modifier_breakdown,
    )

    player.xp += final_xp
    new_level = get_level_for_xp(player.xp)

    leveled_up = new_level > player.level
    player.level = new_level
    player.save(update_fields=['xp', 'level'])

    return final_xp, leveled_up