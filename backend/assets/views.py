from rest_framework import viewsets
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.exceptions import PermissionDenied
from .models import Location, Asset
from .serializers import LocationSerializer, AssetSerializer
from .permissions import IsLocationManagerStrict

class LocationViewSet(viewsets.ModelViewSet):
    queryset = Location.objects.all().order_by('name')
    serializer_class = LocationSerializer
    # DjangoModelPermissions obliga a que el Rol tenga el check de 'view_location', 'add_location', etc.
    permission_classes = [DjangoModelPermissions, IsLocationManagerStrict]


class AssetViewSet(viewsets.ModelViewSet):
    serializer_class = AssetSerializer
    permission_classes = [DjangoModelPermissions, IsLocationManagerStrict]

    def get_queryset(self):
        """
        Filtra los resultados basándose en la matriz de permisos del Rol.
        """
        user = self.request.user
        queryset = Asset.objects.select_related('location', 'assigned_to').all().order_by('-created_at')

        # 1. Filtro de alcance (Scope): Si no es admin y NO tiene el permiso global, 
        # bloqueamos el queryset exclusivamente a las sedes que tiene asignadas.
        if not user.is_superuser and not user.has_perm('assets.view_global_inventory'):
            queryset = queryset.filter(location__in=user.assigned_locations.all())

        # 2. Filtros dinámicos por URL (Ej. ?location_id=uuid)
        location_id = self.request.query_params.get('location_id')
        if location_id:
            queryset = queryset.filter(location_id=location_id)

        return queryset

    def perform_create(self, serializer):
        """
        Auditoría de Creación: Bloquea intentos de inyectar activos en sedes 
        ajenas, incluso si el usuario tiene el permiso de 'add_asset'.
        """
        user = self.request.user
        location = serializer.validated_data['location']
        
        # Si no es superadmin ni tiene poder global, validamos su jurisdicción física
        if not user.is_superuser and not user.has_perm('assets.manage_global_inventory'):
            if not user.assigned_locations.filter(id=location.id).exists():
                raise PermissionDenied("El Rol actual no autoriza la creación de activos en esta sede.")
                
        serializer.save()