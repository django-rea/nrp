# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('work', '0014_newfeature'),
    ]

    operations = [
        migrations.AddField(
            model_name='newfeature',
            name='permissions',
            field=models.TextField(null=True, verbose_name='permissions', blank=True),
        ),
        migrations.AlterField(
            model_name='newfeature',
            name='deployment_date',
            field=models.DateField(verbose_name='deployment date'),
        ),
    ]
