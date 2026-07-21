from rest_framework import serializers
from django.contrib.auth.models import Permission
from .models import Role

class RoleSerializer(serializers.ModelSerializer):

    user_count = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = ['id', 'name', 'user_count', 'permissions']
        read_only_fields = ['id', 'user_count']

    def get_user_count(self, obj):
        """
        Calcula la cantidad de usuarios vinculados a este rol.
        Optimización: DRF ejecutará esto por cada rol. Para evitar el problema N+1
        en despliegues masivos, después optimizaremos el ViewSet con prefetch_related.
        """
        return obj.user_set.count()

class PermissionSerializer(serializers.ModelSerializer):
    app_label = serializers.CharField(source='content_type.app_label', read_only=True)
    model_name = serializers.CharField(source='content_type.model', read_only=True)

    class Meta:
        model = Permission
        fields = ['id', 'name', 'codename', 'app_label', 'model_name']