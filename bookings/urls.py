from django.urls import path
from . import views

app_name = 'bookings'

urlpatterns = [
    path('', views.booking_list, name='booking_list'),
    path('<int:id>/', views.booking_detail, name='booking_detail'),
    path('create/', views.create_booking, name='create_booking'),
    path('<int:id>/cancel/', views.cancel_booking, name='cancel_booking'),
]
