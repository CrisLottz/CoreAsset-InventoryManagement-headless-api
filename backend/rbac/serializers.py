from rest_framework import serializers
from .models import Role

class RoleSerializer(serializers.ModelSerializer):

    user_count = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = ['id', 'name', 'user_count']
        read_only_fields = ['id', 'user_count']

    def get_user_count(self, obj):
        """
        Calcula la cantidad de usuarios vinculados a este rol.
        Optimización: DRF ejecutará esto por cada rol. Para evitar el problema N+1
        en despliegues masivos, después optimizaremos el ViewSet con prefetch_related.
        """
        return obj.user_set.count()