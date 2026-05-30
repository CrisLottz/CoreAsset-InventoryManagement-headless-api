from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.auth.admin import GroupAdmin
from .models import Role


admin.site.unregister(Group)


@admin.register(Role)
class RoleAdmin(GroupAdmin):
    pass