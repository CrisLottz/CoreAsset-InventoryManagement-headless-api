

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('assets', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='asset',
            options={'permissions': [('view_global_inventory', 'Puede ver activos de TODAS las sedes'), ('manage_global_inventory', 'Puede editar/borrar activos de TODAS las sedes')]},
        ),
    ]
