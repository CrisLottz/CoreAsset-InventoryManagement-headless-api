from rest_framework import serializers
from django.contrib.auth import get_user_model
from rbac.models import Role

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'is_staff', 'is_active', 'is_mfa_enabled']
        
        # Reglas de seguridad estrictas a nivel de serialización
        extra_kwargs = {
            'password': {'write_only': True}, # Nunca debe salir en un GET, solo entra en POST/PUT
            'id': {'read_only': True}         # El frontend nunca debe intentar modificar el UUID
        }
     

    def create(self, validated_data):
        """
        Interceptamos la creación para asegurar que la contraseña pase por 
        el algoritmo de hashing (PBKDF2/Argon2) antes de tocar PostgreSQL.
        """
        # Extraemos la contraseña en texto plano del JSON validado
        password = validated_data.pop('password', None)
        
        # Instanciamos el usuario sin guardarlo aún
        user = User(**validated_data)
        
        if password:
            # Esta función nativa aplica la sal criptográfica y el hash
            user.set_password(password)
            
        user.save()
        return user
    
class AssignRoleSerializer(serializers.Serializer):
    """
    Serializador RPC exclusivo para validar la inyección de roles.
    Espera un payload como: {"role_ids": [1, 2]}
    """
    role_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=True # Permitimos array vacío para poder revocar todos los roles
    )

    def validate_role_ids(self, value):
        # Protegemos la integridad relacional comprobando que todos los IDs existen en la base de datos
        existing_roles = Role.objects.filter(id__in=value).values_list('id', flat=True)
        if len(existing_roles) != len(value):
            raise serializers.ValidationError("Uno o más roles proporcionados no existen en el sistema.")
        return value    