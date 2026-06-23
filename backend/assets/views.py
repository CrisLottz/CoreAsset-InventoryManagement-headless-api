from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import DjangoModelPermissions
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from django.db.models import Q

from .models import Location, AssetCategory, Asset, UserTablePreference
from .serializers import LocationSerializer, AssetCategorySerializer, AssetSerializer, UserTablePreferenceSerializer
from .permissions import IsLocationManagerStrict

class LocationViewSet(viewsets.ModelViewSet):
    queryset = Location.objects.all().order_by('name')
    serializer_class = LocationSerializer
    permission_classes = [DjangoModelPermissions, IsLocationManagerStrict]

class CategoryStructureViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AssetCategory.objects.prefetch_related('fields').filter(is_hidden=False).order_by('display_order')
    serializer_class = AssetCategorySerializer
    permission_classes = [DjangoModelPermissions]

@extend_schema_view(
    list=extend_schema(
        summary="Retrieve paginated assets with targeted server-side filtering and sorting",
        parameters=[
            OpenApiParameter(name='category', description='Filter by Category UUID', required=True, type=str),
            OpenApiParameter(name='location', description='Filter by Location UUID', required=False, type=str),
            OpenApiParameter(name='search', description='Search text', required=False, type=str),
            OpenApiParameter(name='search_field', description='Target field for search', required=False, type=str),
            OpenApiParameter(name='ordering', description='Sort field (e.g. internal_tag, -created_at)', required=False, type=str),
        ]
    )
)
class AssetViewSet(viewsets.ModelViewSet):
    serializer_class = AssetSerializer

    def get_queryset(self):
        queryset = Asset.objects.all() 
        
        category_id = self.request.query_params.get('category')
        location_id = self.request.query_params.get('location')
        search_query = self.request.query_params.get('search')
        search_field = self.request.query_params.get('search_field')
        ordering = self.request.query_params.get('ordering', '-created_at')

        if category_id:
            queryset = queryset.filter(category_id=category_id)

        if location_id:
            queryset = queryset.filter(location_id=location_id)

        # 3. Targeted Search Engine (Zoho Style)
        if search_query and search_field:
            if search_field == 'internal_tag':
                queryset = queryset.filter(internal_tag__icontains=search_query)
            elif search_field == 'location':
                queryset = queryset.filter(location__name__icontains=search_query)
            elif search_field == 'assigned_to':
                queryset = queryset.filter(
                    Q(assigned_to__first_name__icontains=search_query) | 
                    Q(assigned_to__last_name__icontains=search_query)
                )
            else:
                # Penetración en JSONB con normalización de espacios (A11y Friendly)
                lookup = f"dynamic_data__{search_field}__icontains"
                query_with_underscores = search_query.replace(' ', '_')
                
                # Busca simultáneamente "In use" o "In_use"
                queryset = queryset.filter(
                    Q(**{lookup: search_query}) | Q(**{lookup: query_with_underscores})
                )

        if ordering:
            if ordering in ['internal_tag', '-internal_tag', 'created_at', '-created_at']:
                queryset = queryset.order_by(ordering)
            else:
                clean_order = ordering.lstrip('-')
                if ordering.startswith('-'):
                    queryset = queryset.order_by(f'-dynamic_data__{clean_order}')
                else:
                    queryset = queryset.order_by(f'dynamic_data__{clean_order}')

        return queryset

class UserTablePreferenceViewSet(viewsets.ModelViewSet):
    serializer_class = UserTablePreferenceSerializer
    def get_queryset(self):
        return UserTablePreference.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @extend_schema(
        summary="Save or update column layout preferences for a category table",
        responses={200: UserTablePreferenceSerializer}
    )
    def create(self, request, *skip_args, **skip_kwargs):
        category_id = request.data.get('category')
        columns_config = request.data.get('columns_config')

        pref, created = UserTablePreference.objects.update_or_create(
            user=request.user,
            category_id=category_id,
            defaults={'columns_config': columns_config}
        )
        serializer = self.get_serializer(pref)
        return Response(serializer.data, status=status.HTTP_200_OK)