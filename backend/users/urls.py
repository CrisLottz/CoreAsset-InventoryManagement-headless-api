from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LoginView, UserMeView, LogoutView, UserViewSet


router = DefaultRouter()


router.register(r'inventory', UserViewSet, basename='user-inventory')

urlpatterns = [

    path('login/', LoginView.as_view(), name='api-login'),
    path('me/', UserMeView.as_view(), name='api-me'),
    path('logout/', LogoutView.as_view(), name='api-logout'),


    path('', include(router.urls)),
]