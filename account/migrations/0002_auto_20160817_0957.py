# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='account',
            name='language',
            field=models.CharField(default=b'en', max_length=10, verbose_name='language', choices=[(b'en', 'English'), (b'es', 'espa\xf1ol')]),
        ),
    ]
