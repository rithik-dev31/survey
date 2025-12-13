from django.db import models
from django.contrib.auth.models import User
from django.conf import settings

# Create your models here.
class Survey(models.Model):
    title = models.CharField(max_length=255)
    age_group = models.CharField(max_length=100, null=True, blank=True)
    occupation = models.CharField(max_length=100, null=True, blank=True)
    location = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class SurveyQuestion(models.Model):
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE)
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, default="text")
    options = models.JSONField(null=True, blank=True)

class SurveyResponse(models.Model):
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE)
    question = models.ForeignKey(SurveyQuestion, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class SurveySession(models.Model):
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

class SurveyChatSession(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    survey = models.ForeignKey(Survey, null=True, blank=True, on_delete=models.SET_NULL)

class SurveyChatMessage(models.Model):
    session = models.ForeignKey(SurveyChatSession, on_delete=models.CASCADE)
    sender = models.CharField(max_length=10)  # "admin" or "bot"
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)


class UserSurveySession(models.Model):
    """
    A per-user instance of a survey. Tracks progress & notification state for each user.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_survey_sessions")
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name="user_survey_sessions")
    is_completed = models.BooleanField(default=False)
    is_notified = models.BooleanField(default=False)   # whether the user has been notified / seen this session
    current_question_index = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        # safe display if user has no __str__ etc.
        return f"UserSurveySession(id={self.id}, user={getattr(self.user, 'username', getattr(self.user, 'id', 'user'))}, survey={self.survey.title})"


class UserSurveyAnswer(models.Model):
    """
    Stores answers for each question for a given UserSurveySession.
    """
    session = models.ForeignKey(UserSurveySession, on_delete=models.CASCADE, related_name="questions")
    question = models.ForeignKey(SurveyQuestion, on_delete=models.CASCADE)
    answer_text = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Answer {self.id} (session={self.session.id})"
    



# --------------------------------data visulatizaion-------------------------


# administator/models.py

class SurveyReport(models.Model):
    survey = models.OneToOneField(Survey, on_delete=models.CASCADE, related_name="report")
    created_at = models.DateTimeField(auto_now_add=True)
    # raw aggregated JSON you send to OpenAI (optional but useful)
    data_json = models.JSONField(null=True, blank=True)
    # HTML report from your own renderer (Chart.js etc.)
    html_content = models.TextField(null=True, blank=True)
    # path or URL to generated PDF (if you store on disk/S3)
    pdf_file = models.FileField(upload_to="survey_reports/", null=True, blank=True)

    def __str__(self):
        return f"Report for survey {self.survey_id}"
