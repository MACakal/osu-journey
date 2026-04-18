from django.utils import timezone
from .models import Beatmap, Play
from accounts.models import Player
from progression.services import calculate_base_xp, award_xp

def sync_recent_plays(player, plays_data):
    new_plays = 0

    for play_data in plays_data:
        beatmap_data = play_data.get('beatmap', {})
        beatmapset_data = play_data.get('beatmapset', {})

        # get or create the beatmap
        beatmap, _ = Beatmap.objects.get_or_create(
            beatmap_id=beatmap_data['id'],
            defaults={
                'beatmapset_id': beatmapset_data.get('id', 0),
                'title': beatmapset_data.get('title', ''),
                'artist': beatmapset_data.get('artist', ''),
                'mapper': beatmapset_data.get('creator', ''),
                'star_rating': beatmap_data.get('difficulty_rating', 0),
                'bpm': beatmap_data.get('bpm') or 0,
                'length_seconds': beatmap_data.get('total_length', 0),
                'ar': beatmap_data.get('ar', 0),
                'od': beatmap_data.get('accuracy', 0),
                'cs': beatmap_data.get('cs', 0),
                'cover_url': beatmapset_data.get('covers', {}).get('card', ''),
                'version': beatmap_data.get('version', ''),
            }
        )

        # skip if this play already exists
        score_id = play_data.get('id')
        if not score_id or Play.objects.filter(osu_score_id=score_id).exists():
            continue

        # parse mods
        raw_mods = play_data.get('mods', [])
        mods = [mod['acronym'] if isinstance(mod, dict) else mod for mod in raw_mods]

        # get adjusted star rating if available
        adjusted_sr = play_data.get('difficulty_rating') or beatmap.star_rating

        play = Play.objects.create(
            osu_score_id=score_id,
            player=player,
            beatmap=beatmap,
            accuracy=play_data.get('accuracy', 0) * 100,
            score=play_data.get('total_score', 0),
            max_combo=play_data.get('max_combo', 0),
            passed=play_data.get('passed', False),
            mods=mods,
            adjusted_star_rating=adjusted_sr,
            played_at=play_data.get('ended_at') or play_data.get('created_at') or timezone.now(),
            rank=play_data.get('rank', 'F'),
            pp=play_data.get('pp'),
        )

        xp_amount, is_personal_best = calculate_base_xp(play, player.skill_baseline)
        award_xp(player, play, xp_amount, is_personal_best)

        # Check quest completion
        from quests.services import check_quest_completion
        check_quest_completion(play)

        new_plays += 1

    # update last synced timestamp
    player.last_synced_at = timezone.now()
    player.save(update_fields=['last_synced_at'])

    return new_plays


def update_skill_baseline(player):
    top_plays = player.plays.filter(
        passed=True
    ).order_by('-adjusted_star_rating')[:50]

    if not top_plays.exists():
        return

    avg = sum(p.adjusted_star_rating for p in top_plays) / top_plays.count()
    player.skill_baseline = round(avg, 2)
    player.save(update_fields=['skill_baseline'])

def sync_top_plays(player, plays_data):
    for play_data in plays_data:
        beatmap_data = play_data.get('beatmap', {})
        beatmapset_data = play_data.get('beatmapset', {})

        beatmap, _ = Beatmap.objects.get_or_create(
            beatmap_id=beatmap_data['id'],
            defaults={
                'beatmapset_id': beatmapset_data.get('id', 0),
                'title': beatmapset_data.get('title', ''),
                'artist': beatmapset_data.get('artist', ''),
                'mapper': beatmapset_data.get('creator', ''),
                'star_rating': beatmap_data.get('difficulty_rating', 0),
                'bpm': beatmap_data.get('bpm') or 0,
                'length_seconds': beatmap_data.get('total_length', 0),
                'ar': beatmap_data.get('ar', 0),
                'od': beatmap_data.get('accuracy', 0),
                'cs': beatmap_data.get('cs', 0),
                'cover_url': beatmapset_data.get('covers', {}).get('card', ''),
                'version': beatmap_data.get('version', ''),
            }
        )

        score_id = play_data.get('id')
        if not score_id or Play.objects.filter(osu_score_id=score_id).exists():
            continue

        raw_mods = play_data.get('mods', [])
        mods = [mod['acronym'] if isinstance(mod, dict) else mod for mod in raw_mods]

        adjusted_sr = play_data.get('difficulty_rating') or beatmap.star_rating
        
        play = Play.objects.create(
            osu_score_id=score_id,
            player=player,
            beatmap=beatmap,
            accuracy=play_data.get('accuracy', 0) * 100,
            score=play_data.get('total_score', 0),
            max_combo=play_data.get('max_combo', 0),
            passed=play_data.get('passed', False),
            mods=mods,
            adjusted_star_rating=adjusted_sr,
            played_at=play_data.get('ended_at') or play_data.get('created_at') or timezone.now(),
            rank=play_data.get('rank', 'F'),
            pp=play_data.get('pp'),
        )

        xp_amount, is_personal_best = calculate_base_xp(play, player.skill_baseline)
        award_xp(player, play, xp_amount, is_personal_best)