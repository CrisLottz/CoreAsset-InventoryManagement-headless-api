from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid

class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    is_mfa_enabled = models.BooleanField(default=False)
    
    # Vinculación White-Label para la gestión de sucursales (Object-Level Permissions)
    assigned_locations = models.ManyToManyField(
        'assets.Location',
        blank=True,
        related_name='managers',
        help_text="Sedes que este usuario puede administrar."
    )

    class Meta:
        db_table = 'auth_user'