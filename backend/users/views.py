from django.contrib.auth import authenticate, login
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import rest_framework
from rest_framework.permissions import AllowAny
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import logout
from rest_framework import viewsets
from django.contrib.auth import get_user_model
from .serializers import UserSerializer
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rbac.models import Role
from .serializers import AssignRoleSerializer

User = get_user_model()



@method_decorator(ensure_csrf_cookie, name='dispatch')
class LoginView(APIView):

    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')


        user = authenticate(request, username=username, password=password)

        if user is not None:

            login(request, user)

            return Response({
                "detail": "Autenticación exitosa",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "is_staff": user.is_staff,
                    "permissions": list(user.get_all_permissions())
                }
            }, status=status.HTTP_200_OK)
        else:

            return Response(
                {"detail": "Credenciales inválidas"},
                status=status.HTTP_401_UNAUTHORIZED
            )


class UserMeView(APIView):

    permission_classes = [IsAuthenticated]
    parser_classes = [rest_framework.parsers.MultiPartParser, rest_framework.parsers.JSONParser]

    def get(self, request):


        user = request.user

        return Response({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_staff": user.is_staff,
            "is_mfa_enabled": user.is_mfa_enabled,
            "avatar": request.build_absolute_uri(user.avatar.url) if user.avatar else None,
            "avatar_visibility": user.avatar_visibility,
            "permissions": list(user.get_all_permissions())
        }, status=status.HTTP_200_OK)

    def patch(self, request):
        user = request.user
        
        # Simple update logic for avatar and visibility
        if 'avatar' in request.FILES:
            user.avatar = request.FILES['avatar']
        if 'avatar_visibility' in request.data:
            user.avatar_visibility = request.data['avatar_visibility']
            
        user.save()
        
        return Response({
            "detail": "Preferencias actualizadas con éxito.",
            "avatar": request.build_absolute_uri(user.avatar.url) if user.avatar else None,
            "avatar_visibility": user.avatar_visibility,
        }, status=status.HTTP_200_OK)

class LogoutView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        logout(request)

        return Response(
            {"detail": "Sesión cerrada exitosamente."},
            status=status.HTTP_200_OK
        )

class VerifyPasswordView(APIView):
    """
    Endpoint para que el frontend valide de forma segura la contraseña
    actual del usuario antes de realizar operaciones destructivas
    (ej: eliminar campos del sistema en Category Builder).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        password = request.data.get('password')
        
        if not password:
            return Response({"detail": "La contraseña es obligatoria."}, status=status.HTTP_400_BAD_REQUEST)
            
        # check_password delega al hasher subyacente la comprobación segura
        if request.user.check_password(password):
            return Response({"detail": "Contraseña válida."}, status=status.HTTP_200_OK)
        else:
            return Response({"detail": "Contraseña incorrecta."}, status=status.HTTP_401_UNAUTHORIZED)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'], url_path='assign-roles')
    def assign_roles(self, request, pk=None):
        """
        Sobrescribe los roles actuales del usuario con la lista proporcionada.
        """

        user = self.get_object()


        serializer = AssignRoleSerializer(data=request.data)

        if serializer.is_valid():
            role_ids = serializer.validated_data['role_ids']


            roles = Role.objects.filter(id__in=role_ids)




            user.groups.set(roles)

            return Response(
                {"detail": "Privilegios actualizados con éxito.", "assigned_roles": role_ids},
                status=status.HTTP_200_OK
            )


        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='change-password')
    def change_password(self, request):
        """
        Cambia la contraseña del usuario autenticado.
        Valida la contraseña actual antes de aplicar la nueva.
        """
        user = request.user
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')

        if not current_password or not new_password or not confirm_password:
            return Response({"detail": "Todos los campos de contraseña son obligatorios."}, status=status.HTTP_400_BAD_REQUEST)

        if new_password != confirm_password:
            return Response({"detail": "La nueva contraseña y la confirmación no coinciden."}, status=status.HTTP_400_BAD_REQUEST)

        if not user.check_password(current_password):
            return Response({"detail": "La contraseña actual es incorrecta."}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()

        return Response({"detail": "Contraseña actualizada exitosamente."}, status=status.HTTP_200_OK)

    def get_serializer_class(self):
        """
        Sobrescribe el serializador por defecto dependiendo de la acción.
        Garantiza que la interfaz web y la documentación OpenAPI
        muestren los campos correctos.
        """
        if self.action == 'assign_roles':
            return AssignRoleSerializer
        return super().get_serializer_class()