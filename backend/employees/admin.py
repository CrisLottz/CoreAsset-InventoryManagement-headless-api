from django.contrib import admin
from .models import Employee

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'job_title', 'is_active')
    search_fields = ('first_name', 'last_name', 'job_title', 'employee_number')
    list_filter = ('is_active',)