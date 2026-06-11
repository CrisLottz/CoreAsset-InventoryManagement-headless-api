from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid

class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    is_mfa_enabled = models.BooleanField(default=False)
    
    # IAM Link: Conecta la credencial de acceso con la persona física
    employee = models.OneToOneField(
        'employees.Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='platform_user'
    )

    assigned_locations = models.ManyToManyField(
        'assets.Location',
        blank=True,
        related_name='managers',
        help_text=_("Locations this user can manage.")
    )

    class Meta:
        db_table = 'auth_user'