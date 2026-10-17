from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from roster.media import member_image

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='roster/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('media/<path:path>', member_image, name='member_image'),
    path('', include('roster.urls')),
]
