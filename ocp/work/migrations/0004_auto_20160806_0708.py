# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('work', '0003_auto_20160804_2155'),
    ]

    operations = [
        migrations.AlterField(
            model_name='membershiprequest',
            name='fairnetwork',
            field=models.CharField(help_text="The username you use in the FairNetwork at <a href='https://fair.coop' target='_blank'>fair.coop</a>", max_length=255, verbose_name='FairNetwork username', blank=True),
        ),
        migrations.AlterField(
            model_name='membershiprequest',
            name='native_language',
            field=models.CharField(max_length=255, verbose_name='Languages', blank=True),
        ),
        migrations.AlterField(
            model_name='membershiprequest',
            name='type_of_membership',
            field=models.CharField(default=b'individual', max_length=12, verbose_name='Type of membership', choices=[(b'individual', 'individual membership (min 1 share)'), (b'collective', 'collective membership (min 2 shares)')]),
        ),
    ]
