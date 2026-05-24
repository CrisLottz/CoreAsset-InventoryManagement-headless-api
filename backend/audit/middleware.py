import uuid
from .models import AuditLog

class AuditMiddleware:
    """
    Middleware que intercepta todas las peticiones HTTP.
    Si la petición es una mutación (POST, PUT, DELETE) y es exitosa,
    registra automáticamente la acción en la base de datos.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Dejamos que la petición viaje hacia el núcleo (vistas/controladores)
        response = self.get_response(request)

        # 2. Cuando la respuesta viene de regreso, evaluamos si debemos auditarla
        if request.method in ['POST', 'PUT', 'PATCH', 'DELETE'] and 200 <= response.status_code < 300:
            
            # Solo auditamos si sabemos quién es el usuario (está autenticado)
            if hasattr(request, 'user') and request.user.is_authenticated:
                
                AuditLog.objects.create(
                    actor=request.user,
                    action=request.method,
                    entity_type=request.path, # Guardamos la URL atacada temporalmente
                    entity_id=uuid.uuid4(),   # Fallback UUID (se afinará al usar DRF)
                    ip_address=request.META.get('REMOTE_ADDR', '0.0.0.0'),
                    metadata_json={
                        "status_code": response.status_code,
                        "user_agent": request.META.get('HTTP_USER_AGENT', 'Unknown')
                    }
                )

        return response