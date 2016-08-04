# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('valueaccounting', '0002_auto_20160706_2026'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='location',
            options={'ordering': ('name',)},
        ),
        migrations.AlterField(
            model_name='agentassociation',
            name='state',
            field=models.CharField(default=b'active', max_length=12, verbose_name='state', choices=[(b'active', 'active'), (b'inactive', 'inactive'), (b'potential', 'candidate')]),
        ),
        migrations.AlterField(
            model_name='agentassociationtype',
            name='association_behavior',
            field=models.CharField(blank=True, max_length=12, null=True, verbose_name='association behavior', choices=[(b'supplier', 'supplier'), (b'customer', 'customer'), (b'member', 'member'), (b'child', 'child'), (b'custodian', 'custodian'), (b'manager', 'manager'), (b'peer', 'peer')]),
        ),
        migrations.AlterField(
            model_name='valueequation',
            name='percentage_behavior',
            field=models.CharField(default=b'straight', help_text='Remaining percentage uses the %% of the remaining amount to be distributed.  Straight percentage uses the %% of the total distribution amount.', max_length=12, verbose_name='percentage behavior', choices=[(b'remaining', 'Remaining percentage'), (b'straight', 'Straight percentage')]),
        ),
    ]
