from django.urls import path
from .views import *

urlpatterns = [
    path('',welcome_page, name='welcome'),
    path('test/',test, name='test'),
    path('public_user/',public_user_page, name='public_user_page'),
    path('logout/', user_logout, name='logout'),
    path("admin/chatbot/", admin_chatbot_page, name="admin_chatbot_page"),
    path("admin_chatbot_api/", admin_chatbot_api, name="admin_chatbot_api"),

    path('admin-dashboard-stats/', admin_dashboard_stats, name='admin_dashboard_stats'),


    path("api/surveys/", survey_history, name="api_surveys"),
    path('api/surveys/<int:pk>/', survey_detail, name='survey-detail'),

    path('survey-report-pdf/<int:survey_id>/', survey_report_pdf, name='survey_report_pdf'),

]