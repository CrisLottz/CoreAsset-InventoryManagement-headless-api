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
                    "is_staff": user.is_staff
                }
            }, status=status.HTTP_200_OK)
        else:

            return Response(
                {"detail": "Credenciales inválidas"},
                status=status.HTTP_401_UNAUTHORIZED
            )


class UserMeView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):


        user = request.user

        return Response({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_staff": user.is_staff,
            "is_mfa_enabled": user.is_mfa_enabled
        }, status=status.HTTP_200_OK)

class LogoutView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        logout(request)

        return Response(
            {"detail": "Sesión cerrada exitosamente."},
            status=status.HTTP_200_OK
        )

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

    def get_serializer_class(self):
        """
        Sobrescribe el serializador por defecto dependiendo de la acción.
        Garantiza que la interfaz web y la documentación OpenAPI
        muestren los campos correctos.
        """
        if self.action == 'assign_roles':
            return AssignRoleSerializer
        return super().get_serializer_class()