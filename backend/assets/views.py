from rest_framework import viewsets, status, pagination
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import DjangoModelPermissions
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from django.db.models import Q, Value, Count, F
from django.db.models.functions import Concat

from .models import Location, AssetCategory, Asset, UserTablePreference
from .serializers import LocationSerializer, AssetCategorySerializer, AssetSerializer, UserTablePreferenceSerializer
from .permissions import IsLocationManagerStrict

class LocationViewSet(viewsets.ModelViewSet):
    queryset = Location.objects.annotate(assets_count=Count('assets')).order_by('name')
    serializer_class = LocationSerializer
    permission_classes = [DjangoModelPermissions, IsLocationManagerStrict]

    @action(detail=True, methods=['get'])
    def category_breakdown(self, request, pk=None):
        location = self.get_object()
        breakdown = location.assets.values(
            'category__id', 
            'category__name'
        ).annotate(count=Count('id')).order_by('-count')
        
        formatted_breakdown = [
            {
                "category_id": str(item['category__id']),
                "category_name": item['category__name'],
                "count": item['count']
            }
            for item in breakdown
        ]
        return Response(formatted_breakdown)

class CategoryStructureViewSet(viewsets.ModelViewSet): # <-- Habilitada la capa de mutación
    queryset = AssetCategory.objects.prefetch_related('fields').filter(is_hidden=False).order_by('display_order')
    serializer_class = AssetCategorySerializer
    permission_classes = [DjangoModelPermissions]

class StandardResultsSetPagination(pagination.PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

@extend_schema_view(
    list=extend_schema(
        summary="Retrieve paginated assets with targeted server-side filtering and sorting",
        parameters=[
            OpenApiParameter(name='category', description='Filter by Category UUID', required=True, type=str),
            OpenApiParameter(name='location', description='Filter by Location UUID', required=False, type=str),
            OpenApiParameter(name='search', description='Search text', required=False, type=str),
            OpenApiParameter(name='search_field', description='Target field for search', required=False, type=str),
            OpenApiParameter(name='assigned_to_null', description='Filter strictly unassigned assets', required=False, type=str),
            OpenApiParameter(name='ordering', description='Sort field (e.g. internal_tag, -created_at)', required=False, type=str),
        ]
    )
)
class AssetViewSet(viewsets.ModelViewSet):
    serializer_class = AssetSerializer
    permission_classes = [DjangoModelPermissions, IsLocationManagerStrict]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = Asset.objects.all() 
        
        category_id = self.request.query_params.get('category')
        location_id = self.request.query_params.get('location')
        search_query = self.request.query_params.get('search')
        search_field = self.request.query_params.get('search_field')
        assigned_to_null = self.request.query_params.get('assigned_to_null')
        ordering = self.request.query_params.get('ordering', '-created_at')

        if category_id:
            queryset = queryset.filter(category_id=category_id)

        if location_id:
            queryset = queryset.filter(location_id=location_id)

        # 3. Targeted Search Engine (Zoho Style)
        if search_field == 'assigned_to' and assigned_to_null == 'true':
            queryset = queryset.filter(assigned_to__isnull=True)
        elif search_query and search_field:
            if search_field == 'internal_tag':
                queryset = queryset.filter(internal_tag__icontains=search_query)
            elif search_field == 'location':
                queryset = queryset.filter(location__name__icontains=search_query)
            elif search_field == 'assigned_to':
                queryset = queryset.annotate(
                    full_name=Concat('assigned_to__first_name', Value(' '), 'assigned_to__last_name')
                ).filter(
                    Q(full_name__icontains=search_query) |
                    Q(assigned_to__first_name__icontains=search_query) |
                    Q(assigned_to__last_name__icontains=search_query)
                )
            else:
                lookup = f"dynamic_data__{search_field}__icontains"
                query_with_underscores = search_query.replace(' ', '_')
                query_with_spaces = search_query.replace('_', ' ')
                
                queryset = queryset.filter(
                    Q(**{lookup: search_query}) | 
                    Q(**{lookup: query_with_underscores}) |
                    Q(**{lookup: query_with_spaces})
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

    @action(detail=False, methods=['post'], url_path='import-csv')
    def import_csv(self, request):
        if 'file' not in request.FILES:
            return Response({"error": "No file uploaded."}, status=status.HTTP_400_BAD_REQUEST)
        
        category_id = request.data.get('category_id')
        if not category_id:
            return Response({"error": "Category ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        import json
        mapping_str = request.data.get('mapping')
        if not mapping_str:
            return Response({"error": "No column mapping provided."}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            mapping = json.loads(mapping_str)
        except json.JSONDecodeError:
            return Response({"error": "Invalid mapping format."}, status=status.HTTP_400_BAD_REQUEST)

        file = request.FILES['file']
        if not file.name.endswith('.csv'):
            return Response({"error": "Invalid file type. Only CSV is allowed."}, status=status.HTTP_400_BAD_REQUEST)

        delimiter = request.data.get('delimiter', ',')

        import csv
        import io
        try:
            file_bytes = file.read()
            try:
                decoded_file = file_bytes.decode('utf-8-sig')
            except UnicodeDecodeError:
                decoded_file = file_bytes.decode('iso-8859-1')
        except Exception as e:
            return Response({"error": f"Error decoding file: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
            
        io_string = io.StringIO(decoded_file)
        reader = csv.DictReader(io_string, delimiter=delimiter)
        
        created_count = 0
        errors = []

        from employees.models import Employee
        import uuid
        
        def is_valid_uuid(val):
            try:
                uuid.UUID(str(val))
                return True
            except ValueError:
                return False

        for row_num, row in enumerate(reader, start=2):
            if not any(val.strip() if val else False for val in row.values()):
                continue

            asset_data = {
                "category": category_id,
                "dynamic_data": {}
            }
            
            for csv_col, db_col in mapping.items():
                if csv_col in row:
                    val = row[csv_col].strip() if row[csv_col] else ""
                    if not val:
                        continue
                        
                    if db_col == 'internal_tag':
                        asset_data['internal_tag'] = val
                    elif db_col == 'location':
                        if is_valid_uuid(val):
                            asset_data['location'] = val
                        else:
                            loc = Location.objects.filter(name__iexact=val).first()
                            if loc:
                                asset_data['location'] = str(loc.id)
                    elif db_col == 'assigned_to':
                        if is_valid_uuid(val):
                            asset_data['assigned_to'] = val
                        else:
                            emp = Employee.objects.filter(email__iexact=val).first()
                            if not emp:
                                emp = Employee.objects.filter(Q(first_name__icontains=val) | Q(last_name__icontains=val)).first()
                            if emp:
                                asset_data['assigned_to'] = str(emp.id)
                    else:
                        asset_data['dynamic_data'][db_col] = val
            
            serializer = self.get_serializer(data=asset_data)
            if serializer.is_valid():
                serializer.save()
                created_count += 1
            else:
                errors.append({"row": row_num, "errors": serializer.errors})

        if errors:
            return Response({
                "message": f"Created {created_count} assets with some errors.",
                "created": created_count,
                "errors": errors
            }, status=status.HTTP_207_MULTI_STATUS)

        return Response({"message": f"Successfully imported {created_count} assets.", "created": created_count}, status=status.HTTP_201_CREATED)


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