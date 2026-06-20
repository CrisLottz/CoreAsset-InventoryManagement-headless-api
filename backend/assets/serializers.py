from rest_framework import serializers
from .models import Location, AssetCategory, CategoryField, Asset

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['id', 'name', 'country', 'address', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']

# ---------------------------------------------------------
# STRUCTURE SERIALIZERS (UI Contract)
# ---------------------------------------------------------
class CategoryFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoryField
        fields = ['id', 'name', 'field_type', 'is_required', 'is_locked', 'options_metadata']

class AssetCategorySerializer(serializers.ModelSerializer):
    fields = CategoryFieldSerializer(many=True, read_only=True)

    class Meta:
        model = AssetCategory
        fields = ['id', 'name', 'icon', 'is_system_default', 'is_hidden', 'display_order', 'fields']

# ---------------------------------------------------------
# POLYMORPHIC ASSET SERIALIZER (Mutations)
# ---------------------------------------------------------
class AssetSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True)
    assigned_employee_name = serializers.SerializerMethodField()

    class Meta:
        model = Asset
        fields = [
            'id', 'internal_tag', 'category', 'category_name', 
            'location', 'location_name', 'assigned_to', 'assigned_employee_name', 
            'dynamic_data', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_assigned_employee_name(self, obj):
        if obj.assigned_to:
            return f"{obj.assigned_to.first_name} {obj.assigned_to.last_name}"
        return None

    def validate(self, data):
        category = data.get('category') or getattr(self.instance, 'category', None)
        dynamic_data = data.get('dynamic_data', {})

        if category:
            errors = {}
            cleaned_dynamic_data = {}
            category_fields = category.fields.all()

            for field in category_fields:
                
                # 1. INTERCEPTOR DE LLAVES FORÁNEAS (ESTO ES LO QUE FALTABA)
                if field.field_type == 'LOCATION':
                    val = data.get('location') if 'location' in data else getattr(self.instance, 'location', None)
                    if field.is_required and not val:
                        raise serializers.ValidationError({"location": ["Location assignment is required."]})
                    continue
                    
                if field.field_type == 'EMPLOYEE':
                    val = data.get('assigned_to') if 'assigned_to' in data else getattr(self.instance, 'assigned_to', None)
                    if field.is_required and not val:
                        raise serializers.ValidationError({"assigned_to": ["Employee assignment is required."]})
                    continue

              
                if 'dynamic_data' in data:
                    val = dynamic_data.get(field.name)
                    
                    if field.is_required and val in [None, '', []]:
                        errors[field.name] = "This field is required."
                        continue
                        
                    if val not in [None, '']:
                        if field.field_type == 'NUMBER':
                            try:
                                float(val)
                            except ValueError:
                                errors[field.name] = "Must be a valid number."
                                
                        elif field.field_type in ['DROPDOWN', 'COLOR_STATUS']:
                            valid_values = [opt.get('value') for opt in field.options_metadata]
                            if val not in valid_values:
                                errors[field.name] = f"Invalid option. Allowed: {valid_values}"
                        
                        cleaned_dynamic_data[field.name] = val

            if errors:
                raise serializers.ValidationError({"dynamic_data": errors})

            if 'dynamic_data' in data:
                data['dynamic_data'] = cleaned_dynamic_data

        return data