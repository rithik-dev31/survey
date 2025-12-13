from django.urls import path
from . import views 

urlpatterns = [
    path("dashboard/", views.public_dashboard, name="public_dashboard"),
    path('logout/',views.user_logout, name='logout'),
    path("survey/start/<int:session_id>/", views.start_survey_chatbot, name="start_survey_chatbot"),
    path("survey/answer/", views.survey_answer_api, name="survey_answer_api"),
]
