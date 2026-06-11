from django.contrib import admin
from .models import Location, AssetCategory, CategoryField, Asset

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'country', 'is_active', 'created_at')
    search_fields = ('name', 'country')

@admin.register(AssetCategory)
class AssetCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_system_default', 'is_hidden', 'display_order')
    list_filter = ('is_system_default', 'is_hidden')
    ordering = ('display_order', 'name')

@admin.register(CategoryField)
class CategoryFieldAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'field_type', 'is_required', 'is_locked')
    list_filter = ('category', 'field_type', 'is_locked')
    search_fields = ('name', 'category__name')

@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    # Ya no existe 'status' fijo, ahora mostramos las relaciones duras de la nueva arquitectura
    list_display = ('internal_tag', 'category', 'location', 'assigned_to', 'created_at')
    list_filter = ('category', 'location')
    search_fields = ('internal_tag',)