from rest_framework import serializers
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):
    """
    Serializador para mostrar los detalles de un usuario.
    """
    is_admin = serializers.BooleanField(source='is_superuser')
    last_login = serializers.DateTimeField(format="%d-%m-%Y %H:%M") # Ejemplo de salida: 13-12-2025 15:30
    date_joined = serializers.DateTimeField(format="%d-%m-%Y %H:%M") # Ejemplo de salida: 13-12-2025 15:30

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'first_name',
            'last_name',
            'email',
            'is_active',
            'is_admin',
            'last_login',
            'date_joined'
        ]
        read_only_fields = fields