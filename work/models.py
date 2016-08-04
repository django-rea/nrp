from django.db import models

from django.utils.translation import ugettext_lazy as _

from valuenetwork.valueaccounting.models import EconomicAgent

MEMBERSHIP_TYPE_CHOICES = (
    #('participant', _('project participant (no membership)')),
    ('individual', _('individual membership (min 1 share)')),
    ('collective', _('collective membership (min 2 shares)')),
)

class MembershipRequest(models.Model):
    request_date = models.DateField(auto_now_add=True, blank=True, null=True, editable=False)
    name = models.CharField(_('Name'), max_length=255)
    surname = models.CharField(_('Surname (for individuals)'), max_length=255, blank=True)
    requested_username = models.CharField(_('Requested username'), max_length=32)
    email_address = models.EmailField(_('Email address'), max_length=96,)
    #    help_text=_("this field is optional, but we can't contact you via email without it"))
    phone_number = models.CharField(_('Phone number'), max_length=32, blank=True, null=True)
    address = models.CharField(_('Address (where do you live?)'), max_length=255, blank=True)
    native_language = models.CharField(_('Native language'), max_length=255)
    type_of_membership = models.CharField(_('Type of access requested'), 
        max_length=12, choices=MEMBERSHIP_TYPE_CHOICES,
        default="individual")
    # todo: deactivate next fields
    membership_for_services = models.BooleanField(_('Membership for services'), default=False,
        help_text=_('you have legal entity and want to offer services or products to the cooperative'))
    autonomous_membership = models.BooleanField(_('Autonomous membership'), default=False,
        help_text=_("you don't have legal entity and want to use the cooperative to make invoices either from inside and to outside the cooperative"))
    ocp_user_membership = models.BooleanField(_('OCP user membership'), default=False,
        help_text=_('for those that only want to use the OCP platform'))
    consumer_membership = models.BooleanField(_('Consumer membership'), default=False,
        help_text=_("you don't offer any product or service but want to consume through it and support the cooperative"))
    # stop deleting fields
    number_of_shares = models.IntegerField(_('Number of shares'), 
        default=1, 
        help_text=_("How many shares do you want to underwrite? Each share is worth 30 Euro (600 Faircoin)."))
    # deactivate next one for launch (perhaps later)
    work_for_shares = models.BooleanField(_('Work for one share'), default=False,
        help_text=_("You can get 1 share for 6 hours of work. If you choose this option, we will send you a list of tasks and the deadline. You won't have full access before the tasks are accomplished."))
    
    description = models.TextField(_('Description'),
        help_text = _("Describe your project or collective and skills or abilities you can offer to the cooperative."))
    # activate next fields asap
    #fairnetwork = models.CharField(_('FairNetwork username'), max_length=255, blank=True,
    #	help_text = _("The username you use at in the FairNetwork at fair.coop"))
    #usefaircoin = models.CharField(_('UseFaircoin profile'), max_length=255, blank=True,
    #	help_text = _("If you are in the directory at use.fair-coin.org please put the Url to your profile."))
    #fairmarket = models.CharField(_('FairMarket shop'), max_length=255, blank=True,
    #	help_text = _("If you have an online shop at market.fair.coop please put the Url to your fair shop."))
    website = models.CharField(_('Website'), max_length=255, blank=True)
    #deactivate next two fields asap
    how_do_you_know_fc = models.TextField(_('How do you know Freedom Coop?'), blank=True,)
    known_member = models.TextField(_('Do you know any member already from FreedomCoop or FairCoop? If so, who?'), blank=True,)
    
    comments_and_questions = models.TextField(_('Comments and questions'), blank=True,)
    agent = models.ForeignKey(EconomicAgent,
        verbose_name=_('agent'), related_name='membership_requests',
        blank=True, null=True,
        help_text=_("this membership request became this EconomicAgent"))

    def __unicode__(self):
        return self.name
