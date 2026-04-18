import random
from django.utils import timezone
from .models import Quest, QuestProgress
from gameplay.models import Play

MOD_OPTIONS = ['EZ', 'NF', 'HR', 'SD', 'PF', 'DT', 'HD', 'FL']

INVALID_COMBINATIONS = [
    frozenset({'EZ', 'HR'}),
    frozenset({'DT', 'HT'}),
    frozenset({'NC', 'HT'}),
    frozenset({'DT', 'NC'}),
    frozenset({'SD', 'PF'}),
    frozenset({'NF', 'SD'}),
    frozenset({'NF', 'PF'}),
]

MOD_MULTIPLIERS = {
    'EZ': 0.5,
    'NF': 1.0,
    'HR': 1.4,
    'SD': 1.0,
    'PF': 1.0,
    'DT': 1.5,
    'HD': 1.06,
    'FL': 1.12,
}


def _round_star(value):
    return round(value, 2)


def _normalize_baseline(baseline):
    return max(1.0, baseline or 1.0)


def _build_xp_reward(baseline, bonus=0):
    return max(25, int(round(40 + baseline * 10 + bonus)))


def _star_range(baseline, low_factor=0.8, high_factor=100.0):
    low = _round_star(baseline * low_factor)
    high = _round_star(max(low, baseline * high_factor))
    return low, high


def _get_mod_multiplier(mods):
    multiplier = 1.0
    for mod in mods:
        multiplier *= MOD_MULTIPLIERS.get(mod, 1.0)
    return multiplier


def _choose_mod():
    # Choose 1 or 2 mods randomly
    num_mods = random.choice([1, 2])
    selected = random.sample(MOD_OPTIONS, num_mods)
    selected_set = frozenset(selected)
    
    # Check if valid
    for invalid in INVALID_COMBINATIONS:
        if invalid.issubset(selected_set):
            # If invalid, try again (simple retry, could loop)
            return _choose_mod()
    
    return selected


def _best_near_baseline_play(player, min_star, max_star):
    return player.plays.filter(
        passed=True,
        adjusted_star_rating__gte=min_star,
        adjusted_star_rating__lte=max_star,
    ).order_by('-score').first()


def _format_star_range(min_star, max_star):
    return f"{min_star}★–{max_star}★" if min_star != max_star else f"{min_star}★"


def _accuracy_target(baseline):
    return min(99, max(93, int(round(92 + (baseline - 1.0) * 1.5))))


def _generate_pass_near_baseline(player):
    baseline = _normalize_baseline(player.skill_baseline)
    min_star = _round_star(baseline * 0.875)

    return {
        'name': f'Pass any map with star rating {min_star}★ or higher',
        'description': (
            f'Pass any beatmap with adjusted star rating {min_star}★ or higher.'
        ),
        'quest_type': 'progression',
        'category': 'consistency',
        'condition_type': 'min_star_rating',
        'condition_value': str(min_star),
        'condition_operator': 'gte',
        'required_count': 1,
        'timeframe': 'alltime',
        'scales_with_baseline': True,
        'is_repeatable': False,
        'xp_reward': _build_xp_reward(baseline),
        'is_active': True,
    }


def _generate_accuracy_quest(player):
    baseline = _normalize_baseline(player.skill_baseline)
    min_star = _round_star(baseline * 0.875)
    accuracy_target = 99

    return {
        'name': f'Get {accuracy_target}% on a {min_star}★ or higher map',
        'description': (
            f'Finish a map with adjusted star rating {min_star}★ or higher '
            f'and at least {accuracy_target}% accuracy.'
        ),
        'quest_type': 'progression',
        'category': 'performance',
        'condition_type': 'min_accuracy',
        'condition_value': str(accuracy_target),
        'condition_operator': 'gte',
        'required_count': 1,
        'timeframe': 'alltime',
        'scales_with_baseline': True,
        'is_repeatable': False,
        'xp_reward': _build_xp_reward(baseline, bonus=10),
        'is_active': True,
    }


def _generate_personal_best_quest(player):
    baseline = _normalize_baseline(player.skill_baseline)
    min_star = _round_star(baseline * 0.875)
    best_play = _best_near_baseline_play(player, min_star, 100.0)  # since no upper limit

    if best_play:
        target = best_play.score + 1
        name = f'Beat your best score on a {min_star}★ or higher map'
        description = (
            f'Improve your score on a map with {min_star}★ or higher and set a new personal best.'
        )
    else:
        target = min_star
        name = f'Pass any map with star rating {min_star}★ or higher'
        description = (
            f'Pass any map with adjusted star rating {min_star}★ or higher. '
            f'This helps create a better score for future quests.'
        )

    return {
        'name': name,
        'description': description,
        'quest_type': 'progression',
        'category': 'challenge',
        'condition_type': 'min_score' if best_play else 'min_star_rating',
        'condition_value': str(target),
        'condition_operator': 'gt' if best_play else 'gte',
        'required_count': 1,
        'timeframe': 'alltime',
        'scales_with_baseline': True,
        'is_repeatable': False,
        'xp_reward': _build_xp_reward(baseline, bonus=20),
        'is_active': True,
    }


def _generate_mod_style_quest(player):
    baseline = _normalize_baseline(player.skill_baseline)
    chosen_mods = _choose_mod()
    mod_str = '+'.join(chosen_mods) if len(chosen_mods) > 1 else chosen_mods[0]
    min_star = _round_star(baseline * 0.875)
    
    return {
        'name': f'Pass a {min_star}★ {mod_str} map',
        'description': (
            f'Pass a map with adjusted star rating {min_star}★ or higher while using {mod_str}. '
            f'This promotes different play styles without pushing difficulty above your baseline.'
        ),
        'quest_type': 'progression',
        'category': 'exploration',
        'condition_type': 'mod_includes',
        'condition_value': ','.join(sorted(chosen_mods)),
        'condition_operator': 'eq',
        'required_count': 1,
        'timeframe': 'alltime',
        'scales_with_baseline': True,
        'is_repeatable': False,
        'xp_reward': _build_xp_reward(baseline, bonus=15),
        'is_active': True,
    }


def generate_baseline_quest_templates(player):
    generators = [
        _generate_pass_near_baseline,
        _generate_accuracy_quest,
        _generate_personal_best_quest,
        _generate_mod_style_quest,
    ]
    random.shuffle(generators)
    return [generator(player) for generator in generators]


def ensure_player_quests(player):
    active_progress = player.quest_progresses.filter(is_archived=False, status='active').select_related('quest')
    if active_progress.exists():
        return active_progress

    templates = generate_baseline_quest_templates(player)
    progress_records = []

    for template in templates:
        quest, _ = Quest.objects.get_or_create(
            name=template['name'],
            defaults=template,
        )
        progress_records.append(
            QuestProgress.objects.create(
                player=player,
                quest=quest,
                current_count=0,
                status='active',
                expires_at=None,
            )
        )

    return progress_records


def check_quest_completion(play):
    player = play.player
    active_progresses = player.quest_progresses.filter(is_archived=False, status='active').select_related('quest')

    for progress in active_progresses:
        quest = progress.quest
        condition_type = quest.condition_type
        condition_value = quest.condition_value
        condition_operator = quest.condition_operator

        if condition_type == 'min_star_rating':
            value = play.adjusted_star_rating
        elif condition_type == 'min_accuracy':
            value = play.accuracy
        elif condition_type == 'min_score':
            value = play.score
        elif condition_type == 'mod_includes':
            # For mod quests, check if all required mods are in play.mods
            required_mods = set(condition_value.split(','))
            play_mods = set(play.mods)
            if required_mods.issubset(play_mods):
                value = 1  # arbitrary, since it's presence
            else:
                continue  # not satisfied
        else:
            continue  # unknown condition

        # Check if condition is met
        if condition_operator == 'gte' and value >= float(condition_value):
            progress.current_count += 1
            if progress.current_count >= quest.required_count:
                progress.status = 'completed'
                progress.completed_at = timezone.now()
                # Award XP
                from progression.services import award_xp
                award_xp(player, play, quest.xp_reward, False, 'quest', quest.id)
                progress.is_archived = True
            progress.save()
        elif condition_operator == 'gt' and value > float(condition_value):
            # Similar for gt
            progress.current_count += 1
            if progress.current_count >= quest.required_count:
                progress.status = 'completed'
                progress.completed_at = timezone.now()
                from progression.services import award_xp
                award_xp(player, play, quest.xp_reward, False, 'quest', quest.id)
                progress.is_archived = True
            progress.save()
