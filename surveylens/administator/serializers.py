from rest_framework import serializers
from .models import Survey

class SurveyHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Survey
        fields = ["id", "title", "age_group", "location", "created_at"]
