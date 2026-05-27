from django.contrib.auth import authenticate, login
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import logout
from rest_framework import viewsets
from django.contrib.auth import get_user_model
from .serializers import UserSerializer

User = get_user_model()


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


class UserMeView(APIView):
    # CRÍTICO: Este endpoint exige que la cookie de sesión sea válida
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Como pasó el filtro de IsAuthenticated, 'request.user' ya contiene 
        # el objeto del usuario real consultado desde PostgreSQL.
        user = request.user
        
        return Response({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_staff": user.is_staff,
            "is_mfa_enabled": user.is_mfa_enabled # Incluimos el campo específico de tu diagrama
        }, status=status.HTTP_200_OK)

class LogoutView(APIView):
    # Solo alguien con sesión iniciada puede cerrarla
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # La función nativa logout() limpia los datos de la sesión y destruye la cookie
        logout(request)
        
        return Response(
            {"detail": "Sesión cerrada exitosamente."}, 
            status=status.HTTP_200_OK
        )
    
class UserViewSet(viewsets.ModelViewSet):
    """
    Controlador maestro para el CRUD de Usuarios.
    ModelViewSet autogenera GET(list), GET(detail), POST, PUT, PATCH y DELETE.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    
    # CRÍTICO: Bloqueamos todo el inventario de usuarios. 
    # Solo personal autenticado puede consultarlo o modificarlo.
    permission_classes = [IsAuthenticated]    