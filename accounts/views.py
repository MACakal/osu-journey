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
    if 'error' in request.GET:
        print(f"OAuth error in callback: {request.GET.get('error')}")
        return redirect('/')

    code = request.GET.get('code')
    print(f"Callback received code: {code}")

    if not code:
        print("No code in callback")
        return redirect('accounts:login')

    try:
        print("Exchanging code for token")
        token_data = services.exchange_code(code)
        access_token = token_data['access_token']
        refresh_token = token_data['refresh_token']
        expires_in = token_data['expires_in']
        token_expires_at = timezone.now() + timedelta(seconds=expires_in)

        print("Getting user data")
        user_data = services.get_current_user(access_token)
        osu_id = user_data['id']
        osu_username = user_data['username']
        print(f"User: {osu_username}, ID: {osu_id}")

        user, created = User.objects.get_or_create(username=osu_username)
        print(f"User created: {created}")

        player, player_created = Player.objects.get_or_create(
            osu_id=osu_id,
            defaults={
                'user': user,
                'osu_username': osu_username,
                'access_token': access_token,
                'refresh_token': refresh_token,
                'token_expires_at': token_expires_at,
            }
        )
        print(f"Player created: {player_created}")

        player.osu_username = osu_username
        player.access_token = access_token
        player.refresh_token = refresh_token
        player.token_expires_at = token_expires_at
        player.save()

        print("Logging in user")
        auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        print("Redirecting to dashboard")
        return redirect('/dashboard/')

    except Exception as e:
        print(f"OAuth error: {e}")
        import traceback
        traceback.print_exc()
        return redirect('accounts:login')


def logout(request):
    auth_logout(request)
    return redirect('/')