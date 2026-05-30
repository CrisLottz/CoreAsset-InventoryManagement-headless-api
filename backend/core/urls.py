from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),


    path('api/v1/users/', include('users.urls')),
    path('api/v1/rbac/', include('rbac.urls')),
    path('api/v1/assets/', include('assets.urls')),



    path('api/v1/schema/', SpectacularAPIView.as_view(), name='schema'),

    path('api/v1/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]