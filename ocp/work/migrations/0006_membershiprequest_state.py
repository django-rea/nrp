# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('work', '0005_auto_20160810_1809'),
    ]

    operations = [
        migrations.AddField(
            model_name='membershiprequest',
            name='state',
            field=models.CharField(default=b'new', verbose_name='state', max_length=12, editable=False, choices=[(b'new', 'new'), (b'accepted', 'accepted'), (b'declined', 'declined')]),
        ),
    ]
