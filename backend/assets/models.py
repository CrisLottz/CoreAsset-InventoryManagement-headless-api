from django.db import models
from django.contrib.postgres.indexes import GinIndex
from django.utils.translation import gettext_lazy as _
import uuid

# ---------------------------------------------------------
# 1. HARD ENTITIES (Integridad Referencial)
# ---------------------------------------------------------
class Location(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

# ---------------------------------------------------------
# 2. CATEGORY ENGINE (El Module Builder SaaS)
# ---------------------------------------------------------
class AssetCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    icon = models.CharField(max_length=50, help_text=_("Frontend icon identifier"))
    is_system_default = models.BooleanField(default=False, help_text=_("Prevents deletion of default modules"))
    is_hidden = models.BooleanField(default=False)
    display_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name

class CategoryField(models.Model):
    FIELD_TYPES = [
        ('TEXT', _('Short Text')),
        ('LONG_TEXT', _('Long Text')),
        ('NUMBER', _('Number')),
        ('DROPDOWN', _('Select Option')),
        ('COLOR_STATUS', _('Status Label')),
        ('EMPLOYEE', _('Employee Lookup')),
        ('LOCATION', _('Location Lookup')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(AssetCategory, on_delete=models.CASCADE, related_name='fields')
    name = models.CharField(max_length=100)
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES)
    is_required = models.BooleanField(default=False)
    is_locked = models.BooleanField(default=False, help_text=_("System fields cannot be modified/deleted"))
    options_metadata = models.JSONField(default=list, blank=True, help_text=_("JSON array for dropdown/color options"))
    
    class Meta:
        unique_together = ('category', 'name')
    
    def __str__(self):
        return f"{self.category.name} - {self.name} ({self.field_type})"

# ---------------------------------------------------------
# 3. POLYMORPHIC ASSET (Motor Híbrido)
# ---------------------------------------------------------
class Asset(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    internal_tag = models.CharField(max_length=50, unique=True)
    category = models.ForeignKey(AssetCategory, on_delete=models.PROTECT, related_name='assets')
    
    # HARD COLUMNS (Para filtrado ultra-rápido y cascadas del ORM)
    location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name='assets', null=True, blank=True)
    assigned_to = models.ForeignKey(
        'employees.Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_assets'
    )
    
    # DYNAMIC DATA (Para cualquier campo creado por el usuario en CategoryField)
    dynamic_data = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['location', 'category']),
            models.Index(fields=['internal_tag']),
            GinIndex(fields=['dynamic_data']),
        ]

        permissions = [
            ("view_global_inventory", _("Can view assets across all locations")),
            ("manage_global_inventory", _("Can manage assets across all locations")),
        ]

    def __str__(self):
        return f"{self.internal_tag} ({self.category.name})"
    

class UserTablePreference(models.Model):
    user = models.ForeignKey(
        'users.User', 
        on_delete=models.CASCADE, 
        related_name='table_preferences'
    )
    category = models.ForeignKey(
        'AssetCategory', 
        on_delete=models.CASCADE, 
        related_name='user_preferences'
    )
    # Almacena una lista ordenada: [{"name": "Status", "is_visible": True, "order": 0}]
    columns_config = models.JSONField(default=list)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'asset_user_table_preferences'
        unique_together = ('user', 'category') # Un usuario solo tiene una configuración por categoría

    def __str__(self):
        return f"{self.user.email} - {self.category.name} Preference"    