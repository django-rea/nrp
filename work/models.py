from django.db import models

from django.utils.translation import ugettext_lazy as _

from valuenetwork.valueaccounting.models import EconomicAgent

MEMBERSHIP_TYPE_CHOICES = (
    ('individual', _('individual')),
    ('collective', _('collective')),
)

class MembershipRequest(models.Model):
    name = models.CharField(_('name'), max_length=255)
    surname = models.CharField(_('surname (for individuals)'), max_length=255, blank=True)
    requested_username = models.CharField(_('requested username'), max_length=32)
    email_address = models.EmailField(_('email address'), max_length=96,)
    #    help_text=_("this field is optional, but we can't contact you via email without it"))
    phone_number = models.CharField(_('phone number'), max_length=32, blank=True, null=True)
    address = models.CharField(_('address (where do you live?)'), max_length=255, blank=True)
    native_language = models.CharField(_('native language'), max_length=255)
    type_of_membership = models.CharField(_('type of membership'), 
        max_length=12, choices=MEMBERSHIP_TYPE_CHOICES,
        default="individual")
    membership_for_services = models.BooleanField(_('Membership for services'), default=False,
        help_text=_('you have legal entity and want to offer services or products to the cooperative'))
    autonomous_membership = models.BooleanField(_('Autonomous membership'), default=False,
        help_text=_("you don't have legal entity and want to use the cooperative to make invoices either from inside and to outside the cooperative"))
    ocp_user_membership = models.BooleanField(_('OCP user membership'), default=False,
        help_text=_('for those that only want to use the OCP platform'))
    consumer_membership = models.BooleanField(_('Consumer membership'), default=False,
        help_text=_("you don't offer any product or service but want to consume through it and support the cooperative"))
    number_of_shares = models.IntegerField(_('number of shares'), 
        default=1, 
        help_text=_("How many shares do you want to underwrite? (minimum one. Each share worth 600 Faircoin = 30 Euro."))
    work_for_shares = models.BooleanField(_('work for one share'), default=False,
        help_text=_("You can get 1 share for 6 hours of work. If you choose this option, we will send you a list of tasks and the deadline. You won't have full access before the tasks are accomplished."))
    description = models.TextField(_('Description'), blank=True,
        help_text=_("Describe your project or collective and skills or abilities you can offer to the cooperative"))
    website = models.CharField(_('website'), max_length=255, blank=True)
    how_do_you_know_fc = models.TextField(_('How do you know Freedom Coop?'), blank=True,)
    known_member = models.TextField(_('Do you know any member already from FreedomCoop or FairCoop? If so, who?'), blank=True,)
    comments_and_questions = models.TextField(_('Comments and questions'), blank=True,)
    agent = models.ForeignKey(EconomicAgent,
        verbose_name=_('agent'), related_name='membership_requests',
        blank=True, null=True,
        help_text=_("this membership request became this EconomicAgent"))
