from rest_framework import serializers
from django.contrib.auth import get_user_model
from rbac.models import Role

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'password', 'is_staff', 'is_active', 'is_mfa_enabled',
            'employee', 'assigned_locations', 'groups', 'user_permissions',
            'avatar', 'avatar_visibility'
        ]

        extra_kwargs = {
            'password': {'write_only': True},
            'id': {'read_only': True}
        }

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get('request')
        
        # Privacy Logic: If avatar is private, hide it from other regular users
        if request and request.user:
            is_self = request.user.id == instance.id
            is_admin = request.user.is_superuser or request.user.is_staff
            if instance.avatar_visibility == 'private' and not is_self and not is_admin:
                ret['avatar'] = None
                
        return ret


    def create(self, validated_data):
        password = validated_data.pop('password', None)
        assigned_locations = validated_data.pop('assigned_locations', [])
        groups = validated_data.pop('groups', [])
        user_permissions = validated_data.pop('user_permissions', [])

        user = User(**validated_data)
        if password:
            user.set_password(password)
        user.save()

        if assigned_locations:
            user.assigned_locations.set(assigned_locations)
        if groups:
            user.groups.set(groups)
        if user_permissions:
            user.user_permissions.set(user_permissions)

        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        
        # M2M Fields handling
        if 'assigned_locations' in validated_data:
            instance.assigned_locations.set(validated_data.pop('assigned_locations'))
        if 'groups' in validated_data:
            instance.groups.set(validated_data.pop('groups'))
        if 'user_permissions' in validated_data:
            instance.user_permissions.set(validated_data.pop('user_permissions'))
        
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