from django.shortcuts import redirect
from django.contrib.auth.models import User
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.utils import timezone
from datetime import timedelta
from .models import Player
from . import services


def login(request):
    return redirect(services.get_auth_url())


def callback(request):
    code = request.GET.get('code')

    if not code:
        return redirect('accounts:login')

    try:
        token_data = services.exchange_code(code)
        access_token = token_data['access_token']
        refresh_token = token_data['refresh_token']
        expires_in = token_data['expires_in']
        token_expires_at = timezone.now() + timedelta(seconds=expires_in)

        user_data = services.get_current_user(access_token)
        osu_id = user_data['id']
        osu_username = user_data['username']

        user, _ = User.objects.get_or_create(username=osu_username)
        player, _ = Player.objects.get_or_create(
            osu_id=osu_id,
            defaults={
                'user': user,
                'osu_username': osu_username,
                'access_token': access_token,
                'refresh_token': refresh_token,
                'token_expires_at': token_expires_at,
            }
        )

        player.osu_username = osu_username
        player.access_token = access_token
        player.refresh_token = refresh_token
        player.token_expires_at = token_expires_at
        player.save()

        auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return redirect('/dashboard/')

    except Exception as e:
        print(f"OAuth error: {e}")
        return redirect('accounts:login')


def logout(request):
    auth_logout(request)
    return redirect('/')