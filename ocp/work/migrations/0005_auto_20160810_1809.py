# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('work', '0004_auto_20160806_0708'),
    ]

    operations = [
        migrations.AlterField(
            model_name='membershiprequest',
            name='address',
            field=models.CharField(max_length=255, verbose_name='Where do you live?', blank=True),
        ),
        migrations.AlterField(
            model_name='membershiprequest',
            name='description',
            field=models.TextField(help_text='Describe your project or collective and the skills or abilities you can offer the cooperative', verbose_name='Description'),
        ),
        migrations.AlterField(
            model_name='membershiprequest',
            name='fairmarket',
            field=models.CharField(help_text="If you have an online shop at <a href='https://market.fair.coop' target='_blank'>market.fair.coop</a> please add the URL to your fair shop.", max_length=255, verbose_name='FairMarket shop', blank=True),
        ),
        migrations.AlterField(
            model_name='membershiprequest',
            name='known_member',
            field=models.CharField(max_length=255, verbose_name='Are there any FairCoop participant(s) who can give references about you? If so, who?', blank=True),
        ),
        migrations.AlterField(
            model_name='membershiprequest',
            name='number_of_shares',
            field=models.IntegerField(default=1, help_text='How many shares would you like to underwrite? Each share is worth 30 Euros (600 Faircoin)', verbose_name='Number of shares'),
        ),
        migrations.AlterField(
            model_name='membershiprequest',
            name='surname',
            field=models.CharField(max_length=255, verbose_name='Surname (for individual memberships)', blank=True),
        ),
        migrations.AlterField(
            model_name='membershiprequest',
            name='usefaircoin',
            field=models.CharField(help_text="If you are in the directory at <a href='https://use.fair-coin.org' target='_blank'>use.fair-coin.org</a> please add the URL to your profile.", max_length=255, verbose_name='UseFaircoin profile', blank=True),
        ),
    ]
