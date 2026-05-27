from django.urls import path
from .views import LoginView, UserMeView, LogoutView # Agregamos LogoutView

urlpatterns = [
    path('login/', LoginView.as_view(), name='api-login'),
    path('me/', UserMeView.as_view(), name='api-me'),
    path('logout/', LogoutView.as_view(), name='api-logout'), # Nueva ruta
]