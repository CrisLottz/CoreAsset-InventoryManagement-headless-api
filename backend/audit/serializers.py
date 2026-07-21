from rest_framework import serializers
from .models import AuditLog
from django.contrib.auth import get_user_model

User = get_user_model()

class AuditActorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = fields

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
