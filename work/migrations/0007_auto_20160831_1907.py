# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

def set_request_state(apps, schema_editor):
    # We can't import the MembershipRequest model directly as it may be a newer
    # version than this migration expects. We use the historical version.
    MembershipRequest = apps.get_model("work", "MembershipRequest")
    for req in MembershipRequest.objects.all():
        if req.agent:
            req.state = "accepted"
            req.save()

class Migration(migrations.Migration):

    dependencies = [
        ('work', '0006_membershiprequest_state'),
    ]

    operations = [
        migrations.RunPython(set_request_state),
    ]
