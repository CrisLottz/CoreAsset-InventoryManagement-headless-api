from django.db import models
import uuid

class Employee(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Equivalente al "Número de Empleado" si lo requieren, opcional pero útil
    employee_number = models.CharField(max_length=50, unique=True, null=True, blank=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    job_title = models.CharField(max_length=100)
    
    # Metadata opcional para integraciones futuras
    email = models.EmailField(unique=True, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.job_title}"