from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.auth.admin import GroupAdmin
from .models import Role

# 1. Desregistramos el modelo original 'Group' para que desaparezca del panel
admin.site.unregister(Group)

# 2. Registramos nuestro Proxy Model 'Role' usando la configuración visual nativa (GroupAdmin)
@admin.register(Role)
class RoleAdmin(GroupAdmin):
    pass