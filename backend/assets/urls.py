from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LocationViewSet, AssetViewSet, AssetMetadataView

router = DefaultRouter()
router.register(r'locations', LocationViewSet, basename='inventory-locations')
router.register(r'inventory', AssetViewSet, basename='inventory-assets')

urlpatterns = [
    # Metadata dinámica expuesta en /api/v1/assets/meta/
    path('meta/', AssetMetadataView.as_view(), name='inventory-metadata'),
    path('', include(router.urls)),
]