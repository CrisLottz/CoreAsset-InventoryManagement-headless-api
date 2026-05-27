from django.db import models
from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
import uuid

class Location(models.Model):
    """
    Entidad White-Label para agrupar activos físicamente o lógicamente.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Asset(models.Model):
    """
    Tronco común del inventario. Utiliza JSONField para flexibilidad extrema.
    """
    STATUS_CHOICES = [
        ('ACTIVE', 'Operativo'),
        ('MAINTENANCE', 'En Mantenimiento'),
        ('RETIRED', 'De Baja / Descartado'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Etiqueta física de inventario (Ej. CLF-2026-001)
    internal_tag = models.CharField(max_length=50, unique=True) 
    
    # Integridad Referencial Estricta: PROTECT impide borrar una sede si tiene activos vinculados
    location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name='assets')
    
    # SET_NULL permite que un empleado sea eliminado de la empresa sin que el activo desaparezca
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='assigned_assets'
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    
    # Columna flexible para características dinámicas (MAC, expiración de licencias, etc.)
    metadata_json = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Optimización de consultas recurrentes a nivel de motor DB
        indexes = [
            models.Index(fields=['location', 'status']),
            models.Index(fields=['internal_tag']),
            GinIndex(fields=['metadata_json']), 
        ]

    def __str__(self):
        return f"{self.internal_tag} - {self.status}"