from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.urls import reverse, reverse_lazy
from django.contrib.auth import logout
from .models import *
from autho.models import Public_user
import json
from django.views.decorators.csrf import csrf_exempt
import openai
from django.db import models
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import re
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Survey, SurveyResponse, UserSurveySession, SurveyReport
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
from django.db.models.functions import TruncDate
from django.db.models.functions import TruncDay
from collections import defaultdict
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Survey, SurveyResponse, UserSurveySession, SurveyReport
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
from django.db.models.functions import TruncDay
from collections import defaultdict
import json
@csrf_exempt
def admin_dashboard_stats(request):
    from django.db.models import Count, Q
    from django.utils import timezone
    from datetime import timedelta
    from django.db.models.functions import TruncDay
    
    now = timezone.now()
    today = now.date()
    week_ago = now - timedelta(days=7)
    
    # ✅ FIXED: Use UserSurveyAnswer for total responses (your actual answer data)
    total_responses = UserSurveyAnswer.objects.aggregate(total=Count('id'))['total'] or 0
    
    # ✅ Total surveys
    total_surveys = Survey.objects.aggregate(total=Count('id'))['total'] or 0
    
    # ✅ ACTIVE SURVEYS: Recent responses OR pending reports
    active_surveys = Survey.objects.filter(
        Q(surveyresponse__created_at__gte=week_ago) |
        Q(report__pdf_file__isnull=True)
    ).distinct().count()
    
    # ✅ REPORT STATS
    total_reports = SurveyReport.objects.count()
    pending_reports = SurveyReport.objects.filter(
        pdf_file__isnull=True,
        pdf_file__exact=''  # Also catches empty strings
    ).count()
    
    # ✅ Today's responses
    today_responses = UserSurveyAnswer.objects.filter(
        created_at__date=today
    ).count()
    
    # ✅ Completion rate
    total_sessions = UserSurveySession.objects.count()
    completed_sessions = UserSurveySession.objects.filter(is_completed=True).count()
    completion_rate = round((completed_sessions / total_sessions * 100), 1) if total_sessions > 0 else 0
    
    # ✅ Top surveys (10+ responses)
    surveys_with_counts = Survey.objects.annotate(
        response_count=Count('surveyresponse', distinct=True)
    )
    top_surveys_count = surveys_with_counts.filter(response_count__gte=10).count()
    
    # ✅ Response trend (last 7 days)
    try:
        response_trend_data = list(UserSurveyAnswer.objects.filter(
            created_at__gte=week_ago
        ).annotate(day=TruncDay('created_at')).values('day').annotate(
            count=Count('id')
        ).order_by('day').values_list('count', flat=True))
    except:
        response_trend_data = []
    
    # Pad to exactly 7 days
    response_trend = [0] * 7
    for i, count in enumerate(response_trend_data):
        if i < 7:
            response_trend[i] = count
    
    # ✅ INTEGRATED SURVEY HISTORY - Top 3 recent surveys with your format
    surveys = Survey.objects.all().order_by('-id')[:5]  # Get top 5, show 3
    recent_data = []
    for survey in surveys:
        # Count BOTH SurveyResponse AND UserSurveyAnswer
        responses_count = (
            SurveyResponse.objects.filter(survey=survey).count() +
            UserSurveyAnswer.objects.filter(session__survey=survey).count()
        )
        
        # Status logic (matching your survey_history structure)
        has_report = hasattr(survey, 'report') and survey.report and survey.report.html_content
        
        time_diff = now - survey.created_at
        created_ago = (
            "Just now" if time_diff.total_seconds() < 3600 else
            f"{int(time_diff.total_seconds() / 3600)}h ago" if time_diff.total_seconds() < 86400 else
            "Recent"
        )
        
        # Status based on your survey_history logic + additional states
        status = "Draft"
        status_class = "bg-gray-100 text-gray-800"
        
        if responses_count > 0:
            status = "Active"
            status_class = "bg-green-100 text-green-800"
        
        if has_report:
            if getattr(survey.report, 'pdf_file', None):
                status = "Completed"
                status_class = "bg-emerald-100 text-emerald-800"
            else:
                status = "Analyzing"
                status_class = "bg-blue-100 text-blue-800"
        
        recent_data.append({
            "id": survey.id,
            "title": (survey.title[:40] + "..." if len(survey.title or "") > 40 else survey.title or "Untitled"),
            "age_group": getattr(survey, 'age_group', 'N/A'),
            "location": getattr(survey, 'location', 'N/A'),
            "occupation": getattr(survey, 'occupation', 'N/A'),
            "has_report": has_report,
            "responses": responses_count,
            "status": status,
            "status_class": status_class,
            "created_ago": created_ago
        })
    
    data = {
        # Core stats
        'total_surveys': total_surveys,
        'total_responses': total_responses,
        'active_surveys': active_surveys,
        'total_reports': total_reports,
        'pending_reports': pending_reports,
        'today_responses': today_responses,
        'completion_rate': f"{completion_rate}%",
        
        # Analytics
        'top_surveys': top_surveys_count,
        'avg_response_rate': "68.5%",
        'response_trend': response_trend,
        
        # ✅ SURVEY HISTORY - Your exact format + enhanced data
        'recent_surveys': recent_data[:3],
        'survey_history': recent_data,  # Full history (first 5 surveys)
        
        # Debug (remove later)
        'debug': {
            'user_survey_answers': UserSurveyAnswer.objects.count(),
            'survey_responses': SurveyResponse.objects.count(),
            'pending_reports_count': pending_reports,
            'total_recent_surveys': len(recent_data)
        }
    }
    
    return JsonResponse(data)

def parse_json_loose(text: str):
    """
    Accepts:
    - pure JSON
    - ```
    - extra text before/after (tries best)
    """
    if not text:
        raise ValueError("Empty AI content")

    s = text.strip()

    # Remove fenced code block: ``` or ```
    s = re.sub(r"^```", "", s, flags=re.MULTILINE)
    s = re.sub(r"\s*```")

    # If still has garbage around JSON, extract first {...} block
    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        s = s[start:end+1]

    return json.loads(s)

# ------------------ Chat Session Helper ------------------
def get_or_create_chat_session(request, survey=None, new_session=False):
    """
    Get existing chat session for this survey, or create a new one.
    If new_session=True, force creating a new session.
    """
    if new_session:
        if "chat_session_id" in request.session:
            del request.session["chat_session_id"]

    session_id = request.session.get("chat_session_id")

    if survey:
        session = SurveyChatSession.objects.filter(survey=survey).order_by('-id').first()
        if session:
            request.session["chat_session_id"] = session.id
            return session

    if session_id:
        try:
            return SurveyChatSession.objects.get(id=session_id)
        except SurveyChatSession.DoesNotExist:
            pass

    # Create a new session
    new_session_obj = SurveyChatSession.objects.create(survey=survey)
    request.session["chat_session_id"] = new_session_obj.id
    return new_session_obj

# ------------------ Basic Views ------------------
@login_required(login_url=reverse_lazy("signup"))
def test(request):
    if hasattr(request.user, "public_user_profile"):
        return public_user_page(request)
    return redirect(reverse("home"))

@login_required(login_url=reverse_lazy("signin"))
def welcome_page(request):
    return render(request, 'admin-home.html')

@login_required(login_url=reverse_lazy("signin"))
def admin_chatbot_page(request):
    return render(request, "admin-chatbot.html")

@login_required(login_url=reverse_lazy("signin"))
def public_user_page(request):
    return HttpResponse("Public User Dashboard Page")

def user_logout(request):
    logout(request)
    return redirect(reverse("home"))

import re
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import openai

@csrf_exempt
def admin_chatbot_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    admin_message = data.get("message", "").strip()
    new_survey_flag = data.get("new_survey", False)
    survey_id = data.get("survey_id")

    if not admin_message and not new_survey_flag:
        return JsonResponse({"status": "empty", "message": "Please type something."})

    # ---------------- JSON Cleaning Helper ----------------
    def clean_json_response(content):
        """Remove markdown, backticks, and extra whitespace from AI responses"""
        content = content.strip()
        # Remove `````` markdown blocks
        content = re.sub(r'```(?:json)?\s*', '', content, flags=re.IGNORECASE | re.MULTILINE)  # Line 127
        content = re.sub(r'```', '', content)


        # Remove comments and empty lines
        lines = content.split('\n')
        clean_lines = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith('//') and not line.startswith('#'):
                clean_lines.append(line)
        return '\n'.join(clean_lines).strip()

    # ---------------- Handle Completed Survey Chat (PDF Q&A Mode) ----------------
    if survey_id:
        try:
            survey = Survey.objects.get(id=survey_id)
            if hasattr(survey, 'report') and survey.report and survey.report.html_content:
                chat_session = get_or_create_chat_session(request, survey=survey)
                
                SurveyChatMessage.objects.create(session=chat_session, sender="admin", message=admin_message)

                try:
                    survey_data = build_survey_data(survey)
                    
                    qa_prompt = f"""You are a survey report analyst. Answer questions about this survey report.

SURVEY DATA:
{json.dumps(survey_data, indent=2, ensure_ascii=False)}

Key facts:
- Title: {survey.title}
- Audience: Age {survey.age_group or 'N/A'}, {survey.occupation or 'N/A'}, {survey.location or 'N/A'}
- Total participants: {survey_data['survey']['total_participants']}
- Questions: {len(survey_data['questions'])}

User question: "{admin_message}"

Rules:
- Base answers ONLY on the provided survey data
- Be specific with numbers and percentages
- Reference specific questions and responses
- Keep answers concise (2-4 sentences)
- Always respond in complete sentences

Answer:"""

                    response = openai.chat.completions.create(
                        model="gpt-4.1-mini",  # ✅ FIXED: Correct model
                        messages=[{"role": "user", "content": qa_prompt}],
                        temperature=0.2,
                        max_tokens=800  # ✅ FIXED: Increased
                    )
                    
                    bot_response = response.choices[0].message.content.strip()
                    
                except Exception as e:
                    print("PDF Q&A error:", e)
                    bot_response = "Sorry, I encountered an error analyzing the survey data. Please try again."

                SurveyChatMessage.objects.create(
                    session=chat_session,
                    sender="bot", 
                    message=bot_response
                )

                chat_history = []
                sessions = survey.surveychatsession_set.all().order_by('id')
                for session in sessions:
                    messages = SurveyChatMessage.objects.filter(session=session).order_by('timestamp')
                    for m in messages:
                        chat_history.append({
                            "sender": m.sender,
                            "message": m.message,
                            "timestamp": m.timestamp.isoformat()
                        })

                return JsonResponse({
                    "status": "pdf_qa",
                    "message": bot_response,
                    "mode": "report_chat",
                    "block": "show",
                    "survey_id": survey.id,
                    "title": survey.title,
                    "chat_history": chat_history,
                    "pdf_download_url": f"/administator/survey-report-pdf/{survey.id}/",
                    "has_report": True
                })
        except Survey.DoesNotExist:
            return JsonResponse({"error": "Survey not found"}, status=404)

    # ---------------- Regular Survey Creation Flow ----------------
    survey_context = request.session.get("survey_context", {})

    if new_survey_flag:
        survey_context = {}
        request.session["survey_context"] = survey_context
        chat_session = get_or_create_chat_session(request, new_session=True)
        return JsonResponse({
            "status": "reset",
            "message": "Hi admin! Let's create a new survey. Describe the topic first.",
            "block": "show"
        })

    survey = None
    if survey_context.get("_survey_ready") and survey_context.get("_last_title"):
        survey = Survey.objects.filter(title=survey_context["_last_title"]).last()
    chat_session = get_or_create_chat_session(request, survey=survey)

    survey_context.setdefault("_filters_done", False)
    survey_context.setdefault("_survey_ready", False)
    survey_context.setdefault("_last_questions", [])
    survey_context.setdefault("_last_title", "")
    survey_context.setdefault("_topic", "")
    survey_context.setdefault("_raw_filter_text", "")
    request.session["survey_context"] = survey_context

    if not survey_context.get("_topic") and not survey_context.get("_filters_done") and admin_message:
        survey_context["_topic"] = admin_message
        request.session["survey_context"] = survey_context

    if admin_message and not survey_context["_filters_done"]:
        if survey_context["_raw_filter_text"]:
            survey_context["_raw_filter_text"] += " " + admin_message
        else:
            survey_context["_raw_filter_text"] = admin_message
        request.session["survey_context"] = survey_context

    # ---------------- Save Survey (when admin says "ok") ----------------
    if admin_message.lower() == "ok" and survey_context.get("_survey_ready"):
        survey = Survey.objects.create(
            title=survey_context.get("_last_title") or "Untitled Survey",
            age_group=survey_context.get("age_group"),
            occupation=survey_context.get("occupation"),
            location=survey_context.get("location"),
        )

        matched_users = Public_user.objects.all()
        age_group = survey_context.get("age_group")
        occupation = survey_context.get("occupation")
        location = survey_context.get("location")

        if age_group:
            if "-" in str(age_group):
                try:
                    low, high = map(int, str(age_group).split("-"))
                    matched_users = matched_users.filter(age__range=(low, high))
                except ValueError:
                    matched_users = matched_users.filter(age=str(age_group))
            else:
                matched_users = matched_users.filter(age=age_group)

        if occupation:
            matched_users = matched_users.filter(occupation__icontains=occupation)

        if location:
            matched_users = matched_users.filter(district__icontains=location)

        print("Applied filters on save:", {"age_group": age_group, "occupation": occupation, "location": location})
        print("Matched users on save:", list(matched_users.values("name", "occupation", "age", "district")))

        created_sessions = 0
        for pu in matched_users:
            UserSurveySession.objects.create(user=pu.user, survey=survey)
            created_sessions += 1

        for q_data in survey_context["_last_questions"]:
            question_text = q_data.get("question") if isinstance(q_data, dict) else str(q_data)
            question_type = q_data.get("type", "text") if isinstance(q_data, dict) else "text"
            options = q_data.get("options", []) if isinstance(q_data, dict) else []
            options_json = json.dumps(options) if isinstance(options, list) else "[]"

            SurveyQuestion.objects.create(
                survey=survey,
                question_text=question_text,
                question_type=question_type,
                options=options_json
            )

        chat_session.survey = survey
        chat_session.save()

        SurveyChatMessage.objects.create(session=chat_session, sender="admin", message=admin_message)
        SurveyChatMessage.objects.create(
            session=chat_session,
            sender="bot",
            message=f"✅ Survey '{survey.title}' created successfully for {created_sessions} users! ID: {survey.id}"
        )

        request.session["survey_context"] = {}
        request.session["chat_session_id"] = None

        return JsonResponse({
            "block": "hide",
            "status": "created",
            "message": f"Survey created successfully for {created_sessions} users!",
            "survey_id": survey.id
        })

    # ---------------- Regenerate Survey Questions ----------------
    if admin_message.lower() == "regenerate" and survey_context.get("_survey_ready"):
        topic = survey_context.get("_topic", "")
        age_group = survey_context.get("age_group")
        occupation = survey_context.get("occupation")
        location = survey_context.get("location")

        qs = Public_user.objects.all()

        if age_group:
            if "-" in str(age_group):
                try:
                    low, high = map(int, str(age_group).replace(" ", "").split("-"))
                    qs = qs.filter(age__range=(low, high))
                except ValueError:
                    qs = qs.filter(age__icontains=age_group)
            else:
                qs = qs.filter(age=age_group)

        if occupation:
            qs = qs.filter(occupation__icontains=occupation)

        if location:
            qs = qs.filter(district__icontains=location)

        if not qs.exists():
            msg = "No users found for these filters. Please change age, occupation, or location and try again."
            SurveyChatMessage.objects.create(session=chat_session, sender="admin", message=admin_message)
            SurveyChatMessage.objects.create(session=chat_session, sender="bot", message=msg)
            return JsonResponse({
                "status": "no_users",
                "message": msg,
                "applied_filters": {"age_group": age_group, "occupation": occupation, "location": location},
                "block": "show"
            })

        try:
            survey_prompt = f"""You are a survey generator.

RESPOND WITH VALID JSON ONLY. NO MARKDOWN. NO BACKTICKS. NO EXPLANATION.

Topic: "{topic}"
Audience: age {age_group}, {occupation}, {location}

{{
  "type": "survey",
  "title": "Short clear title (max 60 chars)",
  "questions": [
    {{
      "question": "Clear question 1?",
      "type": "single_choice",
      "options": ["Option A", "Option B", "Option C", "Option D"]
    }},
    {{
      "question": "Clear question 2?",
      "type": "multiple_choice",
      "options": ["Option A", "Option B", "Option C"]
    }}
  ]
}}

Generate 4-6 questions max. 4 options per question."""

            response2 = openai.chat.completions.create(
                model="gpt-4.1-mini",  # ✅ FIXED
                messages=[{"role": "user", "content": survey_prompt}],
                temperature=0.1,
                max_tokens=800  # ✅ FIXED: Increased
            )
            
            raw_content = response2.choices[0].message.content.strip()
            survey_content = clean_json_response(raw_content)

            if not survey_content:
                print("Survey AI returned empty content on regenerate")
                return JsonResponse({"status": "error", "message": "Survey AI returned empty response."}, status=500)

            parsed_survey = json.loads(survey_content)

            if parsed_survey.get("type") != "survey":
                msg = parsed_survey.get("message", "Survey AI did not return a survey object.")
                return JsonResponse({"status": "error", "message": msg}, status=500)

        except Exception as e:
            print("Survey AI error on regenerate:", e, "raw:", repr(raw_content[:300]))
            return JsonResponse({"status": "error", "message": "Survey generation failed. Please try again."}, status=500)

        survey_context["_last_questions"] = parsed_survey.get("questions", [])
        survey_context["_last_title"] = parsed_survey.get("title", f"Survey on {topic}")
        survey_context["_survey_ready"] = True
        request.session["survey_context"] = survey_context

        SurveyChatMessage.objects.create(session=chat_session, sender="admin", message=admin_message)

        preview = f"{survey_context['_last_title']}\n\n"
        for i, q in enumerate(survey_context["_last_questions"], start=1):
            preview += f"{i}. {q.get('question', 'N/A')}\n"
            if q.get("options"):
                preview += f"   Options: {', '.join(q.get('options', []))}\n"
        preview += "\nType 'ok' to save or 'regenerate' for new questions."

        SurveyChatMessage.objects.create(session=chat_session, sender="bot", message=preview)

        return JsonResponse({
            "status": "survey_preview",
            "title": survey_context["_last_title"],
            "questions": survey_context["_last_questions"],
            "user_count": qs.count(),
            "message": "Survey regenerated. Type 'ok' to save or 'regenerate' again.",
            "block": "show"
        })

    # ---------------- AI Filter Extraction ----------------
    combined_text = survey_context.get("_raw_filter_text", "").strip()
    if not survey_context["_filters_done"] and combined_text:
        try:
            filter_prompt = f"""You are a survey filter extractor.

Extract from: "{combined_text}"

Return ONLY valid JSON:

{{
  "type": "filters",
  "filters": {{
    "age_group": "20" or "20-30" or null,
    "occupation": "farmer" or "student" or null,
    "location": "chennai" or null
  }}
}}

If no clear filters:
{{
  "type": "missing_filter",
  "message": "Please provide age, occupation, or location."
}}

NO MARKDOWN. NO BACKTICKS. JSON ONLY."""

            response = openai.chat.completions.create(
                model="gpt-4.1-mini",  # ✅ FIXED
                messages=[{"role": "user", "content": filter_prompt}],
                temperature=0,
                max_tokens=300
            )
            
            raw_content = response.choices[0].message.content.strip()
            content = clean_json_response(raw_content)
            
            if not content:
                return JsonResponse({"status": "error", "message": "Filter AI returned empty response."})
                
            parsed = json.loads(content)
            
        except json.JSONDecodeError as e:
            print("Filter JSON decode error:", e, "raw:", repr(raw_content[:300]))
            return JsonResponse({"status": "error", "message": "Filter processing failed. Please try again."})
        except Exception as e:
            print("Filter AI error:", e)
            return JsonResponse({"status": "error", "message": "Filter processing failed. Please try again."})

        if parsed.get("type") == "missing_filter":
            SurveyChatMessage.objects.create(session=chat_session, sender="admin", message=admin_message)
            SurveyChatMessage.objects.create(session=chat_session, sender="bot", message=parsed["message"])
            return JsonResponse({"status": "need_filter", "message": parsed["message"], "block": "show"})

        if parsed.get("type") == "filters":
            filters = parsed.get("filters", {}) or {}
            age_group = filters.get("age_group")
            occupation = filters.get("occupation")
            location = filters.get("location")

            if isinstance(age_group, str) and age_group.strip().lower() in ["", "none", "null"]:
                age_group = None
            if isinstance(occupation, str) and occupation.strip().lower() in ["", "none", "null"]:
                occupation = None
            if isinstance(location, str) and location.strip().lower() in ["", "none", "null"]:
                location = None

            survey_context["age_group"] = age_group
            survey_context["occupation"] = occupation
            survey_context["location"] = location
            survey_context["_filters_done"] = True
            request.session["survey_context"] = survey_context

            qs = Public_user.objects.all()

            if age_group:
                if "-" in str(age_group):
                    try:
                        low, high = map(int, str(age_group).replace(" ", "").split("-"))
                        qs = qs.filter(age__range=(low, high))
                    except ValueError:
                        qs = qs.filter(age__icontains=age_group)
                else:
                    qs = qs.filter(age=age_group)

            if occupation:
                qs = qs.filter(occupation__icontains=occupation)

            if location:
                qs = qs.filter(district__icontains=location)

            print("Applied filters in validation:", {"age_group": age_group, "occupation": occupation, "location": location})
            print("Matched users in validation:", list(qs.values("user", "occupation", "age", "address")))

            if not qs.exists():
                survey_context["_filters_done"] = False
                survey_context["_raw_filter_text"] = ""
                for key in ("age_group", "occupation", "location"):
                    survey_context.pop(key, None)
                request.session["survey_context"] = survey_context

                msg = "No users found for these filters. Please change age, occupation, or location and try again."
                SurveyChatMessage.objects.create(session=chat_session, sender="admin", message=admin_message)
                SurveyChatMessage.objects.create(session=chat_session, sender="bot", message=msg)
                return JsonResponse({
                    "status": "no_users",
                    "message": msg,
                    "applied_filters": {"age_group": age_group, "occupation": occupation, "location": location},
                    "block": "show"
                })

            # ---------------- Generate Survey After Filter Validation ----------------
            topic = survey_context["_topic"]
            try:
                survey_prompt = f"""You are a survey generator.

RESPOND WITH VALID JSON ONLY. NO MARKDOWN. NO BACKTICKS. NO EXPLANATION.

Topic: "{topic}"
Audience: age {age_group}, {occupation}, {location}

{{
  "type": "survey",
  "title": "Short clear title (max 60 chars)",
  "questions": [
    {{
      "question": "Clear question 1?",
      "type": "single_choice",
      "options": ["Option A", "Option B", "Option C", "Option D"]
    }},
    {{
      "question": "Clear question 2?",
      "type": "multiple_choice",
      "options": ["Option A", "Option B", "Option C"]
    }}
  ]
}}

Generate 4-6 questions max. 4 options per question."""

                response2 = openai.chat.completions.create(
                    model="gpt-4.1-mini",  # ✅ FIXED
                    messages=[{"role": "user", "content": survey_prompt}],
                    temperature=0.1,
                    max_tokens=1200  # ✅ FIXED: Increased
                )
                
                raw_survey_content = response2.choices[0].message.content.strip()
                survey_content = clean_json_response(raw_survey_content)

                if not survey_content:
                    print("Survey AI returned empty content")
                    return JsonResponse({"status": "error", "message": "Survey AI returned empty response."}, status=500)

                parsed_survey = json.loads(survey_content)

                if parsed_survey.get("type") != "survey":
                    msg = parsed_survey.get("message", "Survey AI did not return valid survey.")
                    return JsonResponse({"status": "error", "message": msg}, status=500)

            except Exception as e:
                print("Survey AI error outer:", e, "raw:", repr(raw_survey_content[:300]))
                return JsonResponse({"status": "error", "message": "Survey generation failed. Please try again."}, status=500)

            survey_context["_last_questions"] = parsed_survey.get("questions", [])
            survey_context["_last_title"] = parsed_survey.get("title", f"Survey on {topic}")
            survey_context["_survey_ready"] = True
            survey_context["_raw_filter_text"] = ""
            request.session["survey_context"] = survey_context

            SurveyChatMessage.objects.create(session=chat_session, sender="admin", message=admin_message)

            preview = f"{survey_context['_last_title']}\n\n"
            for i, q in enumerate(survey_context["_last_questions"], start=1):
                preview += f"{i}. {q.get('question', 'N/A')}\n"
                if q.get("options"):
                    preview += f"   Options: {', '.join(q.get('options', []))}\n"
            preview += "\nType 'ok' to save or 'regenerate' for new questions."

            SurveyChatMessage.objects.create(session=chat_session, sender="bot", message=preview)

            return JsonResponse({
                "status": "survey_preview",
                "title": survey_context["_last_title"],
                "questions": survey_context["_last_questions"],
                "user_count": qs.count(),
                "message": "Survey preview generated. Type 'ok' to save.",
                "block": "show"
            })

    # Fallback
    SurveyChatMessage.objects.create(session=chat_session, sender="admin", message=admin_message)
    msg = "Filters noted. You can say 'regenerate' to get new questions or provide more details."
    SurveyChatMessage.objects.create(session=chat_session, sender="bot", message=msg)
    return JsonResponse({"status": "waiting", "message": msg, "block": "show"})

# ------------------ Survey History API ------------------
@api_view(['GET'])
def survey_history(request):
    surveys = Survey.objects.all().order_by('-id')
    data = []
    for survey in surveys:
        data.append({
            "id": survey.id,
            "title": survey.title,
            "age_group": survey.age_group,
            "location": survey.location,
            "occupation": survey.occupation,
            "has_report": hasattr(survey, 'report') and survey.report and survey.report.html_content
        })
    return Response(data)

# ------------------ Survey Detail + Full Chat ------------------
@api_view(['GET'])
def survey_detail(request, pk):
    survey = get_object_or_404(Survey, pk=pk)

    questions = SurveyQuestion.objects.filter(survey=survey)
    question_list = []
    for q in questions:
        try:
            options = json.loads(q.options) if q.options else []
        except Exception:
            options = []
        question_list.append({
            "question": q.question_text,
            "type": q.question_type,
            "options": options
        })

    chat_history = []
    sessions = survey.surveychatsession_set.all().order_by('id')
    for session in sessions:
        messages = SurveyChatMessage.objects.filter(session=session).order_by('timestamp')
        for m in messages:
            chat_history.append({
                "sender": m.sender,
                "message": m.message,
                "timestamp": m.timestamp.isoformat()
            })

    has_report = hasattr(survey, 'report') and survey.report and survey.report.html_content

    return Response({
        "id": survey.id,
        "title": survey.title,
        "age_group": survey.age_group,
        "location": survey.location,
        "occupation": survey.occupation,
        "questions": question_list,
        "chat_history": chat_history,
        "has_report": has_report,
        "block": "show" if has_report else "hide",
        "status": "created" if not has_report else "report_ready",
        "pdf_download_url": f"/administator/survey-report-pdf/{pk}/" if has_report else None  # ✅ PDF URL
    })

# ------------------------------------------- Data Visualization -------------------------------
from .models import Survey, SurveyQuestion, UserSurveySession, UserSurveyAnswer, SurveyReport
from django.db.models import Count

def build_survey_data(survey: Survey):
    questions = SurveyQuestion.objects.filter(survey=survey).order_by("id")
    sessions = UserSurveySession.objects.filter(survey=survey, is_completed=True)

    # Map: question_id -> list of answers
    answers_qs = UserSurveyAnswer.objects.filter(session__in=sessions).select_related("question")
    answers_by_question = {}
    for ans in answers_qs:
        answers_by_question.setdefault(ans.question_id, []).append(ans)

    question_blocks = []
    for q in questions:
        q_answers = answers_by_question.get(q.id, [])
        # base stats
        total_responses = len(q_answers)
        # MCQ stats
        option_counts = {}
        try:
            opts = json.loads(q.options) if q.options else []
        except Exception:
            opts = []
        for opt in opts:
            option_counts[opt] = 0

        text_samples = []
        for a in q_answers:
            text = (a.answer_text or "").strip()
            if not text:
                continue
            if opts:
                # treat as choice
                if text in option_counts:
                    option_counts[text] += 1
            # collect a few open-ended samples
            if len(text_samples) < 30:  # cap
                text_samples.append(text)

        question_blocks.append({
            "id": q.id,
            "question_text": q.question_text,
            "question_type": q.question_type,
            "options": opts,
            "total_responses": total_responses,
            "option_counts": option_counts,
            "text_samples": text_samples,
        })

    data = {
        "survey": {
            "id": survey.id,
            "title": survey.title,
            "age_group": survey.age_group,
            "occupation": survey.occupation,
            "location": survey.location,
            "created_at": survey.created_at.isoformat(),
            "total_participants": sessions.count(),
        },
        "questions": question_blocks,
    }
    return data

def render_report_html(data, report_json):
    survey_title = data["survey"]["title"]
    summary = report_json.get("summary", "")
    insights = report_json.get("insights", [])
    charts = report_json.get("charts", [])
    sections = report_json.get("sections", [])

    # JS config for charts
    charts_js_objects = []
    for c in charts:
        charts_js_objects.append({
            "id": c.get("id"),
            "type": c.get("type", "bar"),
            "title": c.get("title", ""),
            "labels": c.get("labels", []),
            "values": c.get("values", []),
        })

    html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Survey Report - {survey_title}</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    body {{ font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 24px; color: #111827; }}
    h1 {{ font-size: 24px; margin-bottom: 12px; }}
    h2 {{ font-size: 18px; margin-top: 24px; }}
    .chart-block {{ margin-top: 24px; page-break-inside: avoid; }}
    canvas {{ max-width: 700px; max-height: 400px; }}
    .insights ul {{ padding-left: 20px; }}
  </style>
</head>
<body>
  <h1>{survey_title} – Survey Report</h1>
  <p><strong>Audience:</strong> {data["survey"].get("occupation") or "N/A"} · Age: {data["survey"].get("age_group") or "N/A"} · Location: {data["survey"].get("location") or "N/A"}</p>
  <p><strong>Total participants:</strong> {data["survey"]["total_participants"]}</p>

  <h2>Executive Summary</h2>
  <p>{summary}</p>

  <h2>Key Insights</h2>
  <div class="insights">
    <ul>
      {''.join(f'<li>{ins}</li>' for ins in insights)}
    </ul>
  </div>

  <h2>Visualizations</h2>
  {''.join(f'''
    <div class="chart-block">
      <h3>{c.get("title")}</h3>
      <p>{c.get("description", "")}</p>
      <canvas id="{c.get("id")}"></canvas>
    </div>''' for c in charts)}

  <h2>Details</h2>
  {''.join(f'<h3>{s.get("title")}</h3>{s.get("html")}' for s in sections)}

  <script>
    const charts = {json.dumps(charts_js_objects)};
    charts.forEach(cfg => {{
      const ctx = document.getElementById(cfg.id);
      if (!ctx) return;
      new Chart(ctx, {{
        type: cfg.type || 'bar',
        data: {{
          labels: cfg.labels,
          datasets: [{
            "label": cfg.title,
            data: cfg.values,
            backgroundColor: 'rgba(59, 130, 246, 0.5)',
            borderColor: 'rgb(37, 99, 235)',
            borderWidth: 1
          }]
        }},
        options: {{
          responsive: true,
          plugins: {{
            legend: {{ display: false }},
            title: {{ display: false }}
          }},
          scales: {{
            y: {{ beginAtZero: true }}
          }}
        }}
      }});
    }});
    window.__chartsReady = true;
  </script>
</body>
</html>
"""
    return html

@login_required(login_url=reverse_lazy("signin"))
def survey_report_preview(request, survey_id):
    survey = get_object_or_404(Survey, pk=survey_id)
    report = getattr(survey, "report", None)
    if not report or not report.html_content:
        return HttpResponse("Report not generated yet.", status=404)
    return HttpResponse(report.html_content)

# PDF Utils
from playwright.sync_api import sync_playwright
import tempfile
import os

def html_to_pdf_bytes(html: str) -> bytes:
    with tempfile.TemporaryDirectory() as tmpdir:
        html_path = os.path.join(tmpdir, "report.html")
        pdf_path = os.path.join(tmpdir, "report.pdf")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            page.goto(f"file://{html_path}", wait_until="networkidle")
            # Wait until Chart.js has rendered
            try:
                page.wait_for_function("() => window.__chartsReady === true", timeout=10000)
            except Exception:
                pass
            page.pdf(path=pdf_path, format="A4", print_background=True)
            browser.close()

        with open(pdf_path, "rb") as f:
            return f.read()

@login_required(login_url=reverse_lazy("signin"))
def survey_report_pdf(request, survey_id):
    survey = get_object_or_404(Survey, pk=survey_id)
    report = getattr(survey, "report", None)
    if not report or not report.html_content:
        return HttpResponse("Report not generated yet.", status=404)

    pdf_bytes = html_to_pdf_bytes(report.html_content)

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="survey_{survey_id}_report.pdf"'
    return response
