
from django.urls import path, include

urlpatterns = [
    path("accounts/", include("accounts.urls")),
    # path("dashboard/", include("dashboard.urls")),  # si tienes dashboard
]
# FIN anaira-erp/project/urls.py