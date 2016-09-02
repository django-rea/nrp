# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('work', '0006_project_skillsuggestion'),
    ]

    operations = [
        migrations.AlterField(
            model_name='project',
            name='joining_style',
            field=models.CharField(default=b'autojoin', max_length=12, verbose_name='joining style', choices=[(b'moderated', 'moderated'), (b'autojoin', 'autojoin')]),
        ),
        migrations.AlterField(
            model_name='project',
            name='visibility',
            field=models.CharField(default=b'FCmembers', max_length=12, verbose_name='visibility', choices=[(b'private', 'private'), (b'FCmembers', 'only FC members'), (b'public', 'public')]),
        ),
    ]
