from rest_framework import serializers
from django.contrib.auth import get_user_model
from rbac.models import Role

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'is_staff', 'is_active', 'is_mfa_enabled']


        extra_kwargs = {
            'password': {'write_only': True},
            'id': {'read_only': True}
        }


    def create(self, validated_data):
        """
        Interceptamos la creación para asegurar que la contraseña pase por
        el algoritmo de hashing (PBKDF2/Argon2) antes de tocar PostgreSQL.
        """

        password = validated_data.pop('password', None)


        user = User(**validated_data)

        if password:

            user.set_password(password)

        user.save()
        return user

    def update(self, instance, validated_data):
        """
        Interceptamos la actualización para asegurar que si se provee
        una nueva contraseña, esta sea hasheada antes de guardar.
        """
        password = validated_data.pop('password', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
            
        if password:
            instance.set_password(password)
            
        instance.save()
        return instance

class AssignRoleSerializer(serializers.Serializer):
    """
    Serializador RPC exclusivo para validar la inyección de roles.
    Espera un payload como: {"role_ids": [1, 2]}
    """
    role_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=True
    )

    def validate_role_ids(self, value):

        existing_roles = Role.objects.filter(id__in=value).values_list('id', flat=True)
        if len(existing_roles) != len(value):
            raise serializers.ValidationError("Uno o más roles proporcionados no existen en el sistema.")
        return value