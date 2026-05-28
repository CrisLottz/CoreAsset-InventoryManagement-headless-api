import jsonschema
from rest_framework import serializers
from .models import Location, Asset

# 1. EL CONTRATO (JSON Schema Estándar)
ASSET_METADATA_SCHEMA = {
    "type": "object",
    "required": ["type"],
    "properties": {
        "type": {"type": "string", "enum": ["laptop", "license", "mobile"]}
    },
    # Patrón de validación polimórfica
    "allOf": [
        {
            "if": {"properties": {"type": {"const": "laptop"}}},
            "then": {
                "required": ["mac_address", "cpu"],
                "properties": {
                    # Validación estricta con RegEx para la MAC Address
                    "mac_address": {"type": "string", "pattern": "^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$"},
                    "cpu": {"type": "string"}
                }
            }
        },
        {
            "if": {"properties": {"type": {"const": "license"}}},
            "then": {
                "required": ["tenant"],
                "properties": {
                    "tenant": {"type": "string"}
                }
            }
        }
    ]
}

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['id', 'name', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']

class AssetSerializer(serializers.ModelSerializer):
    location_name = serializers.CharField(source='location.name', read_only=True)

    class Meta:
        model = Asset
        fields = [
            'id', 'internal_tag', 'location', 'location_name',
            'assigned_to', 'status', 'metadata_json',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_metadata_json(self, value):
        """
        Delega toda la complejidad condicional al motor de jsonschema.
        """
        try:
            # Si el JSON no cumple el contrato, lanza una excepción inmediatamente
            jsonschema.validate(instance=value, schema=ASSET_METADATA_SCHEMA)
        except jsonschema.exceptions.ValidationError as e:
            # Traducimos el error de jsonschema al formato legible de DRF
            raise serializers.ValidationError({
                "schema_error": e.message,
                "path": list(e.path) # Indica exactamente en qué nodo del JSON falló
            })
            
        return value