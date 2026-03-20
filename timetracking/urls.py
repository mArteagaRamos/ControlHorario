from django.urls import path
from . import views

urlpatterns = [
    path('time_entries/', views.time_entries, name='time_entries'),
]