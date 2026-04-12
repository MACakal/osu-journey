from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

@login_required(login_url='/auth/login/')
def dashboard(request):
    try:
        player = request.user.player
    except Exception:
        return redirect('/auth/logout/')
    
    context = {
        'player': player,
    }
    return render(request, 'dashboard/dashboard.html', context) 