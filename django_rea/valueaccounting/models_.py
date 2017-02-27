from __future__ import print_function
import datetime
import time
import re
from decimal import *
from operator import attrgetter

from django.utils.encoding import python_2_unicode_compatible
from toposort import toposort, toposort_flatten

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.template.defaultfilters import slugify
import json as simplejson

"""Models based on REA

These models are based on the Bill McCarthy's Resource-Event-Agent accounting model:
https://www.msu.edu/~mccarth4/
http://en.wikipedia.org/wiki/Resources,_events,_agents_(accounting_model)

REA is also the basis for ISO/IEC FDIS 15944-4 ACCOUNTING AND ECONOMIC ONTOLOGY
http://global.ihs.com/doc_detail.cfm?item_s_key=00495115&item_key_date=920616

"""

use_faircoins = settings.USE_FAIRCOINS
FAIRCOIN_DIVISOR = Decimal("1000000.00")


# class Stage(models.Model):
#    name = models.CharField(_('name'), max_length=32)
#    sequence = models.IntegerField(_('sequence'), default=0)


#    class Meta:
#        ordering = ('sequence',)

#    def __str__(self):
#        return self.name




# for help text









# todo: rethink?
ACTIVITY_CHOICES = (
    ('active', _('active contributor')),
    ('affiliate', _('close affiliate')),
    ('inactive', _('inactive contributor')),
    ('passive', _('passive agent')),
    ('external', _('external agent')),
)








# MATERIALITY_CHOICES = (
#    ('intellectual', _('intellectual')),
#    ('material', _('material')),
#    ('purchmatl', _('purchased material')),
#    ('purchtool', _('purchased tool')),
#    ('space', _('space')),
#    ('tool', _('tool')),
#    ('value', _('value')),
#    ('work', _('work')),
# )























class ResourceTypeSpecialPrice(models.Model):
    resource_type = models.ForeignKey(EconomicResourceType,
                                      verbose_name=_('resource type'), related_name='prices')
    identifier = models.CharField(_('identifier'), max_length=128)
    description = models.TextField(_('description'), blank=True, null=True)
    price_per_unit = models.DecimalField(_('price per unit'), max_digits=8, decimal_places=2,
                                         default=Decimal("0.00"))
    stage = models.ForeignKey(ProcessType, related_name="price_at_stage",
                              verbose_name=_('stage'), blank=True, null=True)


@python_2_unicode_compatible
class AgentResourceRole(models.Model):
    agent = models.ForeignKey("EconomicAgent",
                              verbose_name=_('agent'), related_name='agent_resource_roles')
    resource = models.ForeignKey("EconomicResource",
                                 verbose_name=_('resource'), related_name='agent_resource_roles')
    role = models.ForeignKey("AgentResourceRoleType",
                             verbose_name=_('role'), related_name='agent_resource_roles')
    is_contact = models.BooleanField(_('is contact'), default=False)
    owner_percentage = models.IntegerField(_('owner percentage'), null=True)

    def __str__(self):
        return " ".join([self.agent.name, self.role.name, self.resource.__str__()])


class ProcessManager(models.Manager):
    def unfinished(self):
        return Process.objects.filter(finished=False)

    def finished(self):
        return Process.objects.filter(finished=True)

    def current(self):
        return Process.objects.filter(finished=False).filter(start_date__lte=datetime.date.today()).filter(
            end_date__gte=datetime.date.today())

    def current_or_future(self):
        return Process.objects.filter(finished=False).filter(end_date__gte=datetime.date.today())

    def current_or_future_with_use(self):
        # import pdb; pdb.set_trace()
        processes = Process.objects.current_or_future()
        ids = []
        use_et = EventType.objects.get(name="Resource use")
        for process in processes:
            if process.process_pattern:
                if use_et in process.process_pattern.event_types():
                    ids.append(process.id)
        return Process.objects.filter(pk__in=ids)


@python_2_unicode_compatible
class TransferTypeFacetValue(models.Model):
    transfer_type = models.ForeignKey(TransferType,
                                      verbose_name=_('transfer type'), related_name='facet_values')
    facet_value = models.ForeignKey(FacetValue,
                                    verbose_name=_('facet value'), related_name='transfer_types')

    class Meta:
        unique_together = ('transfer_type', 'facet_value')
        ordering = ('transfer_type', 'facet_value')

    def __str__(self):
        return ": ".join([self.transfer_type.name, self.facet_value.facet.name, self.facet_value.value])


@python_2_unicode_compatible
class Feature(models.Model):
    name = models.CharField(_('name'), max_length=128)
    # todo: replace with ___? something
    # option_category = models.ForeignKey(Category,
    #    verbose_name=_('option category'), related_name='features',
    #    blank=True, null=True,
    #    help_text=_("option selections will be limited to this category"),
    #    limit_choices_to=Q(applies_to='Anything') | Q(applies_to='EconomicResourceType'))
    product = models.ForeignKey(EconomicResourceType,
                                related_name="features", verbose_name=_('product'))
    process_type = models.ForeignKey(ProcessType,
                                     blank=True, null=True,
                                     verbose_name=_('process type'), related_name='features')
    event_type = models.ForeignKey(EventType,
                                   verbose_name=_('event type'), related_name='features')
    quantity = models.DecimalField(_('quantity'), max_digits=8, decimal_places=2, default=Decimal('0.00'))
    unit_of_quantity = models.ForeignKey(Unit, blank=True, null=True,
                                         verbose_name=_('unit'), related_name="feature_units")
    created_by = models.ForeignKey(User, verbose_name=_('created by'),
                                   related_name='features_created', blank=True, null=True, editable=False)
    changed_by = models.ForeignKey(User, verbose_name=_('changed by'),
                                   related_name='features_changed', blank=True, null=True, editable=False)
    created_date = models.DateField(auto_now_add=True, blank=True, null=True, editable=False)
    changed_date = models.DateField(auto_now=True, blank=True, null=True, editable=False)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return " ".join([self.name, "Feature for", self.product.name])

    def xbill_child_object(self):
        return self

    def xbill_class(self):
        return "feature"

    def xbill_parent_object(self):
        return self.process_type

    def xbill_children(self):
        return self.options.all()

    def xbill_explanation(self):
        return "Feature"

    def xbill_label(self):
        abbrev = ""
        if self.unit_of_quantity:
            abbrev = self.unit_of_quantity.abbrev
        return " ".join([str(self.quantity), abbrev])

    # def xbill_category(self):
    #    return Category(name="features")

    def node_id(self):
        return "-".join(["Feature", str(self.id)])

    def xbill_parents(self):
        return [self.process_type, self]

    def options_form(self):
        from django_rea.valueaccounting.forms import OptionsForm
        return OptionsForm(feature=self)

    def options_change_form(self):
        from django_rea.valueaccounting.forms import OptionsForm
        option_ids = self.options.values_list('component__id', flat=True)
        init = {'options': option_ids, }
        return OptionsForm(feature=self, initial=init)

    def xbill_change_prefix(self):
        return "".join(["FTR", str(self.id)])

    def xbill_change_form(self):
        from django_rea.valueaccounting.forms import FeatureForm
        # return FeatureForm(instance=self, prefix=self.xbill_change_prefix())
        return FeatureForm(instance=self)


class Option(models.Model):
    feature = models.ForeignKey(Feature,
                                related_name="options", verbose_name=_('feature'))
    component = models.ForeignKey(EconomicResourceType,
                                  related_name="options", verbose_name=_('component'))
    created_by = models.ForeignKey(User, verbose_name=_('created by'),
                                   related_name='options_created', blank=True, null=True, editable=False)
    changed_by = models.ForeignKey(User, verbose_name=_('changed by'),
                                   related_name='options_changed', blank=True, null=True, editable=False)
    created_date = models.DateField(auto_now_add=True, blank=True, null=True, editable=False)
    changed_date = models.DateField(auto_now=True, blank=True, null=True, editable=False)

    class Meta:
        ordering = ('component',)

    def __str__(self):
        return " ".join([self.component.name, "option for", self.feature.name])

    def xbill_child_object(self):
        return self.component

    def xbill_class(self):
        return "option"

    def xbill_parent_object(self):
        return self.feature

    def xbill_children(self):
        return self.component.xbill_children()

    def xbill_explanation(self):
        return "Option"

    def xbill_label(self):
        return ""

    # def xbill_category(self):
    #    return Category(name="features")

    def node_id(self):
        return "-".join(["Option", str(self.id)])

    def xbill_parents(self):
        return [self.feature, self]


class SelectedOption(models.Model):
    commitment = models.ForeignKey(Commitment,
                                   related_name="options", verbose_name=_('commitment'))
    option = models.ForeignKey(Option,
                               related_name="commitments", verbose_name=_('option'))

    class Meta:
        ordering = ('commitment', 'option')

    def __str__(self):
        return " ".join([self.option.name, "option for", self.commitment.resource_type.name])


def check_summary(agent, context_agent, resource_type, event_type):
    events = EconomicEvent.objects.filter(
        from_agent=agent,
        context_agent=context_agent,
        resource_type=resource_type,
        event_type=event_type,
        is_contribution=True)
    total = sum(event.quantity for event in events)
    try:
        summary = CachedEventSummary.objects.filter(
            agent=agent,
            context_agent=context_agent,
            resource_type=resource_type,
            event_type=event_type)
        if summary.count() > 1:
            sids = [str(s.id) for s in summary]
            sidstring = ",".join(sids)
            return " ".join(["More than one Summary. Ids:", sidstring, "Event total:", str(total)])
        summary = summary[0]
        if summary.quantity != total:
            return " ".join(["summary.quantity:", str(summary.quantity), "event total:", str(total)])
    except CachedEventSummary.DoesNotExist:
        return " ".join(["Summary does not exist. Event total:", str(total)])
    return "ok"


def check_events_for_summary(summary):
    events = EconomicEvent.objects.filter(
        from_agent=summary.agent,
        context_agent=summary.context_agent,
        resource_type=summary.resource_type,
        event_type=summary.event_type,
        is_contribution=True)
    total = sum(event.quantity for event in events)
    if summary.quantity != total:
        return " ".join(["summary.quantity:", str(summary.quantity), "event total:", str(total)])
    return "ok"


def update_summary(agent, context_agent, resource_type, event_type):
    events = EconomicEvent.objects.filter(
        from_agent=agent,
        context_agent=context_agent,
        resource_type=resource_type,
        event_type=event_type,
        is_contribution=True)
    total = sum(event.quantity for event in events)
    summary, created = CachedEventSummary.objects.get_or_create(
        agent=agent,
        context_agent=context_agent,
        resource_type=resource_type,
        event_type=event_type)
    summary.quantity = total
    if summary.quantity:
        summary.save()
    else:
        summary.delete()

    # todo: not used
    # class Compensation(models.Model):
    """One EconomicEvent compensating another.

    The EconomicAgents in the exchanging events
    must be opposites.
    That is, the from_agent of one event must be
    the to-agent of the other event, and vice versa.
    Both events must use the same unit of value.
    Compensation events have a M:M relationship:
    that is, one event can be compensated by many other events,
    and the other events can compensate many initiating events.

    Compensation is an REA Duality.

    """


#    initiating_event = models.ForeignKey(EconomicEvent,
#        related_name="initiated_compensations", verbose_name=_('initiating event'))
#    compensating_event = models.ForeignKey(EconomicEvent,
#        related_name="compensations", verbose_name=_('compensating event'))
#    compensation_date = models.DateField(_('compensation date'), default=datetime.date.today)
#    compensating_value = models.DecimalField(_('compensating value'), max_digits=8, decimal_places=2)

#    class Meta:
#        ordering = ('compensation_date',)

#    def __str__(self):
#        value_string = '$' + str(self.compensating_value)
#        return ' '.join([
#            'inititating event:',
#            self.initiating_event.__str__(),
#            'compensating event:',
#            self.compensating_event.__str__(),
#            'value:',
#            value_string,
#        ])

#    def clean(self):
#        #import pdb; pdb.set_trace()
#        if self.initiating_event.from_agent.id != self.compensating_event.to_agent.id:
#            raise ValidationError('Initiating event from_agent must be the compensating event to_agent.')
#        if self.initiating_event.to_agent.id != self.compensating_event.from_agent.id:
#            raise ValidationError('Initiating event to_agent must be the compensating event from_agent.')
#        #if self.initiating_event.unit_of_value.id != self.compensating_event.unit_of_value.id:
#        #    raise ValidationError('Initiating event and compensating event must have the same units of value.')







