import requests
from django.conf import settings

OSU_TOKEN_URL = 'https://osu.ppy.sh/oauth/token'
OSU_API_BASE = 'https://osu.ppy.sh/api/v2'
OSU_AUTH_URL = 'https://osu.ppy.sh/oauth/authorize'


def get_auth_url():
    params = {
        'client_id': settings.OSU_CLIENT_ID,
        'redirect_uri': settings.OSU_REDIRECT_URI,
        'response_type': 'code',
        'scope': 'identify public',
        'prompt': 'none',
    }
    param_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    return f"{OSU_AUTH_URL}?{param_string}"


def exchange_code(code):
    response = requests.post(OSU_TOKEN_URL, data={
        'client_id': settings.OSU_CLIENT_ID,
        'client_secret': settings.OSU_CLIENT_SECRET,
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': settings.OSU_REDIRECT_URI,
    })
    response.raise_for_status()
    return response.json()


def get_current_user(access_token):
    response = requests.get(f"{OSU_API_BASE}/me", headers={
        'Authorization': f"Bearer {access_token}"
    })
    response.raise_for_status()
    return response.json()