from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Role
from .serializers import RoleSerializer

class RoleViewSet(viewsets.ModelViewSet):
    """
    Gestor del ciclo de vida de los Roles.
    Permite crear roles (ej. 'Administrador IT', 'Recursos Humanos').
    """
    queryset = Role.objects.all().order_by('name')
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated]