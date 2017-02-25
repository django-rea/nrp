# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import easy_thumbnails.fields


class Migration(migrations.Migration):

    dependencies = [
        ('work', '0013_auto_20160913_1301'),
    ]

    operations = [
        migrations.CreateModel(
            name='NewFeature',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=128, verbose_name='name')),
                ('deployment_date', models.DateField()),
                ('description', models.TextField(verbose_name='Description')),
                ('url', models.CharField(max_length=255, verbose_name='url', blank=True)),
                ('screenshot', easy_thumbnails.fields.ThumbnailerImageField(upload_to=b'photos', null=True, verbose_name='screenshot', blank=True)),
            ],
            options={
                'ordering': ('-deployment_date',),
            },
        ),
    ]
