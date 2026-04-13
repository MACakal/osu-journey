from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.views.decorators.cache import never_cache
from accounts import services as osu_services
from gameplay.services import sync_recent_plays, sync_top_plays, update_skill_baseline
from progression.services import get_next_level_threshold, get_level_progress
from progression.leaderboard import get_mod_leaderboard

@never_cache
@login_required(login_url='/auth/login/')
def dashboard(request):
    try:
        player = request.user.player
    except Exception:
        return redirect('/auth/logout/')

    try:
        # sync recent plays
        recent_data = osu_services.get_recent_plays(
            player.access_token,
            player.osu_id
        )
        sync_recent_plays(player, recent_data)

        # sync top plays for skill baseline
        top_data = osu_services.get_top_plays(
            player.access_token,
            player.osu_id
        )
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
        'available_mods': ['EZ', 'NF', 'HT', 'HR', 'SD', 'PF', 'DT', 'HD', 'FI', 'FL'],
    }
    return render(request, 'dashboard/leaderboard.html', context)

def home(request):
    if request.user.is_authenticated:
        return redirect('/dashboard/')
    return render(request, 'dashboard/home.html')