from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import Permission
from .models import Role
from .serializers import RoleSerializer, PermissionSerializer

class RoleViewSet(viewsets.ModelViewSet):
    """
    Gestor del ciclo de vida de los Roles.
    Permite crear roles (ej. 'Administrador IT', 'Recursos Humanos').
    """
    queryset = Role.objects.all().order_by('name')
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated]

class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Endpoint para consultar los permisos disponibles del sistema.
    """
    queryset = Permission.objects.select_related('content_type').all().order_by('content_type__app_label', 'content_type__model', 'codename')
    serializer_class = PermissionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None # Para devolver todos en una sola llamada y armar la matriz