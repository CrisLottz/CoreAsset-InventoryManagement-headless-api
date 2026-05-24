from django.contrib import admin
from .models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    # Bloqueamos la creación y edición manual. Un log NUNCA debe ser alterado por un humano.
    def has_add_permission(self, request):
        return False
        
    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False # Nadie, ni el superadmin, puede borrar la evidencia

    list_display = ('action', 'entity_type', 'actor', 'ip_address', 'created_at')
    list_filter = ('action', 'entity_type', 'created_at')
    search_fields = ('actor__username', 'entity_id', 'ip_address')
    readonly_fields = [f.name for f in AuditLog._meta.fields] # Todo es de solo lectura