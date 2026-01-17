
# accounts/urls.py
from django.urls import path
from .views import admin_login_view, admin_logout_view

app_name = "accounts"

urlpatterns = [
    path("login/", admin_login_view, name="login"),
    path("logout/", admin_logout_view, name="logout"),
]
# FIN accounts/urls.py