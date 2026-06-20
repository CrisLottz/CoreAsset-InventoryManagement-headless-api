from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.exceptions import PermissionDenied
from django.core.cache import cache
from django.conf import settings

from .models import Location, AssetCategory, Asset
from .serializers import LocationSerializer, AssetCategorySerializer, AssetSerializer
from .permissions import IsLocationManagerStrict

class LocationViewSet(viewsets.ModelViewSet):
    queryset = Location.objects.all().order_by('name')
    serializer_class = LocationSerializer
    permission_classes = [DjangoModelPermissions, IsLocationManagerStrict]

class CategoryStructureViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Endpoint White-Label. Despacha la configuración de módulos activa.
    El frontend usa esto para saber qué inputs y columnas dibujar.
    """
    # prefetch_related optimiza la subconsulta SQL de los CategoryFields
    queryset = AssetCategory.objects.prefetch_related('fields').filter(is_hidden=False).order_by('display_order')
    serializer_class = AssetCategorySerializer
    permission_classes = [DjangoModelPermissions]

class AssetViewSet(viewsets.ModelViewSet):
    serializer_class = AssetSerializer
    permission_classes = [DjangoModelPermissions, IsLocationManagerStrict]

    def get_queryset(self):
        user = self.request.user
        # JOIN optimizado con la nueva arquitectura
        queryset = Asset.objects.select_related('location', 'category', 'assigned_to').all().order_by('-created_at')

        if not user.is_superuser and not user.has_perm('assets.view_global_inventory'):
            queryset = queryset.filter(location__in=user.assigned_locations.all())

        location_id = self.request.query_params.get('location_id')
        if location_id:
            queryset = queryset.filter(location_id=location_id)

        return queryset

    def list(self, request, *args, **kwargs):
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
        pattern = f"inventory_user_{self.request.user.id}_*"
        cache.delete_pattern(pattern)

    def perform_create(self, serializer):
        user = self.request.user
        location = serializer.validated_data.get('location')

        # Permitimos activos sin sede (ej. Licencias Virtuales)
        if location and not user.is_superuser and not user.has_perm('assets.manage_global_inventory'):
            if not user.assigned_locations.filter(id=location.id).exists():
                raise PermissionDenied("Not authorized to create assets in this location.")

        serializer.save()
        self._invalidate_user_cache()

    def perform_update(self, serializer):
        serializer.save()
        self._invalidate_user_cache()

    def perform_destroy(self, instance):
        instance.delete()
        self._invalidate_user_cache()