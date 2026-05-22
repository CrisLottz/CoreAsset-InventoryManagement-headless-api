import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    """
    Modelo core de usuario para el sistema RBAC e Inventario.
    Al heredar de AbstractUser, Django inyecta automáticamente:
    username, first_name, last_name, email, password, is_active, date_joined, etc.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    is_mfa_enabled = models.BooleanField(default=False, help_text="Indica si el usuario tiene MFA activo.")

    class Meta:
        db_table = 'USERS'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f"{self.username} ({self.email})"