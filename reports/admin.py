from django.contrib import admin
from .models import UserProfile, Complaint, Feedback

admin.site.register(UserProfile)
admin.site.register(Complaint)
admin.site.register(Feedback)