from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache

from assets.models import Asset
from employees.models import Employee
from audit.models import AuditLog

class DashboardAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        force_refresh = request.query_params.get('force_refresh') == 'true'
        location_id = request.query_params.get('location')
        
        # 1. Dynamic Cache Key based on User and Filters
        cache_key = f"dashboard_analytics_user_{request.user.id}"
        if location_id:
            cache_key += f"_loc_{location_id}"

        # 2. Cache Lookup
        if not force_refresh:
            cached_data = cache.get(cache_key)
            if cached_data:
                return Response(cached_data)

        # 3. Base QuerySets & Strict RBAC Enforcement
        asset_qs = Asset.objects.all()
        
        if not request.user.has_perm('assets.view_global_inventory') and not request.user.is_superuser:
            asset_qs = asset_qs.filter(location__in=request.user.assigned_locations.all())

        if location_id:
            asset_qs = asset_qs.filter(location_id=location_id)

        # 4. KPI Aggregations (Pushed to Database, NO Python Loops)
        total_assets = asset_qs.count()
        active_employees = Employee.objects.filter(is_active=True).count()
        
        # Status is stored in dynamic_data. We use icontains for robustness.
        assets_in_maintenance = asset_qs.filter(dynamic_data__Status__icontains='Maintenance').count()
        assets_unassigned = asset_qs.filter(assigned_to__isnull=True).count()

        kpis = {
            "total_assets": total_assets,
            "active_employees": active_employees,
            "assets_in_maintenance": assets_in_maintenance,
            "assets_unassigned": assets_unassigned
        }

        # 5. Assets by Category
        assets_by_category_qs = asset_qs.values('category__name').annotate(count=Count('id')).order_by('-count')
        assets_by_category = [{"name": item['category__name'], "count": item['count']} for item in assets_by_category_qs]

        # 6. Assets by Status
        assets_by_status_qs = asset_qs.filter(dynamic_data__Status__isnull=False).values('dynamic_data__Status').annotate(count=Count('id')).order_by('-count')
        assets_by_status = [{"name": item['dynamic_data__Status'], "count": item['count']} for item in assets_by_status_qs]

        # 7. Assets by Location
        assets_by_location_qs = asset_qs.filter(location__isnull=False).values('location__name').annotate(count=Count('id')).order_by('-count')
        assets_by_location = [{"name": item['location__name'], "count": item['count']} for item in assets_by_location_qs]

        # 8. Recent Activity Volume (Last 7 Days)
        seven_days_ago = timezone.now() - timedelta(days=7)
        
        audit_qs = AuditLog.objects.filter(created_at__gte=seven_days_ago)
        if not request.user.has_perm('assets.view_global_inventory') and not request.user.is_superuser:
            # If not a global admin, only show the volume of actions they performed
            audit_qs = audit_qs.filter(actor=request.user)

        recent_activity_qs = audit_qs.annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(count=Count('id')).order_by('date')
        
        recent_activity_volume = [
            {"date": item['date'].strftime('%Y-%m-%d'), "count": item['count']} 
            for item in recent_activity_qs
        ]

        # 9. Construct Final Payload
        payload = {
            "kpis": kpis,
            "assets_by_category": assets_by_category,
            "assets_by_status": assets_by_status,
            "assets_by_location": assets_by_location,
            "recent_activity_volume": recent_activity_volume
        }

        # 10. Cache payload for 15 minutes
        cache.set(cache_key, payload, timeout=60 * 15)

        return Response(payload)
