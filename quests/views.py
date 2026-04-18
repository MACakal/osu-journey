from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from quests.services import ensure_player_quests


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
