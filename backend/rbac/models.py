from django.db import models
from django.contrib.auth.models import Group

class Role(Group):
    """
    Proxy Model que adapta el modelo nativo 'Group' de Django
    a la semántica de negocio 'Role' (RBAC).
    No crea una tabla nueva en PostgreSQL (usa auth_group).
    """

    class Meta:
        proxy = True
        app_label = 'rbac'
        verbose_name = 'Role'
        verbose_name_plural = 'Roles'