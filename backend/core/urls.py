from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),

    # Application Modules (v1)
    path('api/v1/users/', include('users.urls')),
    path('api/v1/rbac/', include('rbac.urls')),
    path('api/v1/assets/', include('assets.urls')),
    path('api/v1/employees/', include('employees.urls')), # <-- REGISTERED UNDER DOMAIN ROOT
    path('api/v1/audit/', include('audit.urls')),

    # API Documentation (drf-spectacular)
    path('api/v1/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/v1/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)