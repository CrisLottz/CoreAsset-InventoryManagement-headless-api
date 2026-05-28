from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # 1. Inyectamos una nueva sección en la pantalla de edición del usuario
    fieldsets = UserAdmin.fieldsets + (
        ('Privilegios y Acceso (White-Label)', {
            'fields': ('assigned_locations', 'is_mfa_enabled')
        }),
    )
    
    # 2. Mostramos el estado del MFA en la tabla principal
    list_display = ['username', 'email', 'is_staff', 'is_mfa_enabled']
    
    # 3. CRÍTICO: Transforma la selección de múltiples sedes en un widget 
    # visual de dos columnas mucho más profesional que un simple multiselect.
    filter_horizontal = UserAdmin.filter_horizontal + ('assigned_locations',)