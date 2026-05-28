from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # --- ENDPOINTS CORE DE NEGOCIO ---
    path('api/v1/users/', include('users.urls')),
    path('api/v1/rbac/', include('rbac.urls')),
    path('api/v1/assets/', include('assets.urls')),
    
    # --- ENDPOINTS DE DOCUMENTACIÓN AUTOGENERADA ---
    # 1. El contrato puro en formato YAML/JSON
    path('api/v1/schema/', SpectacularAPIView.as_view(), name='schema'),
    # 2. La interfaz gráfica interactiva (Swagger UI)
    path('api/v1/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]