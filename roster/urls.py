from django.urls import path
from . import views
app_name = 'roster'
urlpatterns = [
    path('', views.member_list, name='list'),
    path('members/new/', views.member_create, name='create'),
    path('members/<int:pk>/edit/', views.member_edit, name='edit'),
    path('members/<int:pk>/types/<str:pokemon_type>/<str:category>/', views.participation_edit, name='participation'),
    path('members/<int:pk>/delete/', views.member_delete, name='delete'),
]
