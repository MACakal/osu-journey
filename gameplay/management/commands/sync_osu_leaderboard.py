import time
import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from accounts.models import Player
from accounts.services import resize_and_save_avatar
from gameplay.models import Play, Beatmap

OSU_API_BASE = "https://osu.ppy.sh/api/v2"
SKIP_FIRST_USERS = 0


def get_system_token():
    response = requests.post(
        "https://osu.ppy.sh/oauth/token",
        data={
            "client_id": settings.OSU_CLIENT_ID,
            "client_secret": settings.OSU_CLIENT_SECRET,
            "grant_type": "client_credentials",
            "scope": "public",
        },
        timeout=20,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def osu_get(endpoint, token, params=None):
    response = requests.get(
        f"{OSU_API_BASE}{endpoint}",
        headers={"Authorization": f"Bearer {token}"},
        params=params,
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def chunked(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def normalize_mods(mods):
    """
    Store mods consistently as a Python list of strings.
    Normalizes NC -> DT.
    """
    if not mods:
        return []

    normalized = []
    seen = set()

    for mod in mods:
        if isinstance(mod, dict):
            mod = mod.get("acronym") or mod.get("short_name") or mod.get("name") or ""
        mod = str(mod).strip().upper()
        if not mod:
            continue
        if mod == "NC":
            mod = "DT"
        if mod not in seen:
            seen.add(mod)
            normalized.append(mod)

    return normalized


def build_beatmap_payload(beatmap_data):
    """
    Convert a beatmap API payload into model fields.
    """
    beatmapset = beatmap_data.get("beatmapset") or {}
    covers = beatmapset.get("covers") or {}

    return {
        "beatmapset_id": beatmapset.get("id"),
        "title": beatmapset.get("title", "Unknown"),
        "artist": beatmapset.get("artist", "Unknown"),
        "mapper": beatmapset.get("creator", "Unknown"),
        "star_rating": beatmap_data.get("difficulty_rating", 0) or 0,
        "bpm": beatmap_data.get("bpm", 0) or 0,
        "length_seconds": beatmap_data.get("total_length", 0) or 0,
        "ar": beatmap_data.get("ar", 0) or 0,
        "od": beatmap_data.get("accuracy", 0) or 0,
        "cs": beatmap_data.get("cs", 0) or 0,
        "version": beatmap_data.get("version", "") or "",
        "cover_url": covers.get("cover"),
    }


def fetch_beatmaps_batch(token, beatmap_ids):
    """
    Fetch beatmaps in batches of 50 using /beatmaps?ids[]=...
    Returns a dict {beatmap_id: beatmap_payload}.
    """
    cache = {}

    unique_ids = []
    seen = set()
    for bid in beatmap_ids:
        if bid and bid not in seen:
            seen.add(bid)
            unique_ids.append(bid)

    for batch in chunked(unique_ids, 50):
        params = [("ids[]", bid) for bid in batch]
        data = osu_get("/beatmaps", token, params=params)
        for beatmap in data.get("beatmaps", []):
            beatmap_id = beatmap.get("id")
            if beatmap_id:
                cache[beatmap_id] = beatmap

    return cache


def fetch_single_beatmap(token, beatmap_id):
    data = osu_get(f"/beatmaps/{beatmap_id}", token)
    if isinstance(data, dict):
        return data
    return None


def hydrate_beatmaps(token, beatmap_ids):
    """
    Creates missing beatmaps in bulk and returns a dict:
    {beatmap_id: Beatmap instance}
    """
    unique_ids = []
    seen = set()
    for bid in beatmap_ids:
        if bid and bid not in seen:
            seen.add(bid)
            unique_ids.append(bid)

    if not unique_ids:
        return {}

    payload_cache = fetch_beatmaps_batch(token, unique_ids)

    for beatmap_id in unique_ids:
        if beatmap_id not in payload_cache:
            try:
                payload = fetch_single_beatmap(token, beatmap_id)
                if isinstance(payload, dict):
                    payload_cache[beatmap_id] = payload
            except Exception:
                pass

    existing = {
        b.beatmap_id: b
        for b in Beatmap.objects.filter(beatmap_id__in=unique_ids)
    }

    to_create = []
    for beatmap_id in unique_ids:
        if beatmap_id in existing:
            continue

        payload = payload_cache.get(beatmap_id)
        if not payload:
            continue

        defaults = build_beatmap_payload(payload)
        if not defaults.get("beatmapset_id"):
            continue

        to_create.append(Beatmap(beatmap_id=beatmap_id, **defaults))

    if to_create:
        Beatmap.objects.bulk_create(to_create, ignore_conflicts=True, batch_size=100)

    final_map = {
        b.beatmap_id: b
        for b in Beatmap.objects.filter(beatmap_id__in=unique_ids)
    }
    return final_map


class Command(BaseCommand):
    help = "Sync top 200 osu players and their top 100 plays"

    def handle(self, *args, **options):
        token = get_system_token()

        self.stdout.write(self.style.SUCCESS("Fetching top players..."))

        players = []
        for offset in [0, 100]:
            data = osu_get(
                "/rankings/osu/performance",
                token,
                params={"limit": 100, "offset": offset},
            )
            batch = data.get("ranking", [])
            players.extend(batch)
            self.stdout.write(f"Fetched batch: {len(batch)} (offset {offset})")

        self.stdout.write(self.style.SUCCESS(f"Total players fetched: {len(players)}"))

        players_to_sync = players[SKIP_FIRST_USERS:]
        self.stdout.write(
            self.style.WARNING(
                f"Skipping first {SKIP_FIRST_USERS} users, syncing {len(players_to_sync)} players"
            )
        )

        for i, p in enumerate(players_to_sync, start=SKIP_FIRST_USERS + 1):
            user = p.get("user") or {}
            user_id = user.get("id")
            username = user.get("username", "unknown")
            avatar_url = user.get("avatar_url")

            if not user_id:
                self.stdout.write(self.style.WARNING(f"[{i}] Skipping row with no user id"))
                continue

            self.stdout.write(f"\n[{i}/{len(players)}] Syncing {username} ({user_id})")

            player, created = Player.objects.get_or_create(
                osu_id=user_id,
                defaults={
                    "osu_username": username,
                    "profile_image_url": avatar_url,
                },
            )

            avatar_changed = created

            if player.osu_username != username:
                player.osu_username = username

            if avatar_url and player.profile_image_url != avatar_url:
                player.profile_image_url = avatar_url
                avatar_changed = True

            update_fields = []
            if player.osu_username != username:
                update_fields.append("osu_username")
            if avatar_url and player.profile_image_url == avatar_url:
                update_fields.append("profile_image_url")

            if update_fields:
                player.save(update_fields=list(set(update_fields)))

            if avatar_url and (avatar_changed or not player.avatar_image):
                try:
                    resize_and_save_avatar(player, player.profile_image_url)
                    self.stdout.write(f"{username}: avatar updated")
                except Exception as e:
                    self.stdout.write(f"{username}: avatar failed - {e}")

            try:
                plays = osu_get(
                    f"/users/{user_id}/scores/best",
                    token,
                    params={"limit": 100},
                )
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"FAILED plays for {username}: {e}"))
                continue

            self.stdout.write(f"Fetched plays: {len(plays)}")

            if not plays:
                self.stdout.write(self.style.WARNING(f"No plays returned for {username}"))
                continue

            beatmap_ids = []
            for s in plays:
                beatmap_data = s.get("beatmap") or {}
                beatmap_id = beatmap_data.get("id")
                if beatmap_id:
                    beatmap_ids.append(beatmap_id)

            beatmap_cache = hydrate_beatmaps(token, beatmap_ids)
            self.stdout.write(f"Hydrated beatmaps in cache: {len(beatmap_cache)}")

            play_objects = []
            skipped_no_beatmap_id = 0
            skipped_no_beatmap = 0

            for s in plays:
                beatmap_data = s.get("beatmap") or {}
                beatmap_id = beatmap_data.get("id")

                if not beatmap_id:
                    skipped_no_beatmap_id += 1
                    continue

                beatmap = beatmap_cache.get(beatmap_id)
                if beatmap is None:
                    skipped_no_beatmap += 1
                    continue

                play_objects.append(
                    Play(
                        osu_score_id=s.get("id"),
                        player=player,
                        beatmap=beatmap,
                        pp=s.get("pp") or 0,
                        accuracy=s.get("accuracy") or 0,
                        score=s.get("score") or 0,
                        max_combo=s.get("max_combo") or 0,
                        rank=s.get("rank"),
                        mods=normalize_mods(s.get("mods")),
                        passed=bool(s.get("passed", True)),
                        played_at=s.get("created_at"),
                        adjusted_star_rating=float(beatmap.star_rating or 0),
                    )
                )

            if not play_objects:
                self.stdout.write(
                    self.style.WARNING(
                        f"{username}: saved 0 plays "
                        f"(missing beatmap_id={skipped_no_beatmap_id}, missing beatmap data={skipped_no_beatmap})"
                    )
                )
                continue

            with transaction.atomic():
                Play.objects.filter(player=player).delete()
                Play.objects.bulk_create(play_objects, batch_size=100)

            Player.objects.filter(pk=player.pk).update(last_synced_at=timezone.now())

            self.stdout.write(
                self.style.SUCCESS(
                    f"{username}: saved {len(play_objects)} plays "
                    f"(missing beatmap_id={skipped_no_beatmap_id}, missing beatmap data={skipped_no_beatmap})"
                )
            )

            time.sleep(0.3)

        self.stdout.write(self.style.SUCCESS("SYNC COMPLETE"))