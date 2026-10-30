import random
import time

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.mail import send_mail
from .models import UserProfile, Complaint, ComplaintPhoto, Feedback
from .email_service import send_login_otp_resend

# =========================================================
# HOME
# =========================================================

def home(request):
    return render(request, "login.html")


# =========================================================
# USER LOGIN + EMAIL OTP
# =========================================================

def user_login(request):

    if request.method == "POST":

        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")

        # Authenticate username + password
        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is None:

            return render(request, "user_login.html", {
                "error": "Invalid username or password."
            })

        # Check email
        if user.email.lower() != email.lower():

            return render(request, "user_login.html", {
                "error": "Invalid email address."
            })

        last_otp_time = request.session.get("last_otp_time")

        if last_otp_time:

             if time.time() - last_otp_time < 60:

                 return render(request, "user_login.html", {

                     "error": "Please wait 60 seconds before requesting another OTP."

                     })

        

        # Generate 6 digit OTP
        otp = str(random.randint(100000, 999999))
        

        # Store OTP in session
        request.session["login_otp"] = otp
        request.session["login_user_id"] = user.id
        request.session["otp_time"] = time.time()
        request.session["otp_attempts"] = 0
        request.session["last_otp_time"] = time.time()

        # Send OTP (Resend with SMTP fallback)
        email_result = send_login_otp_resend(user.email, otp, is_admin=False)
        if not email_result["success"]:
            return render(request, "user_login.html", {
                "error": email_result["error"]
            })

        return redirect("verify_otp")



    return render(request, "user_login.html")


# =========================================================
# OTP VERIFICATION
# =========================================================

def verify_otp(request):

    if request.method == "POST":

        entered_otp = request.POST.get("otp", "").strip()

        saved_otp = request.session.get("login_otp")
        user_id = request.session.get("login_user_id")
        otp_time = request.session.get("otp_time")

        # Wrong OTP attempts
        otp_attempts = request.session.get(
            "otp_attempts",
            0
        )

        # OTP session missing
        if not saved_otp or not user_id or not otp_time:

            return render(request, "verify_otp.html", {
                "error": "OTP expired. Please login again."
            })

        # OTP expired after 5 minutes
        if time.time() - otp_time > 300:

            request.session.pop("login_otp", None)
            request.session.pop("login_user_id", None)
            request.session.pop("otp_time", None)
            request.session.pop("otp_attempts", None)

            return render(request, "verify_otp.html", {
                "error": "OTP expired. Please login again."
            })

        # Wrong OTP
        if entered_otp != saved_otp:

            otp_attempts += 1

            request.session["otp_attempts"] = otp_attempts

            # Maximum 3 attempts
            if otp_attempts >= 3:

                request.session.pop("login_otp", None)
                request.session.pop("login_user_id", None)
                request.session.pop("otp_time", None)
                request.session.pop("otp_attempts", None)

                return render(request, "verify_otp.html", {
                    "error": "Too many incorrect attempts. Please login again."
                })

            remaining = 3 - otp_attempts

            return render(request, "verify_otp.html", {
                "error": f"Incorrect OTP. {remaining} attempts remaining."
            })

        # Get user
        try:

            user = User.objects.get(
                id=user_id
            )

        except User.DoesNotExist:

            return render(request, "verify_otp.html", {
                "error": "Invalid login information."
            })

        # Login
        login(request, user)

        # Clear OTP session
        request.session.pop("login_otp", None)
        request.session.pop("login_user_id", None)
        request.session.pop("otp_time", None)
        request.session.pop("otp_attempts", None)

        return redirect("user_dashboard")

    return render(request, "verify_otp.html")

# =========================================================
# ADMIN LOGIN
# =========================================================


def admin_login(request):

    if request.method == "POST":

        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")

        # Authenticate username + password
        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is None:

            return render(request, "admin_login.html", {
                "error": "Invalid admin username or password."
            })

        # Check email
        if user.email.lower() != email.lower():

            return render(request, "admin_login.html", {
                "error": "Invalid admin email address."
            })

        # Check Admin role
        try:

            profile = UserProfile.objects.get(
                user=user
            )

        except UserProfile.DoesNotExist:

            return render(request, "admin_login.html", {
                "error": "This account is not an admin account."
            })

        if profile.role != "admin":

            return render(request, "admin_login.html", {
                "error": "This account is not an admin account."
            })

        # OTP resend protection
        last_otp_time = request.session.get(
            "admin_last_otp_time"
        )

        if last_otp_time:

            if time.time() - last_otp_time < 60:

                return render(request, "admin_login.html", {
                    "error": "Please wait 60 seconds before requesting another OTP."
                })

        # Generate 6 digit OTP
        otp = str(
            random.randint(100000, 999999)
        )

        # Store OTP in session
        request.session["admin_login_otp"] = otp
        request.session["admin_login_user_id"] = user.id
        request.session["admin_otp_time"] = time.time()
        request.session["admin_otp_attempts"] = 0
        request.session["admin_last_otp_time"] = time.time()

        # Send OTP (Resend with SMTP fallback)
        email_result = send_login_otp_resend(user.email, otp, is_admin=True)
        if not email_result["success"]:
            return render(request, "admin_login.html", {
                "error": email_result["error"]
            })

        return redirect("admin_verify_otp")



    return render(request, "admin_login.html")


def admin_verify_otp(request):

    if request.method == "POST":

        entered_otp = request.POST.get("otp", "").strip()

        saved_otp = request.session.get("admin_login_otp")
        user_id = request.session.get("admin_login_user_id")

        if entered_otp == saved_otp:

            user = User.objects.get(id=user_id)

            login(request, user)

            request.session.pop("admin_login_otp", None)
            request.session.pop("admin_login_user_id", None)
            request.session.pop("admin_otp_time", None)
            request.session.pop("admin_otp_attempts", None)
            request.session.pop("admin_last_otp_time", None)

            return redirect("admin_dashboard")

        return render(request, "admin_verify_otp.html", {
            "error": "Invalid OTP"
        })

    return render(request, "admin_verify_otp.html")

# =========================================================
# USER DASHBOARD
# =========================================================

@login_required(login_url="/user-login/")
def user_dashboard(request):

    complaints = Complaint.objects.filter(
        user=request.user
    ).order_by("-created_at")

    total_complaints = complaints.count()

    in_progress = complaints.filter(
        status="in_progress"
    ).count()

    resolved = complaints.filter(
        status="resolved"
    ).count()

    community_reports = Complaint.objects.exclude(
        user=request.user
    ).count()

    map_complaints = list(
        Complaint.objects.exclude(
            latitude__isnull=True
        ).exclude(
            longitude__isnull=True
        ).values(
            "id",
            "title",
            "category",
            "description",
            "status",
            "latitude",
            "longitude"
        )
    )

    return render(request, "user_dashboard.html", {
        "complaints": complaints,
        "total_complaints": total_complaints,
        "in_progress": in_progress,
        "resolved": resolved,
        "community_reports": community_reports,
        "map_complaints": map_complaints,
    })


# =========================================================
# ADMIN DASHBOARD
# =========================================================


@login_required(login_url="/admin-login/")
def admin_dashboard(request):

    filter_status = request.GET.get("status")

    # ALL USERS ki complaints
    complaints = Complaint.objects.select_related(
    "user"
).prefetch_related(
    "photos"
).all().order_by("-created_at")

    # Status ke according ALL USERS ki complaints
    if filter_status in [
        "pending",
        "in_progress",
        "resolved"
    ]:
        complaints = complaints.filter(
            status=filter_status
        )

    # Counts
    total_complaints = Complaint.objects.count()

    pending = Complaint.objects.filter(
        status="pending"
    ).count()

    in_progress = Complaint.objects.filter(
        status="in_progress"
    ).count()

    resolved = Complaint.objects.filter(
        status="resolved"
    ).count()

    # Map complaints
    map_complaints = list(
        Complaint.objects.exclude(
            latitude__isnull=True
        ).exclude(
            longitude__isnull=True
        ).values(
            "id",
            "title",
            "category",
            "description",
            "status",
            "latitude",
            "longitude"
        )
    )

    return render(request, "admin_dashboard.html", {
        "complaints": complaints,
        "total_complaints": total_complaints,
        "pending": pending,
        "in_progress": in_progress,
        "resolved": resolved,
        "map_complaints": map_complaints,
        "filter_status": filter_status,
    })


def admin_create_account(request):

    if request.method == "POST":

        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if password != confirm_password:
            return render(request, "admin_create_account.html", {
                "error": "Passwords do not match."
            })

        if User.objects.filter(username=username).exists():
            return render(request, "admin_create_account.html", {
                "error": "Username already exists."
            })

        if User.objects.filter(email=email).exists():
            return render(request, "admin_create_account.html", {
                "error": "Email already registered."
            })

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        UserProfile.objects.create(
            user=user,
            role="admin"
        )

        return redirect("admin_login")

    return render(request, "admin_create_account.html")


# =========================================================
# CREATE ACCOUNT
# =========================================================

def create_account(request):

    if request.method == "POST":

        username = request.POST.get(
            "username",
            ""
        ).strip()

        email = request.POST.get(
            "email",
            ""
        ).strip()

        password = request.POST.get(
            "password",
            ""
        )

        # Username check
        if User.objects.filter(
            username=username
        ).exists():

            return render(request, "create_account.html", {
                "error": "Username already exists."
            })

        # Email check
        if User.objects.filter(
            email=email
        ).exists():

            return render(request, "create_account.html", {
                "error": "Email already registered."
            })

        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        # Create citizen profile
        UserProfile.objects.create(
            user=user,
            role="user"
        )

        return redirect("user_login")

    return render(request, "create_account.html")


# =========================================================
# REPORT ISSUE
# =========================================================

@login_required(login_url="/user-login/")
def report_issue(request):

    if request.method == "POST":

        photos = request.FILES.getlist("photos")

        # Maximum 3 photos
        if len(photos) > 3:
            return render(request, "report_issue.html", {
                "error": "You can upload maximum 3 photos."
            })

        complaint = Complaint.objects.create(
            user=request.user,

            title=request.POST.get(
                "title",
                ""
            ).strip(),

            category=request.POST.get(
                "category",
                ""
            ),

            description=request.POST.get(
                "description",
                ""
            ).strip(),

            latitude=request.POST.get(
                "latitude"
            ) or None,

            longitude=request.POST.get(
                "longitude"
            ) or None,

            address=request.POST.get(
                "address",
                ""
            ).strip(),

            status="pending",
        )

        # Save uploaded photos
        for photo in photos:

            ComplaintPhoto.objects.create(
                complaint=complaint,
                image=photo
            )

        return redirect("my_complaints")
    
    return render(
        request,
        "report_issue.html"
    )


# =========================================================
# UPDATE COMPLAINT STATUS
# =========================================================

@login_required(login_url="/admin-login/")
def update_complaint_status(request, complaint_id):

    if request.method == "POST":

        complaint = get_object_or_404(
            Complaint,
            id=complaint_id
        )

        new_status = request.POST.get("status")

        allowed_statuses = [
            "pending",
            "in_progress",
            "resolved"
        ]

        if new_status in allowed_statuses:

            complaint.status = new_status
            complaint.save()

        return redirect("manage_complaints")

    return redirect("manage_complaints")


# =========================================================
# MY COMPLAINTS
# =========================================================

@login_required(login_url="/user-login/")
def my_complaints(request):

    complaints = Complaint.objects.filter(
        user=request.user
    ).prefetch_related(
        "photos"
    ).order_by("-created_at")

    return render(
        request,
        "my_complaints.html",
        {
            "complaints": complaints
        }
    )

# =========================================================
# USER PROFILE
# =========================================================

@login_required(login_url="/user-login/")
def user_profile(request):

    return render(
        request,
        "user_profile.html"
    )


# =========================================================
# ADMIN PROFILE
# =========================================================

@login_required(login_url="/admin-login/")
def admin_profile(request):

    if request.method == "POST":

        request.user.first_name = request.POST.get(
            "first_name",
            ""
        ).strip()

        request.user.last_name = request.POST.get(
            "last_name",
            ""
        ).strip()

        request.user.email = request.POST.get(
            "email",
            ""
        ).strip()

        request.user.save()

        return redirect("admin_profile")

    return render(
        request,
        "admin_profile.html",
        {
            "admin": request.user
        }
    )


# =========================================================
# MANAGE COMPLAINTS
# =========================================================

@login_required(login_url="/admin-login/")
def manage_complaints(request):

    complaints = Complaint.objects.all().order_by(
        "-created_at"
    )

    return render(
        request,
        "manage_complaints.html",
        {
            "complaints": complaints
        }
    )


# =========================================================
# LOGOUT
# =========================================================

def user_logout(request):

    logout(request)

    return redirect("home")


# =========================================================
# COMPLAINT LIST
# =========================================================

@login_required(login_url="/admin-login/")
def complaint_list(request, status=None):

    complaints = Complaint.objects.select_related(
        "user"
    ).prefetch_related(
        "photos"
    ).order_by("-created_at")

    if status:
        complaints = complaints.filter(
            status=status
        )

    return render(request, "complaint_list.html", {

        "complaints": complaints,

        "page_title": {

            None: "All Complaints",

            "pending":
                "Pending Issues",

            "in_progress":
                "In Progress",

            "resolved":
                "Resolved Issues",

        }.get(
            status,
            "Complaints"
        ),

        "filter_status": status,

    })


# =========================================================
# GIVE FEEDBACK
# =========================================================

@login_required(login_url="/user-login/")
def give_feedback(request, complaint_id):

    complaint = get_object_or_404(
        Complaint,
        id=complaint_id,
        user=request.user,
        status="resolved"
    )

    if request.method == "POST":

        rating = request.POST.get(
            "rating"
        )

        feedback_text = request.POST.get(
            "feedback",
            ""
        )

        tags = request.POST.getlist(
            "tags"
        )

        tags_text = ", ".join(tags)

        if rating:

            Feedback.objects.update_or_create(

                complaint=complaint,

                defaults={

                    "user": request.user,

                    "rating": int(rating),

                    "feedback": feedback_text,

                    "tags": tags_text,
                }
            )

            return redirect(
                "my_complaints"
            )

    return render(
        request,
        "feedback.html",
        {
            "complaint": complaint
        }
    )


# =========================================================
# ADMIN FEEDBACK
# =========================================================

@login_required(login_url="/admin-login/")
def admin_feedback(request):

    feedbacks = Feedback.objects.select_related(
        "user",
        "complaint"
    ).order_by("-created_at")

    return render(
        request,
        "admin_feedback.html",
        {
            "feedbacks": feedbacks
        }
    )