import requests
from django.conf import settings
from io import BytesIO
from django.core.files.base import ContentFile
from PIL import Image, ImageOps

OSU_TOKEN_URL = 'https://osu.ppy.sh/oauth/token'
OSU_API_BASE = 'https://osu.ppy.sh/api/v2'
OSU_AUTH_URL = 'https://osu.ppy.sh/oauth/authorize'


def get_auth_url():
    params = {
        'client_id': settings.OSU_CLIENT_ID,
        'redirect_url': settings.OSU_REDIRECT_URL,
        'response_type': 'code',
        'scope': 'identify public',
    }
    param_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    return f"{OSU_AUTH_URL}?{param_string}"


def exchange_code(code):
    response = requests.post(OSU_TOKEN_URL, data={
        'client_id': settings.OSU_CLIENT_ID,
        'client_secret': settings.OSU_CLIENT_SECRET,
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_url': settings.OSU_REDIRECT_URL,
    })
    response.raise_for_status()
    return response.json()


def get_current_user(access_token):
    response = requests.get(f"{OSU_API_BASE}/me", headers={
        'Authorization': f"Bearer {access_token}"
    })
    response.raise_for_status()
    return response.json()


def resize_and_save_avatar(player, avatar_url, size=(60, 60)):
    if not avatar_url:
        return

    try:
        response = requests.get(avatar_url, timeout=10)
        response.raise_for_status()

        image = Image.open(BytesIO(response.content))
        image = image.convert('RGBA')
        resized = ImageOps.fit(image, size, method=Image.LANCZOS)

        buffer = BytesIO()
        resized.save(buffer, format='PNG')
        buffer.seek(0)

        filename = f'avatars/{player.osu_id}.png'
        player.avatar_image.save(filename, ContentFile(buffer.read()), save=True)
    except Exception as e:
        print(f'Could not resize avatar: {e}')


def get_recent_plays(access_token, osu_id, limit=50):
    response = requests.get(
        f"{OSU_API_BASE}/users/{osu_id}/scores/recent",
        headers={
            'Authorization': f"Bearer {access_token}"
        },
        params={
            'include_fails': 1,
            'limit': limit,
        }
    )
    response.raise_for_status()
    return response.json()

def get_top_plays(access_token, osu_id, limit=100):
    response = requests.get(
        f"{OSU_API_BASE}/users/{osu_id}/scores/best",
        headers={
            'Authorization': f"Bearer {access_token}"
        },
        params={
            'limit': limit,
        }
    )
    response.raise_for_status()
    return response.json()

def refresh_access_token(player):
    response = requests.post(OSU_TOKEN_URL, data={
        'client_id': settings.OSU_CLIENT_ID,
        'client_secret': settings.OSU_CLIENT_SECRET,
        'grant_type': 'refresh_token',
        'refresh_token': player.refresh_token,
    })
    response.raise_for_status()
    data = response.json()

    from django.utils import timezone
    from datetime import timedelta

    player.access_token = data['access_token']
    player.refresh_token = data['refresh_token']
    player.token_expires_at = timezone.now() + timedelta(seconds=data['expires_in'])
    player.save(update_fields=['access_token', 'refresh_token', 'token_expires_at'])

    return player.access_token

def get_valid_token(player):
    from django.utils import timezone

    if timezone.now() >= player.token_expires_at:
        return refresh_access_token(player)
    return player.access_token