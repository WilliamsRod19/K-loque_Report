# Generated by Django 5.2.1 on 2025-06-08 16:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('incident', '0002_alter_incident_date'),
    ]

    operations = [
        migrations.AlterField(
            model_name='incident',
            name='description',
            field=models.CharField(max_length=255, verbose_name='descripción'),
        ),
    ]
