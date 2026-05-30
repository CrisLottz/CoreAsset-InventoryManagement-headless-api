from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.exceptions import PermissionDenied
from django.core.cache import cache
from django.conf import settings
from .models import Location, Asset
from .serializers import LocationSerializer, AssetSerializer
from .permissions import IsLocationManagerStrict

class LocationViewSet(viewsets.ModelViewSet):
    queryset = Location.objects.all().order_by('name')
    serializer_class = LocationSerializer
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



        if not user.is_superuser and not user.has_perm('assets.view_global_inventory'):
            queryset = queryset.filter(location__in=user.assigned_locations.all())


        location_id = self.request.query_params.get('location_id')
        if location_id:
            queryset = queryset.filter(location_id=location_id)

        return queryset

    def list(self, request, *args, **kwargs):
        """
        Intercepta la petición GET. Sirve desde Redis si existe,
        de lo contrario consulta a PostgreSQL y guarda el resultado.
        """
        location_id = request.query_params.get('location_id', 'all')
        cache_key = f"inventory_user_{request.user.id}_loc_{location_id}"

        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)

        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response_data = self.get_paginated_response(serializer.data).data
        else:
            serializer = self.get_serializer(queryset, many=True)
            response_data = serializer.data


        cache.set(cache_key, response_data, timeout=getattr(settings, 'CACHE_TTL', 900))

        return Response(response_data)

    def _invalidate_user_cache(self):
        """
        Borra todas las llaves de Redis asociadas a este usuario.
        """
        pattern = f"inventory_user_{self.request.user.id}_*"
        cache.delete_pattern(pattern)

    def perform_create(self, serializer):
        user = self.request.user
        location = serializer.validated_data['location']

        if not user.is_superuser and not user.has_perm('assets.manage_global_inventory'):
            if not user.assigned_locations.filter(id=location.id).exists():
                raise PermissionDenied("El Rol actual no autoriza la creación de activos en esta sede.")

        serializer.save()
        self._invalidate_user_cache()

    def perform_update(self, serializer):
        serializer.save()
        self._invalidate_user_cache()

    def perform_destroy(self, instance):
        instance.delete()
        self._invalidate_user_cache()