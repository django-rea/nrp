# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('work', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='membershiprequest',
            name='address',
            field=models.CharField(max_length=255, verbose_name='Address (where do you live?)', blank=True),
        ),
        migrations.AlterField(
            model_name='membershiprequest',
            name='description',
            field=models.TextField(help_text='Describe your project or collective and skills or abilities you can offer to the cooperative.', verbose_name='Description'),
        ),
        migrations.AlterField(
            model_name='membershiprequest',
            name='email_address',
            field=models.EmailField(max_length=96, verbose_name='Email address'),
        ),
        migrations.AlterField(
            model_name='membershiprequest',
            name='name',
            field=models.CharField(max_length=255, verbose_name='Name'),
        ),
        migrations.AlterField(
            model_name='membershiprequest',
            name='native_language',
            field=models.CharField(max_length=255, verbose_name='Native language'),
        ),
        migrations.AlterField(
            model_name='membershiprequest',
            name='number_of_shares',
            field=models.IntegerField(default=1, help_text='How many shares do you want to underwrite? Each share is worth 30 Euro (600 Faircoin).', verbose_name='Number of shares'),
        ),
        migrations.AlterField(
            model_name='membershiprequest',
            name='phone_number',
            field=models.CharField(max_length=32, null=True, verbose_name='Phone number', blank=True),
        ),
        migrations.AlterField(
            model_name='membershiprequest',
            name='requested_username',
            field=models.CharField(max_length=32, verbose_name='Requested username'),
        ),
        migrations.AlterField(
            model_name='membershiprequest',
            name='surname',
            field=models.CharField(max_length=255, verbose_name='Surname (for individuals)', blank=True),
        ),
        migrations.AlterField(
            model_name='membershiprequest',
            name='type_of_membership',
            field=models.CharField(default=b'individual', max_length=12, verbose_name='Type of access requested', choices=[(b'individual', 'individual membership (min 1 share)'), (b'collective', 'collective membership (min 2 shares)')]),
        ),
        migrations.AlterField(
            model_name='membershiprequest',
            name='website',
            field=models.CharField(max_length=255, verbose_name='Website', blank=True),
        ),
        migrations.AlterField(
            model_name='membershiprequest',
            name='work_for_shares',
            field=models.BooleanField(default=False, help_text="You can get 1 share for 6 hours of work. If you choose this option, we will send you a list of tasks and the deadline. You won't have full access before the tasks are accomplished.", verbose_name='Work for one share'),
        ),
    ]
