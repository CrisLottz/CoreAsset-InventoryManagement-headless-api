from django.urls import path
from .views import LoginView, UserMeView # Importamos la nueva vista

urlpatterns = [
    path('login/', LoginView.as_view(), name='api-login'),
    path('me/', UserMeView.as_view(), name='api-me'), # Nueva ruta
]