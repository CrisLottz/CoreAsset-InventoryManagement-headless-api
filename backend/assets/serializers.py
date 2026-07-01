import uuid
from rest_framework import serializers
from django.db import transaction
from .models import Location, AssetCategory, CategoryField, Asset, UserTablePreference

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['id', 'name', 'country', 'address', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']

# ---------------------------------------------------------
# STRUCTURE SERIALIZERS (UI Contract & Nested Mutations)
# ---------------------------------------------------------
class CategoryFieldSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False) # Permite strings temporales como 'new-123' del frontend

    class Meta:
        model = CategoryField
        fields = ['id', 'name', 'field_type', 'is_required', 'is_locked', 'options_metadata']

class AssetCategorySerializer(serializers.ModelSerializer):
    # Removido read_only=True para permitir mutaciones de escritura anidada
    fields = CategoryFieldSerializer(many=True, required=False)

    class Meta:
        model = AssetCategory
        fields = ['id', 'name', 'icon', 'is_system_default', 'is_hidden', 'display_order', 'fields']

    def create(self, validated_data):
        fields_data = validated_data.pop('fields', [])
        
        with transaction.atomic():
            category = AssetCategory.objects.create(**validated_data)
            
            for field_item in fields_data:
                CategoryField.objects.create(
                    id=uuid.uuid4(),
                    category=category,
                    name=field_item.get('name'),
                    field_type=field_item.get('field_type'),
                    is_required=field_item.get('is_required', False),
                    is_locked=False,
                    options_metadata=field_item.get('options_metadata', [])
                )
        return category

    def update(self, instance, validated_data):
        fields_data = validated_data.pop('fields', [])
        
        # Encapsulamiento en Transacción Atómica de PostgreSQL
        with transaction.atomic():
            # 1. Actualizar metadatos principales del Módulo
            instance.name = validated_data.get('name', instance.name)
            instance.icon = validated_data.get('icon', instance.icon)
            instance.is_hidden = validated_data.get('is_hidden', instance.is_hidden)
            instance.display_order = validated_data.get('display_order', instance.display_order)
            instance.save()

            # 2. Orquestar campos dinámicos
            keep_fields_ids = []
            
            for field_item in fields_data:
                field_id = field_item.get('id')
                
                # Caso A: Campo Nuevo (Inyectado por React)
                if not field_id or str(field_id).startswith('new-'):
                    new_field = CategoryField.objects.create(
                        id=uuid.uuid4(),
                        category=instance,
                        name=field_item.get('name'),
                        field_type=field_item.get('field_type'),
                        is_required=field_item.get('is_required', False),
                        is_locked=False,
                        options_metadata=field_item.get('options_metadata', [])
                    )
                    keep_fields_ids.append(new_field.id)
                
                # Caso B: Campo Existente
                else:
                    try:
                        db_field = CategoryField.objects.get(id=field_id, category=instance)
                        
                        # Salvaguarda arquitectónica: Evitar corrupción JSONB
                        if db_field.field_type != field_item.get('field_type') and not db_field.is_locked:
                            raise serializers.ValidationError(
                                f"Forbidden: Altering data type of field '{db_field.name}' from {db_field.field_type} to {field_item.get('field_type')} is blocked."
                            )
                        
                        db_field.name = field_item.get('name', db_field.name)
                        db_field.is_required = field_item.get('is_required', db_field.is_required)
                        db_field.options_metadata = field_item.get('options_metadata', db_field.options_metadata)
                        db_field.save()
                        
                        keep_fields_ids.append(db_field.id)
                    except CategoryField.DoesNotExist:
                        pass 

            # 3. Limpieza: Borrar campos excluidos que no estén bloqueados por el sistema
            CategoryField.objects.filter(category=instance).exclude(id__in=keep_fields_ids).filter(is_locked=False).delete()

        return instance

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

# ---------------------------------------------------------
# USER VIEW PREFERENCES SERIALIZER
# ---------------------------------------------------------
class UserTablePreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserTablePreference
        fields = ['category', 'columns_config', 'updated_at']

    def validate_columns_config(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("columns_config must be a list of layout objects.")
        return value