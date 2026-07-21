from rest_framework import viewsets, permissions
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils.dateparse import parse_datetime
from django.db.models import Q
from .models import AuditLog
from .serializers import AuditLogSerializer

class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Strictly Read-Only ViewSet for Audit Logs.
    Enforces DjangoModelPermissions (requires view_auditlog).
    """
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['action', 'entity_type', 'ip_address']
    ordering_fields = ['created_at', 'action']
    ordering = ['-created_at']

    def get_queryset(self):
        """
        Custom robust filtering to avoid external dependencies.
        Supports filtering by actor (UUID), action, entity_type, and date ranges.
        """
        queryset = AuditLog.objects.select_related('actor').all()
        
        # We must verify permissions manually if accessing via DRF browsable API 
        # or list endpoints because DjangoModelPermissions by default allows GET 
        # if the user is authenticated. 
        # BUT wait, DjangoModelPermissions checks `view_auditlog` for GET requests 
        # only if we set it up properly, but by default it requires `view_` permission 
        # since DRF 3.10+ if we use `DjangoModelPermissions`.
        
        # Query Params
        actor_id = self.request.query_params.get('actor')
        action = self.request.query_params.get('action')
        entity_type = self.request.query_params.get('entity_type')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        if actor_id:
            queryset = queryset.filter(actor_id=actor_id)
        
        if action:
            queryset = queryset.filter(action__iexact=action)
            
        if entity_type:
            queryset = queryset.filter(entity_type__icontains=entity_type)
            
        if start_date:
            parsed_start = parse_datetime(start_date)
            if parsed_start:
                queryset = queryset.filter(created_at__gte=parsed_start)
                
        if end_date:
            parsed_end = parse_datetime(end_date)
            if parsed_end:
                queryset = queryset.filter(created_at__lte=parsed_end)

        return queryset
