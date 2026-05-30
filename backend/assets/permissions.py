from rest_framework import permissions

class IsLocationManagerStrict(permissions.BasePermission):
    """
    Controla el alcance geográfico (Scope) de las operaciones.
    """
    def has_object_permission(self, request, view, obj):

        if request.method in permissions.SAFE_METHODS:
            return True


        if request.user.is_superuser or request.user.has_perm('assets.manage_global_inventory'):
            return True


        location = obj if hasattr(obj, 'name') else obj.location
        return request.user.assigned_locations.filter(id=location.id).exists()