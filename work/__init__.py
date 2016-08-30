# -*- coding: utf-8 -*-

# Connecting signal "comment_was_posted" to comment_notification()
def comment_notification(sender, comment, **kwargs):
    #import pdb; pdb.set_trace()
    from django.contrib.contenttypes.models import ContentType
    ct_commented = ContentType.objects.get(id=comment.content_type)
    if ct_commented.model == 'membershiprequest':
        msr = comment.content_object

        if msr.agent:
            from django.db import models
            msr_agent = models.EconomicAgent.objects.get(id=msr.agent)
            msr_owner_name = msr_agent.name
            msr_owner_email = msr_agent.email
        else:
            msr_owner_name = msr.name
            msr_owner_email = msr.email_address

        from django.conf import settings
        if "notification" in settings.INSTALLED_APPS:
            from notification import models as notification
            from django.contrib.auth.models import User
            users = User.objects.filter(is_staff=True)
            if users:
                site_name = get_site_name()
                membership_url= get_url_starter() + "/accounting/membership-request/" + str(msr.id) + "/"
                notification.send(
                    users,
                    "comment_membership_request",
                    {"name": comment.name,
                    "comment": comment.comment,
                    "site_name": site_name,
                    "membership_url": membership_url,
                    }
)

    #TODO: other content types where comments are attached to.
    elif content_type_commented.model == 'joinrequest':
        pass

from django_comments.models import Comment
from django_comments.signals import comment_was_posted
comment_was_posted.connect(comment_notification, sender=Comment)
