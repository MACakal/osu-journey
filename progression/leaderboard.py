from gameplay.models import Play
from accounts.models import Player

INVALID_COMBINATIONS = [
    frozenset({'EZ', 'HR'}),
    frozenset({'DT', 'HT'}),
    frozenset({'NC', 'HT'}),
    frozenset({'DT', 'NC'}),
    frozenset({'SD', 'PF'}),
    frozenset({'NF', 'SD'}),
    frozenset({'NF', 'PF'}),
]


# ----------------------------
# MOD PARSING (FIXED CORE ISSUE)
# ----------------------------
def parse_mods(value):
    """
    Normalizes mods from BOTH:
    - DB strings ("HD,HR,DT")
    - API lists (["HD", "HR"])
    """
    if not value:
        return frozenset()

    if isinstance(value, str):
        mods = [m.strip().upper() for m in value.split(",") if m.strip()]
    else:
        mods = [str(m).strip().upper() for m in value if str(m).strip()]

    # normalize NC → DT
    mods = ["DT" if m == "NC" else m for m in mods]

    return frozenset(mods)


def normalize_mods(mods):
    return ["DT" if mod == "NC" else mod for mod in mods]


def is_valid_mod_combination(mods):
    mods = normalize_mods(mods)
    mod_set = frozenset(mods)

    for invalid in INVALID_COMBINATIONS:
        if invalid.issubset(mod_set):
            return False

    return True


def get_mod_leaderboard(mod_combination):
    if not is_valid_mod_combination(mod_combination):
        return None, "Invalid mod combination"

    target_mods = parse_mods(mod_combination)

    results = []

    for player in Player.objects.all():
        plays = Play.objects.filter(
            player=player,
            passed=True,
            pp__isnull=False,
            pp__gt=0,
        ).select_related("beatmap")

        filtered_plays = []

        for p in plays:
            play_mods = parse_mods(p.mods)

            if play_mods == target_mods:
                filtered_plays.append(p)

        if not filtered_plays:
            continue

        # best per map
        best_per_map = {}
        for p in filtered_plays:
            key = p.beatmap_id
            if key not in best_per_map or p.pp > best_per_map[key].pp:
                best_per_map[key] = p

        sorted_plays = sorted(
            best_per_map.values(),
            key=lambda p: p.pp,
            reverse=True
        )[:100]

        weighted_pp = round(
            sum(p.pp * (0.95 ** i) for i, p in enumerate(sorted_plays)),
            2
        )

        if weighted_pp > 0:
            results.append({
                "player": player,
                "weighted_pp": weighted_pp,
                "play_count": len(filtered_plays),
            })

    results.sort(key=lambda x: x["weighted_pp"], reverse=True)

    return results, None