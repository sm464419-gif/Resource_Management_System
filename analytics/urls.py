from django.urls import path
from . import views

app_name='analytics'
urlpatterns = [
    path('', views.analytics_dashboard, name='analytics_dashboard'),
    path('generate-report/', views.generate_report, name='generate_report'),
    path('calculate-utilization/', views.calculate_utilization, name='calculate_utilization'),
    path('utilization-report/', views.utilization_report_view, name='utilization_report'),
    path('predict-demand/', views.predict_demand, name='predict_demand'),
    path('demand-forecast/', views.demand_forecast_view, name='demand_forecast'),
    path('export-report/', views.report_export, name='report_export'),

]