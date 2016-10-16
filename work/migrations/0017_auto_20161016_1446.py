# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('work', '0016_auto_20161016_0937'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='invoicenumber',
            options={'ordering': ('-invoice_date', '-sequence')},
        ),
        migrations.AddField(
            model_name='invoicenumber',
            name='description',
            field=models.TextField(null=True, verbose_name='Description', blank=True),
        ),
    ]
