from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LoginView, UserMeView, LogoutView, UserViewSet

# 1. Inicializamos el Router de DRF
router = DefaultRouter()

# 2. Registramos nuestro ViewSet. Esto generará rutas como /inventory/ y /inventory/<uuid>/
router.register(r'inventory', UserViewSet, basename='user-inventory')

urlpatterns = [
    # Rutas manuales de autenticación
    path('login/', LoginView.as_view(), name='api-login'),
    path('me/', UserMeView.as_view(), name='api-me'),
    path('logout/', LogoutView.as_view(), name='api-logout'),
    
    # 3. Inyectamos las rutas dinámicas generadas por el Router
    path('', include(router.urls)),
]