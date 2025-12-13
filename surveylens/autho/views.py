from django.shortcuts import render
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password
# from .models import PublicUser
from django.http import JsonResponse

# 👉 Signup Page + User Creation
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Q
from .models import Public_user, TAMIL_NADU_DISTRICTS
from django.http import HttpResponse
from django.urls import reverse

from django.shortcuts import render, redirect
from django.urls import reverse

def index(request):
    # Debug prints (optional)
    print("Authenticated:", request.user.is_authenticated)
    print("Has public_user_profile:", hasattr(request.user, "public_user_profile"))

    # If user is not logged in, show signup page
    if not request.user.is_authenticated:
        return redirect("signin")

    # If user has a public_user_profile → redirect to public user page
    if hasattr(request.user, "public_user_profile"):
        return redirect(reverse("public_dashboard"))

    # Otherwise → this is an admin, go to admin home
    return redirect(reverse("welcome"))


def signin_page(request):
    # Redirect authenticated users appropriately

    
    
    # Handle unauthenticated users only
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        
        if user is None:
            return JsonResponse({
                "status": "error",
                "message": "Invalid username or password!"
            })
        
        login(request, user)
        
        if user.is_superuser:
            return JsonResponse({
                "status": "success",
                "message": "Login successful!",
                "redirect": "admin_page"
            })
        
        return JsonResponse({
            "status": "success",
            "message": "Login successful!",
            "redirect": "dashboard"
        })
    
    # Render login form for GET requests (unauthenticated only)
    return render(request, "signin.html")




def signup_page(request):
    if request.method == "POST":

        # Check if request is AJAX
        if request.headers.get("x-requested-with") == "XMLHttpRequest":

            name = request.POST.get("name")
            username = request.POST.get("username")
            email = request.POST.get("email")
            password = request.POST.get("password")
            occupation = request.POST.get("occupation")
            dob = request.POST.get("dob")
            age = request.POST.get("age")
            phone = request.POST.get("phone")
            address = request.POST.get("address")
            district = request.POST.get("district")

            # Check duplicates (email & username)
            if User.objects.filter(Q(email=email) | Q(username=username)).exists():
                return JsonResponse({
                    "status": "error",
                    "message": "Email or Username already exists!"
                })

            # Create base user
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=name,
                password=password
            )

            # Create public user profile
            Public_user.objects.create(
                user=user,
                name=name,
                occupation=occupation,
                dob=dob,
                age=age,
                phone=phone,
                address=address,
                district=district
            )

            return JsonResponse({
                "status": "success",
                "message": "Account created successfully!",
                "redirect_url": "/signin/"
            })

    return render(request, "signup.html", {"districts": TAMIL_NADU_DISTRICTS})

def admin_page(request):
	return HttpResponse("Admin Dashboard - Under Construction")

def dashboard(request):
	return HttpResponse("User Dashboard - Under Construction")

