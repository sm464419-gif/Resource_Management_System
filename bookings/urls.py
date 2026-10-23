from django.urls import path
from . import views

app_name = 'bookings'

urlpatterns = [
    path('', views.booking_list, name='booking_list'),
    path('<int:id>/', views.booking_detail, name='booking_detail'),
    path('create/', views.create_booking, name='create_booking'),
    path('<int:id>/cancel/', views.cancel_booking, name='cancel_booking'),
    path('calendar/', views.booking_calendar, name='booking_calendar'),
    path('history/', views.booking_history, name='booking_history'),
    path('conflicts/', views.conflict_list, name='conflict_list'),
    path('conflicts/<int:id>/', views.conflict_detail, name='conflict_detail'),
    path('conflicts/<int:id>/resolve/', views.resolve_conflict, name='resolve_conflict'),
    path('waitlist/', views.waitlist_view, name='waitlist'),
    path('waitlist/add/', views.add_to_waitlist, name='add_to_waitlist'),
    path('waitlist/<int:id>/leave/', views.leave_waitlist, name='leave_waitlist'),
]
