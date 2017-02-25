# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('work', '0011_merge'),
    ]

    operations = [
        migrations.AddField(
            model_name='joinrequest',
            name='state',
            field=models.CharField(default=b'new', verbose_name='state', max_length=12, editable=False, choices=[(b'new', 'new'), (b'accepted', 'accepted'), (b'declined', 'declined')]),
        ),
    ]
