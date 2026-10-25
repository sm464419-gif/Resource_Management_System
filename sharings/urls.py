from django.urls import path
from . import views

app_name = "sharings"

urlpatterns = [
    path("", views.shared_pool_list, name="shared_pool"),
    path("release/", views.release_to_pool, name="release_to_pool",),
    path("withdraw/<int:pool_id>/", views.withdraw_from_pool, name="withdraw_from_pool",),
    path("request/<int:pool_id>/", views.request_share, name="request_create",),
    path("requests/", views.sharing_request_list, name="shared_requests",),
    path("requests/<int:request_id>/", views.sharing_request_detail, name="request_detail",),
    path("requests/<int:request_id>/approve/", views.approve_request, name="approve_request",),
    path("requests/<int:request_id>/reject/", views.reject_request, name="reject_request",),
]
