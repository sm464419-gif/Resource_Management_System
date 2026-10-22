from django.urls import path
from . import views

app_name = "resources"

urlpatterns = [
    # Resource URLs
    path("", views.resource_list, name="resource_list"),
    path("<int:pk>/", views.resource_detail, name="resource_detail"),
    path("create/", views.resource_create, name="resource_create"),
    path("<int:pk>/update/", views.resource_update, name="resource_update"),
    path("<int:pk>/delete/", views.resource_delete, name="resource_delete"),

    # Category URLs
    path("categories/", views.category_list, name="category_list"),
    path("categories/create/", views.category_create, name="category_create"),
]