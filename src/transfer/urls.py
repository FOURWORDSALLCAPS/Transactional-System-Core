from django.urls import path

from .views import register_transfer


app_name = "transfer"

urlpatterns = [path("transfer/", register_transfer)]
