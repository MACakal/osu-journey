from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.views.decorators.cache import never_cache
from accounts import services as osu_services
from gameplay.services import sync_recent_plays, sync_top_plays, update_skill_baseline
from progression.services import get_next_level_threshold, get_level_progress
from progression.leaderboard import get_mod_leaderboard
from accounts.services import get_valid_token
from quests.services import ensure_player_quests
from quests.services import ensure_player_quests

@never_cache
@login_required(login_url='/auth/login/')
def dashboard(request):
    try:
        player = request.user.player
    except Exception:
        return redirect('/auth/logout/')

    try:
        # sync recent plays
        token = get_valid_token(player)
        recent_data = osu_services.get_recent_plays(token, player.osu_id)
        sync_recent_plays(player, recent_data)

        # sync top plays for skill baseline
        top_data = osu_services.get_top_plays(token, player.osu_id)
        sync_top_plays(player, top_data)

        # recalculate skill baseline from top plays
        update_skill_baseline(player)

    except Exception as e:
        print(f"Sync error: {e}")

    next_level_xp = get_next_level_threshold(player.level)
    xp_progress = player.xp - 0 if player.level == 1 else player.xp
    context = {
        'player': player,
        'recent_plays': player.plays.order_by('-played_at')[:10],
        'next_level_xp': get_next_level_threshold(player.level),
        'level_progress': get_level_progress(player),
    }
    return render(request, 'dashboard/dashboard.html', context)

def leaderboard(request):
    mods = request.GET.getlist('mods')
    results = None
    error = None

    if mods:
        results, error = get_mod_leaderboard(mods)

    context = {
        'results': results,
        'error': error,
        'selected_mods': mods,
        'available_mods': ['EZ', 'NF', 'HT', 'HR', 'SD', 'PF', 'DT', 'HD', 'FL'],
    }
    return render(request, 'dashboard/leaderboard.html', context)

@never_cache
@login_required(login_url='/auth/login/')
def top_plays(request):
    try:
        player = request.user.player
    except Exception:
        return redirect('/auth/logout/')

    from progression.leaderboard import normalize_mods, is_valid_mod_combination

    selected_mods = request.GET.getlist('mods')
    error = None

    plays = list(
        player.plays.filter(
            passed=True,
            pp__isnull=False,
            pp__gt=0,
        )
    )

    if selected_mods:
        if not is_valid_mod_combination(selected_mods):
            error = 'Invalid mod combination'
            plays = []
        else:
            normalized_selected = set(normalize_mods(selected_mods))
            filtered_plays = []

            for p in plays:
                play_mods = set(normalize_mods(p.mods))

                # Treat NC as DT for matching
                if 'DT' in normalized_selected and 'NC' in play_mods:
                    play_mods.discard('NC')
                    play_mods.add('DT')

                # Exact match only: no extra mods allowed
                if play_mods == normalized_selected:
                    filtered_plays.append(p)

            plays = filtered_plays

    best_per_map = {}
    for p in plays:
        if p.beatmap_id not in best_per_map or p.pp > best_per_map[p.beatmap_id].pp:
            best_per_map[p.beatmap_id] = p

    plays = sorted(best_per_map.values(), key=lambda p: p.pp, reverse=True)[:100]

    context = {
        'player': player,
        'plays': plays,
        'selected_mods': selected_mods,
        'available_mods': ['EZ', 'NF', 'HT', 'HR', 'SD', 'PF', 'DT', 'HD', 'FI', 'FL'],
        'error': error,
    }
    return render(request, 'dashboard/top_plays.html', context)


@never_cache
@login_required(login_url='/auth/login/')
def quests(request):
    try:
        player = request.user.player
    except Exception:
        return redirect('/auth/logout/')

    active_quests = ensure_player_quests(player)
    return render(request, 'dashboard/quests.html', {
        'player': player,
        'active_quests': active_quests,
    })


def home(request):
    if request.user.is_authenticated:
        return redirect('/dashboard/')
    return render(request, 'dashboard/home.html')