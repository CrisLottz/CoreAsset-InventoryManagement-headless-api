from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LoginView, UserMeView, LogoutView, UserViewSet, VerifyPasswordView

router = DefaultRouter()

router.register(r'', UserViewSet, basename='user')

urlpatterns = [
    path('login/', LoginView.as_view(), name='api-login'),
    path('me/', UserMeView.as_view(), name='api-me'),
    path('logout/', LogoutView.as_view(), name='api-logout'),
    path('verify-password/', VerifyPasswordView.as_view(), name='api-verify-password'),


    path('', include(router.urls)),
]