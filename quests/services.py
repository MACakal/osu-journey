import random
from django.utils import timezone
from .models import Quest, QuestProgress

# PF and FL removed: PF is too punishing (no miss + no 100s), FL requires dedicated training
MOD_OPTIONS_BASE = ['EZ', 'NF', 'HR', 'HD']
MOD_OPTIONS_ADVANCED = ['EZ', 'NF', 'HR', 'SD', 'DT', 'HD']

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



def _choose_mod(baseline=1.0):
    pool = MOD_OPTIONS_ADVANCED if baseline >= 3.0 else MOD_OPTIONS_BASE
    num_mods = random.choice([1, 2])
    if num_mods > len(pool):
        num_mods = 1
    selected = random.sample(pool, num_mods)
    selected_set = frozenset(selected)

    for invalid in INVALID_COMBINATIONS:
        if invalid.issubset(selected_set):
            return _choose_mod(baseline)

    return selected


def _best_near_baseline_play(player, min_star, max_star):
    return player.plays.filter(
        passed=True,
        adjusted_star_rating__gte=min_star,
        adjusted_star_rating__lte=max_star,
    ).order_by('-score').first()



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
    accuracy_target = _accuracy_target(baseline)

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
        name = f'Beat your best PP on a {min_star}★+ map you\'ve already played'
        description = (
            f'On any beatmap with adjusted star rating {min_star}★ or higher that you\'ve played before, '
            f'set a new personal best PP score on that same map.'
        )
        condition_type = 'beatmap_personal_best_pp'
        condition_value = str(min_star)
        condition_operator = 'gt'
    else:
        name = f'Pass any map with star rating {min_star}★ or higher'
        description = (
            f'Pass any beatmap with adjusted star rating {min_star}★ or higher. '
            f'This helps create a better score for future quests.'
        )
        condition_type = 'min_star_rating'
        condition_value = str(min_star)
        condition_operator = 'gte'

    return {
        'name': name,
        'description': description,
        'quest_type': 'progression',
        'category': 'challenge',
        'condition_type': condition_type,
        'condition_value': condition_value,
        'condition_operator': condition_operator,
        'required_count': 1,
        'timeframe': 'alltime',
        'scales_with_baseline': True,
        'is_repeatable': False,
        'xp_reward': _build_xp_reward(baseline, bonus=20),
        'is_active': True,
    }


def _generate_mod_style_quest(player):
    baseline = _normalize_baseline(player.skill_baseline)
    chosen_mods = _choose_mod(baseline)
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
        'condition_value': f"{','.join(sorted(chosen_mods))}|{min_star}",
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

    if progress_records:
        for play in player.plays.filter(passed=True).order_by('played_at'):
            check_quest_completion(play)

    return player.quest_progresses.filter(is_archived=False, status='active').select_related('quest')


def check_quest_completion(play):
    player = play.player
    active_progresses = player.quest_progresses.filter(is_archived=False, status='active').select_related('quest')

    for progress in active_progresses:
        quest = progress.quest
        condition_type = quest.condition_type
        condition_value = quest.condition_value
        condition_operator = quest.condition_operator

        # Most quest progress should only count passed plays.
        if not play.passed:
            continue

        if condition_type == 'min_star_rating':
            value = play.adjusted_star_rating
        elif condition_type == 'min_accuracy':
            value = play.accuracy
        elif condition_type == 'min_score':
            value = play.score
        elif condition_type == 'min_pp':
            value = play.pp or 0
        elif condition_type == 'beatmap_personal_best_pp':
            min_star = float(condition_value)
            if play.adjusted_star_rating < min_star or play.pp is None:
                continue

            best_previous_play = player.plays.filter(
                beatmap=play.beatmap,
                pp__isnull=False,
            ).exclude(pk=play.pk).order_by('-pp').first()

            if not best_previous_play or play.pp <= best_previous_play.pp:
                continue

            progress.current_count += 1
            if progress.current_count >= quest.required_count:
                progress.status = 'completed'
                progress.completed_at = timezone.now()
                from progression.services import award_xp
                award_xp(player, play, quest.xp_reward, False, 'quest', quest.id)
                progress.is_archived = True
            progress.save()
            continue
        elif condition_type == 'mod_includes':
            # condition_value format: "MOD1,MOD2|min_star" or legacy "MOD1,MOD2"
            if '|' in condition_value:
                mods_part, min_star_part = condition_value.split('|', 1)
                if play.adjusted_star_rating < float(min_star_part):
                    continue
            else:
                mods_part = condition_value
            required_mods = set(mods_part.split(','))
            play_mods = set(play.mods)
            if not required_mods.issubset(play_mods):
                continue
            progress.current_count += 1
            if progress.current_count >= quest.required_count:
                progress.status = 'completed'
                progress.completed_at = timezone.now()
                from progression.services import award_xp
                award_xp(player, play, quest.xp_reward, False, 'quest', quest.id)
                progress.is_archived = True
            progress.save()
            continue
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
