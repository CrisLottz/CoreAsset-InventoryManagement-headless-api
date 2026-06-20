from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LocationViewSet, CategoryStructureViewSet, AssetViewSet

router = DefaultRouter()
router.register(r'locations', LocationViewSet, basename='inventory-locations')
router.register(r'categories', CategoryStructureViewSet, basename='inventory-categories')
router.register(r'inventory', AssetViewSet, basename='inventory-assets')

urlpatterns = [
    path('', include(router.urls)),
]