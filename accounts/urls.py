from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('auth/login/', views.login, name='login'),
    path('auth/callback/', views.callback, name='callback'),
    path('auth/logout/', views.logout, name='logout'),
]