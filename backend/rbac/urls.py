from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RoleViewSet, PermissionViewSet

router = DefaultRouter()
router.register(r'roles', RoleViewSet, basename='rbac-roles')
router.register(r'permissions', PermissionViewSet, basename='rbac-permissions')

urlpatterns = [
    path('', include(router.urls)),
]