# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('valueaccounting', '0003_auto_20160803_1925'),
    ]

    operations = [
        migrations.AlterField(
            model_name='economicevent',
            name='digital_currency_tx_state',
            field=models.CharField(blank=True, max_length=12, null=True, verbose_name='digital currency transaction state', choices=[(b'new', 'New'), (b'pending', 'Pending'), (b'broadcast', 'Broadcast'), (b'confirmed', 'Confirmed')]),
        ),
    ]
