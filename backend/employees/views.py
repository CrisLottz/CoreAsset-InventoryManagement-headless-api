from rest_framework import viewsets, permissions, filters, pagination, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import authenticate
from .models import Employee
from .serializers import EmployeeSerializer
import csv
import io

class StandardResultsSetPagination(pagination.PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    permission_classes = [permissions.DjangoModelPermissions]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['first_name', 'last_name', 'email', 'employee_number']

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == 'list':
            status_filter = self.request.query_params.get('status', 'active')
            if status_filter == 'active':
                return qs.filter(is_active=True)
            elif status_filter == 'inactive':
                return qs.filter(is_active=False)
        return qs

    def perform_destroy(self, instance):
        # Soft delete
        instance.is_active = False
        instance.save()

    @action(detail=True, methods=['post'])
    def reactivate(self, request, pk=None):
        employee = self.get_object()
        employee.is_active = True
        employee.save()
        return Response({"status": "reactivated"})

    @action(detail=True, methods=['post'], url_path='hard-delete')
    def hard_delete(self, request, pk=None):
        # Require password for hard delete
        password = request.data.get('password')
        if not password:
            return Response({"error": "Admin password is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify the user's password
        user = authenticate(username=request.user.username, password=password)
        if user is None or user != request.user:
            return Response({"error": "Invalid password."}, status=status.HTTP_403_FORBIDDEN)
        
        employee = self.get_object()
        employee.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['post'], url_path='import-csv')
    def import_csv(self, request):
        if 'file' not in request.FILES:
            return Response({"error": "No file uploaded."}, status=status.HTTP_400_BAD_REQUEST)
        
        # mapping is expected to be a JSON string like '{"Nombre": "first_name", "Correo": "email"}'
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

        try:
            file_bytes = file.read()
            try:
                decoded_file = file_bytes.decode('utf-8-sig')
            except UnicodeDecodeError:
                decoded_file = file_bytes.decode('iso-8859-1')
        except Exception as e:
            return Response({"error": f"Error decoding file: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        io_string = io.StringIO(decoded_file)
        reader = csv.DictReader(io_string)
        
        created_count = 0
        errors = []

        for row_num, row in enumerate(reader, start=2): # Start at 2 since row 1 is headers
            # Skip completely empty rows
            if not any(val.strip() if val else False for val in row.values()):
                continue

            employee_data = {}
            for csv_col, db_col in mapping.items():
                if csv_col in row:
                    employee_data[db_col] = row[csv_col].strip() if row[csv_col] else ""
            
            serializer = self.get_serializer(data=employee_data)
            if serializer.is_valid():
                serializer.save()
                created_count += 1
            else:
                errors.append({"row": row_num, "errors": serializer.errors})

        if errors:
            # If we want all-or-nothing, we should use a database transaction.
            # But partial success is often better for CSVs, returning the errors.
            return Response({
                "message": f"Created {created_count} employees with some errors.",
                "created": created_count,
                "errors": errors
            }, status=status.HTTP_207_MULTI_STATUS)

        return Response({"message": f"Successfully imported {created_count} employees.", "created": created_count}, status=status.HTTP_201_CREATED)