from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('top-plays/', views.top_plays, name='top_plays'),
    path('quests/', views.quests, name='quests'),
    path('xp-logs/', views.xp_logs, name='xp_logs'),
]