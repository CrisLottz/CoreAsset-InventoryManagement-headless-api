

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assets', '0001_initial'),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='user',
            options={},
        ),
        migrations.AddField(
            model_name='user',
            name='assigned_locations',
            field=models.ManyToManyField(blank=True, help_text='Sedes que este usuario puede administrar.', related_name='managers', to='assets.location'),
        ),
        migrations.AlterField(
            model_name='user',
            name='is_mfa_enabled',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterModelTable(
            name='user',
            table='auth_user',
        ),
    ]
