from django.contrib import admin
from django.urls import path, include # Importar 'include'

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Todas las rutas de la app 'users' quedarán bajo el prefijo /api/v1/users/
    path('api/v1/users/', include('users.urls')),
]