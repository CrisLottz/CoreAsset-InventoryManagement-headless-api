import uuid
from django.db import models
from django.conf import settings

class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Integridad referencial estricta: si un usuario se elimina, sus logs permanecen inmutables
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT, 
        related_name='audit_logs'
    )
    
    action = models.CharField(max_length=50)         # Ej: 'CREATE', 'UPDATE', 'DELETE'
    entity_type = models.CharField(max_length=100)    # Ej: 'User', 'Asset', 'License'
    entity_id = models.UUIDField()
    
    # Campo JSONB nativo de PostgreSQL para almacenar estructuras de datos variables
    metadata_json = models.JSONField(default=dict)
    
    ip_address = models.GenericIPAddressField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audit_logs'
        ordering = ['-created_at']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'

    def __str__(self):
        return f"{self.action} - {self.entity_type} ({self.created_at})"