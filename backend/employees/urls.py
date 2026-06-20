from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EmployeeViewSet

router = DefaultRouter()
# Registramos en la raíz de este dominio
router.register(r'', EmployeeViewSet, basename='employees')

urlpatterns = [
    path('', include(router.urls)),
]