from rest_framework import permissions

class IsLocationManagerStrict(permissions.BasePermission):
    """
    Controla el alcance geográfico (Scope) de las operaciones.
    """
    def has_object_permission(self, request, view, obj):
        # 1. Si es lectura (GET), el filtrado ya ocurrió en el ViewSet. Permitimos el paso.
        if request.method in permissions.SAFE_METHODS:
            return True

        # 2. Si es Superusuario o tiene el check de 'manage_global_inventory', aprueba todo.
        if request.user.is_superuser or request.user.has_perm('assets.manage_global_inventory'):
            return True

        # 3. Si no es global, verificamos si la sede del objeto está en sus sedes asignadas.
        location = obj if hasattr(obj, 'name') else obj.location
        return request.user.assigned_locations.filter(id=location.id).exists()