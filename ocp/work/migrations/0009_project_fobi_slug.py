# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('work', '0008_joinrequest'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='fobi_slug',
            field=models.CharField(max_length=255, verbose_name='custom form slug', blank=True),
        ),
    ]
