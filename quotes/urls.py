from django.urls import path
from . import views

urlpatterns = [
    path('', views.QuoteUploadView.as_view(), name='quote_upload'),
    path('result/', views.QuoteResultView.as_view(), name='quote_result'),
    path('download/<int:quote_id>/<str:format>/', views.DownloadReportView.as_view(), name='download_report'),
] 