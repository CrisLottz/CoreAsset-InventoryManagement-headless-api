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

        response = self.get_response(request)


        if request.method in ['POST', 'PUT', 'PATCH', 'DELETE'] and 200 <= response.status_code < 300:


            if hasattr(request, 'user') and request.user.is_authenticated:
                import re
                import logging
                
                logger = logging.getLogger(__name__)
                entity_id = None
                
                try:
                    if request.method in ['POST', 'PUT', 'PATCH']:
                        if hasattr(response, 'data') and isinstance(response.data, dict):
                            extracted_id = response.data.get('id')
                            if extracted_id:
                                entity_id = uuid.UUID(str(extracted_id))
                    elif request.method == 'DELETE':
                        match = re.search(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', request.path, re.IGNORECASE)
                        if match:
                            entity_id = uuid.UUID(match.group(0))
                except Exception as e:
                    logger.warning(f"Failed to extract entity_id in AuditMiddleware: {e}")
                    entity_id = None
                    
                try:
                    AuditLog.objects.create(
                        actor=request.user,
                        action=request.method,
                        entity_type=request.path,
                        entity_id=entity_id,
                        ip_address=request.META.get('REMOTE_ADDR', '0.0.0.0'),
                        metadata_json={
                            "status_code": response.status_code,
                            "user_agent": request.META.get('HTTP_USER_AGENT', 'Unknown')
                        }
                    )
                except Exception as e:
                    logger.error(f"Failed to create AuditLog entry: {e}")

        return response