from rest_framework import serializers
from .models import Employee

class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = [
            'id', 
            'employee_number', 
            'first_name', 
            'last_name', 
            'job_title', 
            'email', 
            'is_active', 
            'created_at', 
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_employee_number(self, value):
        if value == "":
            return None
        return value

    def validate_email(self, value):
        if value == "":
            return None
        return value