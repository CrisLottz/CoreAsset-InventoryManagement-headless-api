from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Configuración visual del modelo User en el panel de administración.
    Extendemos UserAdmin nativo para mantener el hash de contraseñas 
    y agregamos nuestros campos personalizados.
    """
    # Columnas que se verán en la tabla principal
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_mfa_enabled', 'is_staff')
    
    # Filtros laterales
    list_filter = ('is_mfa_enabled', 'is_staff', 'is_superuser', 'is_active')
    
    # Agrupación de campos al editar un usuario
    fieldsets = UserAdmin.fieldsets + (
        ('Seguridad Avanzada', {'fields': ('is_mfa_enabled',)}),
    )