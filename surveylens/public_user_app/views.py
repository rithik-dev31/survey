from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.urls import reverse
from django.http import JsonResponse
import openai
import json
import os
from administator.models import UserSurveySession, UserSurveyAnswer


OPENAI_MODEL = "gpt-4.1-mini"
OPENAI_TEMPERATURE = 0.0
OPENAI_MAX_TOKENS = 500


def call_openai_chat(messages):
    """Call OpenAI API and return assistant response text."""
    try:
        response = openai.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=OPENAI_TEMPERATURE,
            max_tokens=OPENAI_MAX_TOKENS
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("OpenAI API error:", e)
        return "I am a SurveyLens AI for collecting survey responses. I cannot respond to that message."


@login_required
def public_dashboard(request):
    pending = UserSurveySession.objects.filter(user=request.user, is_completed=False)
    completed = UserSurveySession.objects.filter(user=request.user, is_completed=True)
    return render(request, "public-dashboard.html", {
        "pending_surveys": pending,
        "completed_surveys": completed,
    })


def user_logout(request):
    logout(request)
    return redirect(reverse("home"))


@login_required
def start_survey_chatbot(request, session_id):
    session = get_object_or_404(UserSurveySession, id=session_id, user=request.user)

    # Mark notification as seen
    if not session.is_notified:
        session.is_notified = True
        session.save()

    return render(request, "public-chatbot.html", {"session": session})
@login_required
def survey_answer_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    session_id = data.get("session_id")
    user_answer = data.get("answer")
    q_index = data.get("q_index")

    session = get_object_or_404(UserSurveySession, id=session_id, user=request.user)
    survey = session.survey
    questions = list(survey.surveyquestion_set.all())

    def prepare_bot_question_text(question_obj):
        base = question_obj.question_text or "Question"
        qtype = question_obj.question_type or "text"
        options = ""
        if question_obj.options:
            try:
                opts = json.loads(question_obj.options)
                if isinstance(opts, list) and opts:
                    options = " Options: " + ", ".join([str(o) for o in opts])
            except Exception:
                options = ""
        return f"{base}{options} (Answer type: {qtype})."

    # -------------------------
    # First load (q_index = -1) - RESUME LOGIC
    # -------------------------
    if q_index == -1:
        if not questions:
            session.is_completed = True
            session.save()
            return JsonResponse({"status": "completed", "message": "No questions available."})
        
        # ✅ RESUME from saved progress or start fresh
        resume_index = getattr(session, 'current_question_index', 0)
        
        if resume_index >= len(questions):
            session.is_completed = True
            session.save()
            return JsonResponse({
                "status": "completed", 
                "bot_reply": "Thank you! You already completed this survey.",
                "message": "Survey already completed."
            })
        
        current_q = questions[resume_index]
        
        messages = [
            {
                "role": "system",
                "content": (
                    "You are SurveyLens AI. Your only purpose is to collect survey responses clearly and politely. "
                    "Always respond in a friendly tone. Keep responses short. "
                    "When the user writes in any language, always respond in that same language. "
                    "Do not translate or change language unless the user clearly asks."
                )
            },
            {
                "role": "user",
                "content": (
                    f"Ask this survey question in a friendly, conversational way: "
                    f"{prepare_bot_question_text(current_q)}"
                )
            }
        ]

        bot_text = call_openai_chat(messages)
        return JsonResponse({
            "status": "next",
            "bot_reply": bot_text or "Please answer the question above.",
            "next_question": current_q.question_text,
            "question_type": current_q.question_type,
            "options": json.loads(current_q.options) if current_q.options else [],
            "q_index": resume_index  # ✅ Start from saved index
        })

    # -------------------------
    # Validate q_index with resume support
    # -------------------------
    saved_index = getattr(session, 'current_question_index', 0)
    if q_index < saved_index or q_index >= len(questions):
        # Force resume to saved position if client sends invalid/old index
        q_index = saved_index
        if q_index >= len(questions):
            session.is_completed = True
            session.save()
            return JsonResponse({
                "status": "completed",
                "bot_reply": "Thank you! Survey already completed.",
                "message": "Already at end of survey."
            })
    
    current_question = questions[q_index]

    # -------------------------
    # No answer provided
    # -------------------------
    if user_answer is None or not str(user_answer).strip():
        messages = [
            {
                "role": "system",
                "content": (
                    "You are SurveyLens AI. Keep it short and friendly. "
                    "Always respond in the same language as the user's latest message."
                )
            },
            {
                "role": "user",
                "content": f"User didn't answer. Gently repeat this question: {current_question.question_text}"
            }
        ]
        bot_text = call_openai_chat(messages)
        return JsonResponse({
            "status": "next",
            "bot_reply": bot_text or "Please answer the question above.",
            "next_question": current_question.question_text,
            "question_type": current_question.question_type,
            "options": json.loads(current_question.options) if current_question.options else [],
            "q_index": q_index
        })

    # -------------------------
    # Advanced JSON Classification
    # -------------------------
    classification_system = (
        "You are a survey intent classifier. Analyze user responses and return ONLY valid JSON. "
        "Output format: {\"intent\": \"answer|survey_meta|unrelated\", "
        "\"reply\": \"short response\", "
        "\"language\": \"the exact name of the language of the user's message (e.g., English, Tamil, Hindi, Kannada)\", "
        "\"save_answer\": true|false}\n\n"
        "RULES:\n"
        "1. intent='answer' → User gave ANY kind of answer to the CURRENT question "
        "(including 'I don't know' or 'no idea') → save_answer=true.\n"
        "2. intent='survey_meta' → User asks about the survey itself (purpose, privacy, length) → save_answer=false.\n"
        "3. intent='unrelated' → Pure chit-chat/off-topic (e.g., 'what is your name', jokes) → save_answer=false, "
        "reply EXACTLY: \"I am a SurveyLens AI for collecting survey responses. I cannot respond to that message.\"\n\n"
        "You MUST detect the language of the latest user message and set the language field to that exact language name. "
        "When you generate 'reply', ALWAYS respond in the same language as the latest user message. "
        "Return JSON ONLY - no other text."
    )

    user_context = (
        f"Question: {current_question.question_text}\n"
        f"User said: {user_answer}\n"
        "Classify and respond:"
    )

    messages = [
        {"role": "system", "content": classification_system},
        {"role": "user", "content": user_context}
    ]

    classification_raw = call_openai_chat(messages)

    # Robust JSON parsing with fallback
    try:
        cleaned = classification_raw.strip()
        # Remove `````` wrappers if present
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            cleaned = cleaned.replace("json", "", 1).strip()
        classified = json.loads(cleaned)
        intent = classified.get("intent", "unrelated")
        bot_reply = classified.get("reply")
        lang = classified.get("language", "English")
        save_answer_flag = bool(classified.get("save_answer", False))
    except Exception as e:
        print(f"JSON Parse Error: {e}, raw: {classification_raw}")
        intent = "unrelated"
        bot_reply = "I am a SurveyLens AI for collecting survey responses. I cannot respond to that message."
        lang = "English"
        save_answer_flag = False

    # -------------------------
    # Handle intents
    # -------------------------
    if intent == "answer" and save_answer_flag:
        # Save answer and advance
        UserSurveyAnswer.objects.create(
            session=session,
            question=current_question,
            answer_text=user_answer
        )
        session.current_question_index = q_index + 1
        session.save()

        next_q_index = q_index + 1
        if next_q_index >= len(questions):
            session.is_completed = True
            session.save()
            closing_msg = "Thank you! Survey completed."
            try:
                close_messages = [
                    {
                        "role": "system",
                        "content": (
                            "You are SurveyLens AI. Say a brief thank-you message. "
                            "You MUST respond only in this language: " + lang + "."
                        )
                    },
                    {
                        "role": "user",
                        "content": "Say thank you for completing the survey."
                    }
                ]
                closing_msg = call_openai_chat(close_messages)
            except Exception as e:
                print("Closing message error:", e)
            return JsonResponse({
                "status": "completed",
                "bot_reply": closing_msg,
                "message": "Survey completed!"
            })
        else:
            # Next question – respond in same language as user's last answer
            next_q = questions[next_q_index]
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are SurveyLens AI. Ask the next survey question in a friendly, conversational way. "
                        "You MUST respond only in this language: " + lang + ". "
                        "Do not mix any other language, even if it appeared earlier in the conversation. "
                        "Keep the message short."
                    )
                },
                {
                    "role": "user",
                    "content": f"Ask this question: {prepare_bot_question_text(next_q)}"
                }
            ]
            next_bot_text = call_openai_chat(messages)
            return JsonResponse({
                "status": "next",
                "bot_reply": next_bot_text or "Please answer the question above.",
                "next_question": next_q.question_text,
                "question_type": next_q.question_type,
                "options": json.loads(next_q.options) if next_q.options else [],
                "q_index": next_q_index
            })

    elif intent == "survey_meta":
        # Meta questions: answer in same language as user
        if not bot_reply:
            bot_reply = "This survey helps improve services. Your answers are anonymous and secure."
        return JsonResponse({
            "status": "ok",
            "bot_reply": bot_reply,
            "q_index": q_index,
            "note": "survey_meta"
        })

    else:  # unrelated
        refusal = "I am a SurveyLens AI for collecting survey responses. I cannot respond to that message."
        return JsonResponse({
            "status": "ok",
            "bot_reply": refusal,
            "q_index": q_index,
            "note": "unrelated_or_refused"
        })
