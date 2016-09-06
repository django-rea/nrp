from django.db import models
from django.contrib.auth.models import User

from django.utils.translation import ugettext_lazy as _

from valuenetwork.valueaccounting.models import EconomicAgent
#from fobi.models import FormEntry

MEMBERSHIP_TYPE_CHOICES = (
    #('participant', _('project participant (no membership)')),
    ('individual', _('individual membership (min 1 share)')),
    ('collective', _('collective membership (min 2 shares)')),
)

REQUEST_STATE_CHOICES = (
    ('new', _('new')),
    ('accepted', _('accepted')),
    ('declined', _('declined')),
)

class MembershipRequest(models.Model):
    request_date = models.DateField(auto_now_add=True, blank=True, null=True, editable=False)
    name = models.CharField(_('Name'), max_length=255)
    surname = models.CharField(_('Surname (for individual memberships)'), max_length=255, blank=True)
    requested_username = models.CharField(_('Requested username'), max_length=32)
    email_address = models.EmailField(_('Email address'), max_length=96,)
    #    help_text=_("this field is optional, but we can't contact you via email without it"))
    phone_number = models.CharField(_('Phone number'), max_length=32, blank=True, null=True)
    address = models.CharField(_('Where do you live?'), max_length=255, blank=True)
    native_language = models.CharField(_('Languages'), max_length=255, blank=True)
    type_of_membership = models.CharField(_('Type of membership'),
        max_length=12, choices=MEMBERSHIP_TYPE_CHOICES,
        default="individual")
    #membership_for_services = models.BooleanField(_('Membership for services'), default=False,
    #    help_text=_('you have legal entity and want to offer services or products to the cooperative'))
    #autonomous_membership = models.BooleanField(_('Autonomous membership'), default=False,
    #    help_text=_("you don't have legal entity and want to use the cooperative to make invoices either from inside and to outside the cooperative"))
    #ocp_user_membership = models.BooleanField(_('OCP user membership'), default=False,
    #    help_text=_('for those that only want to use the OCP platform'))
    #consumer_membership = models.BooleanField(_('Consumer membership'), default=False,
    #    help_text=_("you don't offer any product or service but want to consume through it and support the cooperative"))
    number_of_shares = models.IntegerField(_('Number of shares'),
        default=1,
        help_text=_("How many shares would you like to underwrite? Each share is worth 30 Euros (600 Faircoin)"))
    #work_for_shares = models.BooleanField(_('work for one share'), default=False,
    #    help_text=_("You can get 1 share for 6 hours of work. If you choose this option, we will send you a list of tasks and the deadline. You won't have full access before the tasks are accomplished."))
    description = models.TextField(_('Description'),
        help_text=_("Describe your project or collective and the skills or abilities you can offer the cooperative"))
    website = models.CharField(_('Website'), max_length=255, blank=True)
    fairnetwork = models.CharField(_('FairNetwork username'), max_length=255, blank=True,
        help_text = _("The username you use in the FairNetwork at <a href='https://fair.coop' target='_blank'>fair.coop</a>"))
    usefaircoin = models.CharField(_('UseFaircoin profile'), max_length=255, blank=True,
        help_text = _("If you are in the directory at <a href='https://use.fair-coin.org' target='_blank'>use.fair-coin.org</a> please add the URL to your profile."))
    fairmarket = models.CharField(_('FairMarket shop'), max_length=255, blank=True,
        help_text = _("If you have an online shop at <a href='https://market.fair.coop' target='_blank'>market.fair.coop</a> please add the URL to your fair shop."))
    #how_do_you_know_fc = models.TextField(_('How do you know Freedom Coop?'), blank=True,)
    known_member = models.CharField(_('Are there any FairCoop participant(s) who can give references about you? If so, who?'), max_length=255, blank=True)
    comments_and_questions = models.TextField(_('Comments and questions'), blank=True,)

    agent = models.ForeignKey(EconomicAgent,
        verbose_name=_('agent'), related_name='membership_requests',
        blank=True, null=True,
        help_text=_("this membership request became this EconomicAgent"))
    state = models.CharField(_('state'),
        max_length=12, choices=REQUEST_STATE_CHOICES,
        default='new', editable=False)

    def __unicode__(self):
        return self.name


JOINING_STYLE_CHOICES = (
    ('moderated', _('moderated')),
    ('autojoin', _('autojoin')),
)

VISIBILITY_CHOICES = (
    ('private', _('private')),
    ('FCmembers', _('only FC members')),
    ('public', _('public')),
)

class Project(models.Model):
    agent = models.OneToOneField(EconomicAgent,
        verbose_name=_('agent'), related_name='project')
    joining_style = models.CharField(_('joining style'),
        max_length=12, choices=JOINING_STYLE_CHOICES,
        default="autojoin")
    visibility = models.CharField(_('visibility'),
        max_length=12, choices=VISIBILITY_CHOICES,
        default="FCmembers")
    fobi_slug = models.CharField(_('custom form slug'),
        max_length=255, blank=True)

    #fobi_form = models.OneToOneField(FormEntry,
    #    verbose_name=_('custom form'), related_name='project',
    #    blank=True, null=True,
    #    help_text=_("this Project use this custom form (fobi FormEntry)"))
    #join_request = models.ForeignKey(JoinRequest,
    #    verbose_name=_('join request'), related_name='project',
    #    blank=True, null=True,
    #    help_text=_("this Project is using this JoinRequest form"))

    def __unicode__(self):
        return _('Project: ') + self.agent.name

    def is_moderated(self):
        return self.joining_style == 'moderated'

    def is_public(self):
        return self.visibility == 'public'


class SkillSuggestion(models.Model):
    skill = models.CharField(_('skill'), max_length=128,
        help_text=_("A new skill that you want to offer that is not already listed"))
    suggested_by = models.ForeignKey(User, verbose_name=_('suggested by'),
        related_name='skill_suggestion', blank=True, null=True, editable=False)
    suggestion_date = models.DateField(auto_now_add=True, blank=True, null=True, editable=False)

    def __unicode__(self):
        return self.skill

from nine.versions import DJANGO_LTE_1_5
from fobi.contrib.plugins.form_handlers.db_store.models import SavedFormDataEntry

USER_TYPE_CHOICES = (
    #('participant', _('project participant (no membership)')),
    ('individual', _('individual')),
    ('collective', _('collective')),
)

class JoinRequest(models.Model):
    # common fields for all projects
    project = models.ForeignKey(Project,
        verbose_name=_('project'), related_name='join_requests',
        #blank=True, null=True,
        help_text=_("this join request is for joining this Project"))

    request_date = models.DateField(auto_now_add=True, blank=True, null=True, editable=False)
    type_of_user = models.CharField(_('Type of user'),
        max_length=12, choices=USER_TYPE_CHOICES,
        default="individual")
    name = models.CharField(_('Name'), max_length=255)
    surname = models.CharField(_('Surname (for individual join requests)'), max_length=255, blank=True)
    requested_username = models.CharField(_('Requested username'), max_length=32)
    email_address = models.EmailField(_('Email address'), max_length=96,)
    #    help_text=_("this field is optional, but we can't contact you via email without it"))
    phone_number = models.CharField(_('Phone number'), max_length=32, blank=True, null=True)
    address = models.CharField(_('Town/Region where you are based'), max_length=255, blank=True, null=True)
    #native_language = models.CharField(_('Languages'), max_length=255, blank=True)

    #description = models.TextField(_('Description'),
    #    help_text=_("Describe your collective or the personal skills you can offer to the project"))

    agent = models.ForeignKey(EconomicAgent,
        verbose_name=_('agent'), related_name='project_join_requests',
        blank=True, null=True,
        help_text=_("this join request became this EconomicAgent"))

    fobi_data = models.OneToOneField(SavedFormDataEntry,
        verbose_name=_('custom fobi id'), related_name='join_request',
        blank=True, null=True,
        help_text=_("this join request is linked to this custom form (fobi SavedFormDataEntry)"))

    state = models.CharField(_('state'),
        max_length=12, choices=REQUEST_STATE_CHOICES,
        default='new', editable=False)

    def fobi_slug(self):
      if self.project.fobi_slug:
        return self.project.fobi_slug
      return False

    def __unicode__(self):
        return self.name

