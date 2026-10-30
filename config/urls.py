from django.contrib import admin
from django.urls import path
from reports import views
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [

    path(
        'admin/',
        admin.site.urls
    ),

    path(
        '',
        views.home,
        name='home'
    ),

    path(
        'user-login/',
        views.user_login,
        name='user_login'
    ),

    path(
        'admin-login/',
        views.admin_login,
        name='admin_login'
    ),

    path(
        'user-dashboard/',
        views.user_dashboard,
        name='user_dashboard'
    ),

    path(
        'admin-dashboard/',
        views.admin_dashboard,
        name='admin_dashboard'
    ),

    path(
        'create-account/',
        views.create_account,
        name='create_account'
    ),

    path(
        'report-issue/',
        views.report_issue,
        name='report_issue'
    ),

    path(
        'update-complaint-status/<int:complaint_id>/',
        views.update_complaint_status,
        name='update_complaint_status'
    ),

    path(
        'my-complaints/',
        views.my_complaints,
        name='my_complaints'
    ),

    path(
        'manage-complaints/',
        views.manage_complaints,
        name='manage_complaints'
    ),

    path(
        'user-profile/',
        views.user_profile,
        name='user_profile'
    ),

    path(
        'admin-profile/',
        views.admin_profile,
        name='admin_profile'
    ),

    path(
        'logout/',
        views.user_logout,
        name='logout'
    ),

    path(
        'complaints/',
        views.complaint_list,
        name='all_complaints'
    ),

    path(
        'complaints/pending/',
        lambda request: views.complaint_list(
            request,
            'pending'
        ),
        name='pending_issues'
    ),

    path(
        'complaints/in-progress/',
        lambda request: views.complaint_list(
            request,
            'in_progress'
        ),
        name='in_progress_issues'
    ),

    path(
        'complaints/resolved/',
        lambda request: views.complaint_list(
            request,
            'resolved'
        ),
        name='resolved_issues'
    ),

    path(
        'feedback/<int:complaint_id>/',
        views.give_feedback,
        name='give_feedback'
    ),

    path(
        'admin-feedback/',
        views.admin_feedback,
        name='admin_feedback'
    ),

    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path(
    "admin-verify-otp/",
    views.admin_verify_otp,
    name="admin_verify_otp"
),
path(
    "admin-create-account/",
    views.admin_create_account,
    name="admin_create_account"
),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
