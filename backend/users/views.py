from django.contrib.auth import authenticate, login
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

# Decorador vital: Garantiza que, pase lo que pase, Django envíe la cookie CSRF al frontend
@method_decorator(ensure_csrf_cookie, name='dispatch')
class LoginView(APIView):
    # Cualquiera puede intentar iniciar sesión, no pedimos token previo
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        # 1. authenticate() verifica el hash Argon2/PBKDF2 en la base de datos
        user = authenticate(request, username=username, password=password)

        if user is not None:
            # 2. login() es la función mágica que genera la Cookie de Sesión (sessionid)
            login(request, user)
            
            return Response({
                "detail": "Autenticación exitosa",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "is_staff": user.is_staff
                }
            }, status=status.HTTP_200_OK)
        else:
            # 401 Unauthorized: El estándar REST para credenciales inválidas
            return Response(
                {"detail": "Credenciales inválidas"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )