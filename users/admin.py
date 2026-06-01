from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["username", "full_name", "role", "phone", "is_active"]
    list_filter = ["role", "is_active", "is_staff"]
    search_fields = ["username", "first_name", "last_name", "middle_name", "phone"]
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Дополнительно", {"fields": ("middle_name", "phone", "role")}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Дополнительно", {"fields": ("middle_name", "phone", "role")}),
    )
