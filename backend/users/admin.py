from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):

    fieldsets = UserAdmin.fieldsets + (
        ('Privilegios y Acceso (White-Label)', {
            'fields': ('assigned_locations', 'is_mfa_enabled')
        }),
    )


    list_display = ['username', 'email', 'is_staff', 'is_mfa_enabled']



    filter_horizontal = UserAdmin.filter_horizontal + ('assigned_locations',)