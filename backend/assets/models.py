from django.db import models
from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.utils.translation import gettext_lazy as _
import uuid

class Location(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Asset(models.Model):
    STATUS_CHOICES = [
        ('ACTIVE', _('Operativo')),
        ('MAINTENANCE', _('En Mantenimiento')),
        ('RETIRED', _('De Baja / Descartado')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    internal_tag = models.CharField(max_length=50, unique=True)
    location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name='assets')
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_assets'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    metadata_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['location', 'status']),
            models.Index(fields=['internal_tag']),
            GinIndex(fields=['metadata_json']),
        ]

        permissions = [
            ("view_global_inventory", "Puede ver activos de TODAS las sedes"),
            ("manage_global_inventory", "Puede editar/borrar activos de TODAS las sedes"),
        ]

    def __str__(self):
        return f"{self.internal_tag} - {self.status}"