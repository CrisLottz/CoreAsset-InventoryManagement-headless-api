from rest_framework import serializers
from .models import AuditLog
from django.contrib.auth import get_user_model

User = get_user_model()

class AuditActorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'avatar', 'avatar_visibility']
        read_only_fields = fields

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

class AuditLogSerializer(serializers.ModelSerializer):
    # Nested representation for the frontend to display human-readable names
    actor_details = AuditActorSerializer(source='actor', read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            'id', 
            'actor', 
            'actor_details', 
            'action', 
            'entity_type', 
            'entity_id', 
            'metadata_json', 
            'ip_address', 
            'created_at'
        ]
        read_only_fields = fields
