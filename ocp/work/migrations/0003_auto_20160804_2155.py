# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('work', '0002_auto_20160804_1834'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='membershiprequest',
            name='autonomous_membership',
        ),
        migrations.RemoveField(
            model_name='membershiprequest',
            name='consumer_membership',
        ),
        migrations.RemoveField(
            model_name='membershiprequest',
            name='how_do_you_know_fc',
        ),
        migrations.RemoveField(
            model_name='membershiprequest',
            name='membership_for_services',
        ),
        migrations.RemoveField(
            model_name='membershiprequest',
            name='ocp_user_membership',
        ),
        migrations.RemoveField(
            model_name='membershiprequest',
            name='work_for_shares',
        ),
        migrations.AddField(
            model_name='membershiprequest',
            name='fairmarket',
            field=models.CharField(help_text="If you have an online shop at <a href='https://market.fair.coop' target='_blank'>market.fair.coop</a> please put the URL to your fair shop.", max_length=255, verbose_name='FairMarket shop', blank=True),
        ),
        migrations.AddField(
            model_name='membershiprequest',
            name='fairnetwork',
            field=models.CharField(help_text="The username you use at in the FairNetwork at <a href='https://fair.coop' target='_blank'>fair.coop</a>", max_length=255, verbose_name='FairNetwork username', blank=True),
        ),
        migrations.AddField(
            model_name='membershiprequest',
            name='usefaircoin',
            field=models.CharField(help_text="If you are in the directory at <a href='https://use.fair-coin.org' target='_blank'>use.fair-coin.org</a> please put the URL to your profile.", max_length=255, verbose_name='UseFaircoin profile', blank=True),
        ),
        migrations.AlterField(
            model_name='membershiprequest',
            name='description',
            field=models.TextField(help_text='Describe your project or collective and the skills or abilities you can offer to the cooperative', verbose_name='Description'),
        ),
        migrations.AlterField(
            model_name='membershiprequest',
            name='known_member',
            field=models.CharField(max_length=255, verbose_name='Is there any FairCoop participant who can give references about you? If so, who?', blank=True),
        ),
        migrations.AlterField(
            model_name='membershiprequest',
            name='number_of_shares',
            field=models.IntegerField(default=1, help_text='How many shares do you want to underwrite? Each share is worth 30 Euro (600 Faircoin)', verbose_name='Number of shares'),
        ),
    ]
