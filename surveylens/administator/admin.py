from django.contrib import admin

# Register your models here.


from .models import Survey, SurveyQuestion, SurveyResponse, SurveySession, SurveyChatSession, SurveyChatMessage,UserSurveySession, UserSurveyAnswer,SurveyReport
admin.site.register(Survey)
admin.site.register(SurveyQuestion)
admin.site.register(SurveyResponse)
admin.site.register(SurveySession)
admin.site.register(SurveyChatSession)
admin.site.register(SurveyChatMessage)



@admin.register(UserSurveySession)
class UserSurveySessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "survey", "is_completed", "is_notified", "current_question_index", "created_at")
    list_filter = ("is_completed", "is_notified", "survey")
    search_fields = ("user__username", "user__email", "survey__title")

@admin.register(UserSurveyAnswer)
class UserSurveyAnswerAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "question", "created_at")
    search_fields = ("session__user__username", "question__question_text")


admin.site.register(SurveyReport)