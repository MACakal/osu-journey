from gameplay.models import Play
from accounts.models import Player

INVALID_COMBINATIONS = [
    frozenset({'EZ', 'HR'}),
    frozenset({'DT', 'HT'}),
    frozenset({'NC', 'HT'}),
    frozenset({'DT', 'NC'}),
]

def normalize_mods(mods):
    return ['DT' if mod == 'NC' else mod for mod in mods]


def is_valid_mod_combination(mods):
    mods = normalize_mods(mods)
    mod_set = frozenset(mods)
    for invalid in INVALID_COMBINATIONS:
        if invalid.issubset(mod_set):
            return False
    return True

def calculate_weighted_pp(plays):
    sorted_plays = plays.filter(pp__isnull=False).order_by('-pp')
    weighted_pp = sum(
        play.pp * (0.95 ** i)
        for i, play in enumerate(sorted_plays)
    )
    return round(weighted_pp, 2)

def get_mod_leaderboard(mod_combination):
    if not is_valid_mod_combination(mod_combination):
        return None, 'Invalid mod combination'

    normalized = normalize_mods(mod_combination)

    results = []
    for player in Player.objects.all():
        plays = Play.objects.filter(
            player=player,
            passed=True,
            pp__isnull=False,
        )

        # filter in Python since SQLite doesn't support JSONField contains
        if 'DT' in normalized:
            plays = [p for p in plays if 'DT' in p.mods or 'NC' in p.mods]
        else:
            plays = list(plays)

        for mod in normalized:
            if mod != 'DT':
                plays = [p for p in plays if mod in p.mods]

        if not plays:
            continue

        sorted_plays = sorted(plays, key=lambda p: p.pp or 0, reverse=True)
        weighted_pp = round(sum(
            p.pp * (0.95 ** i)
            for i, p in enumerate(sorted_plays)
            if p.pp
        ), 2)

        if weighted_pp > 0:
            results.append({
                'player': player,
                'weighted_pp': weighted_pp,
                'play_count': len(plays),
            })

    results = sorted(results, key=lambda x: x['weighted_pp'], reverse=True)
    return results, None