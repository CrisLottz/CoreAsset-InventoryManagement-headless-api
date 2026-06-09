import jsonschema
from rest_framework import serializers
from .models import Location, Asset


ASSET_METADATA_SCHEMA = {
    "type": "object",
    "required": ["type"],
    "properties": {
        "type": {"type": "string", "enum": ["laptop", "license", "mobile"]}
    },
    "allOf": [
        {
            "if": {"properties": {"type": {"const": "laptop"}}},
            "then": {
                "properties": {
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
    # INYECCIÓN: Extraer el username del modelo User asociado, solo lectura.
    assigned_user_name = serializers.CharField(source='assigned_to.username', read_only=True)

    class Meta:
        model = Asset
        fields = [
            'id', 'internal_tag', 'location', 'location_name',
            'assigned_to', 'assigned_user_name', 'status', 'metadata_json',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_metadata_json(self, value):
        """
        Delega toda la complejidad condicional al motor de jsonschema.
        """
        try:
            jsonschema.validate(instance=value, schema=ASSET_METADATA_SCHEMA)
        except jsonschema.exceptions.ValidationError as e:
            raise serializers.ValidationError({
                "schema_error": e.message,
                "path": list(e.path)
            })

        return value