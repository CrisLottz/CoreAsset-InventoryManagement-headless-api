from django.contrib import admin
from .models import Location, Asset

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    search_fields = ('name',)
    list_filter = ('is_active',)

@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('internal_tag', 'location', 'status', 'assigned_to', 'created_at')
    list_filter = ('location', 'status')
    search_fields = ('internal_tag',)