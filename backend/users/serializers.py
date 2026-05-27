from rest_framework import serializers
from django.contrib.auth import get_user_model

# Obtenemos dinámicamente tu modelo User con UUID
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