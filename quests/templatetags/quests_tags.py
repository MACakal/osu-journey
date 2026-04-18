from django import template
from quests.models import Quest  # adjust if your model is elsewhere

register = template.Library()

@register.filter
def get_quest_name(quest_id):
    try:
        return Quest.objects.get(id=quest_id).name
    except Quest.DoesNotExist:
        return "Unknown quest"