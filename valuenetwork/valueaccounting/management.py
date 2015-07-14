from django.conf import settings
from django.db.models import signals
from django.utils.translation import ugettext_noop as _

if "notification" in settings.INSTALLED_APPS:
    from notification import models as notification

    def create_notice_types(app, created_models, verbosity, **kwargs):
        notification.create_notice_type("valnet_join_task", _("Join Task"), _("a colleaque wants to help with this task"), default=2)
        notification.create_notice_type("valnet_help_wanted", _("Help Wanted"), _("a colleague requests help that fits your skills"), default=2)
        notification.create_notice_type("valnet_new_task", _("New Task"), _("a new task was posted that fits your skills"), default=2)
        notification.create_notice_type("valnet_new_todo", _("New Todo"), _("a new todo was posted that is assigned to you"), default=2)
        notification.create_notice_type("valnet_deleted_todo", _("Deleted Todo"), _("a todo that was assigned to you has been deleted"), default=2)
        notification.create_notice_type("valnet_distribution", _("New Distribution"), _("you have received a new income distribution"), default=2)
        notification.create_notice_type("valnet_payout_request", _("Payout Request"), _("you have received a new payout request"), default=2)
        print "created notice types"
    signals.post_syncdb.connect(create_notice_types, sender=notification)
else:
    print "Skipping creation of NoticeTypes as notification app not found"

