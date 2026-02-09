# siteapp/api_urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("zeus/", views.api_zeus, name="api_zeus"),
]
