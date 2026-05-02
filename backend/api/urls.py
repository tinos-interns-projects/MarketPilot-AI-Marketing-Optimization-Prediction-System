from django.urls import path
from .views import predict, optimize_budget, channel_performance

urlpatterns = [
    path('predict/', predict, name='predict'),
    path('optimize-budget/', optimize_budget, name='optimize_budget'),
    path('channel-performance/', channel_performance, name='channel_performance'),
]