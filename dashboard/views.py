from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.views.decorators.cache import never_cache
from accounts import services as osu_services
from gameplay.services import sync_recent_plays, update_skill_baseline

@never_cache
@login_required(login_url='/auth/login/')
def dashboard(request):
    try:
        player = request.user.player
    except Exception:
        return redirect('/auth/logout/')

    # sync plays on every dashboard load for now
    try:
        plays_data = osu_services.get_recent_plays(
            player.access_token,
            player.osu_id
        )
        new_plays = sync_recent_plays(player, plays_data)
        update_skill_baseline(player)
    except Exception as e:
        print(f"Sync error: {e}")

    context = {
        'player': player,
        'recent_plays': player.plays.order_by('-played_at')[:10],
    }
    return render(request, 'dashboard/dashboard.html', context)

def home(request):
    return render(request, 'dashboard/home.html')