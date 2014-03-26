import datetime
import re
from decimal import *
from operator import attrgetter

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.template.defaultfilters import slugify

from easy_thumbnails.fields import ThumbnailerImageField


"""Models based on REA

These models are based on the Bill McCarthy's Resource-Event-Agent accounting model:
https://www.msu.edu/~mccarth4/
http://en.wikipedia.org/wiki/Resources,_events,_agents_(accounting_model)

REA is also the basis for ISO/IEC FDIS 15944-4 ACCOUNTING AND ECONOMIC ONTOLOGY
http://global.ihs.com/doc_detail.cfm?item_s_key=00495115&item_key_date=920616

"""

def unique_slugify(instance, value, slug_field_name='slug', queryset=None,
                   slug_separator='-'):
    """
    Calculates a unique slug of ``value`` for an instance.

    ``slug_field_name`` should be a string matching the name of the field to
    store the slug in (and the field to check against for uniqueness).

    ``queryset`` usually doesn't need to be explicitly provided - it'll default
    to using the ``.all()`` queryset from the model's default manager.
    """
    slug_field = instance._meta.get_field(slug_field_name)

    slug = getattr(instance, slug_field.attname)
    slug_len = slug_field.max_length

    # Sort out the initial slug. Chop its length down if we need to.
    slug = slugify(value)
    if slug_len:
        slug = slug[:slug_len]
    slug = _slug_strip(slug, slug_separator)
    original_slug = slug

    # Create a queryset, excluding the current instance.
    if not queryset:
        queryset = instance.__class__._default_manager.all()
        if instance.pk:
            queryset = queryset.exclude(pk=instance.pk)

    # Find a unique slug. If one matches, at '-2' to the end and try again
    # (then '-3', etc).
    next = 2
    while not slug or queryset.filter(**{slug_field_name: slug}):
        slug = original_slug
        end = '-%s' % next
        if slug_len and len(slug) + len(end) > slug_len:
            slug = slug[:slug_len-len(end)]
            slug = _slug_strip(slug, slug_separator)
        slug = '%s%s' % (slug, end)
        next += 1

    setattr(instance, slug_field.attname, slug)


def _slug_strip(value, separator=None):
    """
    Cleans up a slug by removing slug separator characters that occur at the
    beginning or end of a slug.

    If an alternate separator is used, it will also replace any instances of
    the default '-' separator with the new separator.
    """
    if separator == '-' or not separator:
        re_sep = '-'
    else:
        re_sep = '(?:-|%s)' % re.escape(separator)
        value = re.sub('%s+' % re_sep, separator, value)
    return re.sub(r'^%s+|%s+$' % (re_sep, re_sep), '', value)


#class Stage(models.Model):
#    name = models.CharField(_('name'), max_length=32)
#    sequence = models.IntegerField(_('sequence'), default=0)
    

#    class Meta:
#        ordering = ('sequence',)
     
#    def __unicode__(self):
#        return self.name
        

#for help text
PAGE_CHOICES = (
    ('home', _('Home')),
    ('demand', _('Demand')),
    ('supply', _('Supply')),
    ('inventory', _('Inventory')),
    ('resource_types', _('Resource Types')),
    ('edit_recipes', _('Edit Recipes')),
    ('recipes', _('Recipes')),
    ('projects', _('Projects')),
    ('my_work', _('My Work')),
    ('labnotes', _('Labnotes Form')),
    ('labnote', _('Labnote view page')),
    ('all_work', _('All Work')),
    ('process', _('Process')),
    ('exchange', _('Exchange')),
)

class Help(models.Model):
    page = models.CharField(_('page'), max_length=16, choices=PAGE_CHOICES, unique=True)
    description = models.TextField(_('description'), blank=True, null=True)

    class Meta:
        verbose_name_plural = _('help')
        ordering = ('page',)
     
    def __unicode__(self):
        return self.get_page_display()


class Facet(models.Model):
    name = models.CharField(_('name'), max_length=32, unique=True)
    description = models.TextField(_('description'), blank=True, null=True)

    class Meta:
        ordering = ('name',)

    def __unicode__(self):
        return self.name

    def value_list(self):
        return ", ".join([fv.value for fv in self.values.all()])


class FacetValue(models.Model):
    facet = models.ForeignKey(Facet,
        verbose_name=_('facet'), related_name='values')
    value = models.CharField(_('value'), max_length=32)
    description = models.TextField(_('description'), blank=True, null=True)

    class Meta:
        unique_together = ('facet', 'value')
        ordering = ('facet', 'value')

    def __unicode__(self):
        return ": ".join([self.facet.name, self.value])


UNIT_TYPE_CHOICES = (
    ('area', _('area')),
    ('length', _('length')),
    ('quantity', _('quantity')),
    ('time', _('time')),
    ('value', _('value')),
    ('volume', _('volume')),
    ('weight', _('weight')),
    ('ip', _('ip')),
)
 
class Unit(models.Model):
    unit_type = models.CharField(_('unit type'), max_length=12, choices=UNIT_TYPE_CHOICES)
    abbrev = models.CharField(_('abbreviation'), max_length=8)
    name = models.CharField(_('name'), max_length=64)
    symbol = models.CharField(_('symbol'), max_length=1, blank=True)

    class Meta:
        ordering = ('name',)
     
    def __unicode__(self):
        return self.name


#todo: rethink?
ACTIVITY_CHOICES = (
    ('active', _('active contributor')),
    ('affiliate', _('close affiliate')),
    ('inactive', _('inactive contributor')),
    ('passive', _('passive agent')),
    ('external', _('external agent')),
)

SIZE_CHOICES = (
    ('individual', _('individual')),
    ('org', _('organization')),
    ('network', _('network')),
    ('team', _('project team')),
    ('community', _('community')),
)


class Location(models.Model):
    name = models.CharField(_('name'), max_length=128, unique=True)
    description = models.TextField(_('description'), blank=True, null=True)
    address = models.CharField(max_length=255, blank=True)
    latitude = models.FloatField(default=0.0, blank=True, null=True)
    longitude = models.FloatField(default=0.0, blank=True, null=True)

    def __unicode__(self):
        return self.name

    def resources(self):
        return self.resources_at_location.all()

class AgentType(models.Model):
    name = models.CharField(_('name'), max_length=128)
    parent = models.ForeignKey('self', blank=True, null=True, 
        verbose_name=_('parent'), related_name='sub-agents', editable=False)
    member_type = models.CharField(_('member type'), 
        max_length=12, choices=ACTIVITY_CHOICES,
        default='active')
    party_type = models.CharField(_('party type'), 
        max_length=12, choices=SIZE_CHOICES,
        default='individual')

    class Meta:
        ordering = ('name',)

    def __unicode__(self):
        return self.name


class AgentManager(models.Manager):

    def without_user(self):
        #import pdb; pdb.set_trace()
        all_agents = EconomicAgent.objects.all()
        ua_ids = []
        for agent in all_agents:
            if agent.users.all():
                ua_ids.append(agent.id)
        return EconomicAgent.objects.exclude(id__in=ua_ids)

    def active_contributors(self):
        return EconomicAgent.objects.filter(agent_type__member_type="active")

class EconomicAgent(models.Model):
    name = models.CharField(_('name'), max_length=255)
    nick = models.CharField(_('ID'), max_length=32, unique=True)
    url = models.CharField(_('url'), max_length=255, blank=True)
    agent_type = models.ForeignKey(AgentType,
        verbose_name=_('agent type'), related_name='agents')
    description = models.TextField(_('description'), blank=True, null=True)
    address = models.CharField(_('address'), max_length=255, blank=True)
    email = models.EmailField(_('email address'), max_length=96, blank=True, null=True)
    latitude = models.FloatField(_('latitude'), default=0.0, blank=True, null=True)
    longitude = models.FloatField(_('longitude'), default=0.0, blank=True, null=True)
    reputation = models.DecimalField(_('reputation'), max_digits=8, decimal_places=2, 
        default=Decimal("0.00"))
    photo = ThumbnailerImageField(_("photo"),
        upload_to='photos', blank=True, null=True)
    photo_url = models.CharField(_('photo url'), max_length=255, blank=True)
    slug = models.SlugField(_("Page name"), editable=False)
    created_date = models.DateField(_('created date'), default=datetime.date.today)
    created_by = models.ForeignKey(User, verbose_name=_('created by'),
        related_name='agents_created', blank=True, null=True, editable=False)
    changed_by = models.ForeignKey(User, verbose_name=_('changed by'),
        related_name='agents_changed', blank=True, null=True, editable=False)
    changed_date = models.DateField(auto_now=True, blank=True, null=True, editable=False)
    objects = AgentManager()
    
    class Meta:
        ordering = ('nick',)
    
    def __unicode__(self):
        return self.nick
    
    def save(self, *args, **kwargs):
        unique_slugify(self, self.nick)
        super(EconomicAgent, self).save(*args, **kwargs)

    def seniority(self):
        return (datetime.date.today() - self.created_date).days

    def node_id(self):
        return "-".join(["Agent", str(self.id)])

    def color(self):
        return "green"

    def produced_resource_type_relationships(self):
        return self.resource_types.filter(event_type__relationship='out')

    def produced_resource_types(self):
        return [ptrt.resource_type for ptrt in self.produced_resource_type_relationships()]

    def consumed_and_used_resource_type_relationships(self):
        return self.resource_types.filter(
            Q(event_type__relationship='consume')|Q(event_type__relationship='use'))

    def consumed_and_used_resource_types(self):
        return [ptrt.resource_type for ptrt in self.consumed_and_used_resource_type_relationships()]

    def xbill_parents(self):
        return self.produced_resource_type_relationships()

    def xbill_children(self):
        return []

    def xbill_class(self):
        return "economic-agent"  

    def score(self):
        return sum(art.score for art in self.resource_types.all())

    def contributions(self):
        return self.given_events.filter(is_contribution=True)

    def user(self):
        users = self.users.all()
        if users:
            return users[0]
        else:
            return None

    def worked_processes(self):
        cts = self.given_commitments.all()
        events = self.given_events.all()
        processes = [x.process for x in cts if x.process]
        processes.extend([x.process for x in events if x.process])
        return list(set(processes))
        
    def active_processes(self):
        return [p for p in self.worked_processes() if p.finished==False]


class AgentUser(models.Model):
    agent = models.ForeignKey(EconomicAgent,
        verbose_name=_('agent'), related_name='users')
    user = models.OneToOneField(User, 
        verbose_name=_('user'), related_name='agent')


class AssociationType(models.Model):
    name = models.CharField(_('name'), max_length=128)


class AgentAssociation(models.Model):
    from_agent = models.ForeignKey(EconomicAgent,
        verbose_name=_('from'), related_name='associations_from')
    to_agent = models.ForeignKey(EconomicAgent,
        verbose_name=_('to'), related_name='associations_to')
    association_type = models.ForeignKey(AssociationType,
        verbose_name=_('association type'), related_name='associations')
    description = models.TextField(_('description'), blank=True, null=True)


DIRECTION_CHOICES = (
    ('in', _('input')),
    ('consume', _('consume')),
    ('use', _('use')),
    ('out', _('output')),
    ('cite', _('citation')),
    ('work', _('work')),
    ('todo', _('todo')),
    ('pay', _('payment')),
    ('receive', _('receipt')),
    ('expense', _('expense')),
    ('cash', _('cash contribution')),
    ('resource', _('resource contribution')),
)

RELATED_CHOICES = (
    ('process', _('process')),
    ('agent', _('agent')), #not used logically as an event type, rather for agent - resource type relationships
    ('exchange', _('exchange')),
)

RESOURCE_EFFECT_CHOICES = (
    ('+', _('increase')),
    ('-', _('decrease')),
    ('x', _('transfer')), #means - for from_agent, + for to_agent
    ('=', _('no effect')),
    ('<', _('failure')),
)


class EventTypeManager(models.Manager):

    def get_by_natural_key(self, name):
        return self.get(name=name)


class EventType(models.Model):
    name = models.CharField(_('name'), max_length=128)
    label = models.CharField(_('label'), max_length=32)
    inverse_label = models.CharField(_('inverse label'), max_length=40, blank=True)
    relationship = models.CharField(_('relationship'), 
        max_length=12, choices=DIRECTION_CHOICES, default='in')
    related_to = models.CharField(_('related to'), 
        max_length=12, choices=RELATED_CHOICES, default='process')
    resource_effect = models.CharField(_('resource effect'), 
        max_length=12, choices=RESOURCE_EFFECT_CHOICES)
    unit_type = models.CharField(_('unit type'), 
        max_length=12, choices=UNIT_TYPE_CHOICES,
        blank=True)
    slug = models.SlugField(_("Page name"), editable=False)

    objects = EventTypeManager()

    class Meta:
        ordering = ('label',)

    def natural_key(self):
        return (self.name)

    def __unicode__(self):
        return self.label

    def save(self, *args, **kwargs):
        unique_slugify(self, self.name)
        super(EventType, self).save(*args, **kwargs)

    @classmethod
    def create(cls, name, label, inverse_label, relationship, related_to, resource_effect, unit_type, verbosity=2):
        """  
        Creates a new EventType, updates an existing one, or does nothing.
        This is intended to be used as a post_syncdb manangement step.
        """
        try:
            event_type = cls._default_manager.get(name=name)
            updated = False
            if name != event_type.name:
                event_type.name = name
                updated = True
            if label != event_type.label:
                event_type.label = label
                updated = True
            if inverse_label != event_type.inverse_label:
                event_type.inverse_label = inverse_label
                updated = True
            if relationship != event_type.relationship:
                event_type.relationship = relationship
                updated = True
            if related_to != event_type.related_to:
                event_type.related_to = related_to
                updated = True
            if resource_effect != event_type.resource_effect:
                event_type.resource_effect = resource_effect
                updated = True
            if unit_type != event_type.unit_type:
                event_type.unit_type = unit_type
                updated = True
            if updated:
                event_type.save()
                if verbosity > 1:
                    print "Updated %s EventType" % name
        except cls.DoesNotExist:
            cls(name=name, label=label, inverse_label=inverse_label, relationship=relationship,
                related_to=related_to, resource_effect=resource_effect, unit_type=unit_type).save()
            if verbosity > 1:
                print "Created %s EventType" % name

    def creates_resources(self):
        return self.resource_effect == "+"

    def consumes_resources(self):
        return self.resource_effect == "-"


class AccountingReference(models.Model):
    code = models.CharField(_('code'), max_length=128, unique=True)
    name = models.CharField(_('name'), max_length=128)

    def __unicode__(self):
        return self.name


#MATERIALITY_CHOICES = (
#    ('intellectual', _('intellectual')),
#    ('material', _('material')),
#    ('purchmatl', _('purchased material')),
#    ('purchtool', _('purchased tool')),
#    ('space', _('space')),
#    ('tool', _('tool')),
#    ('value', _('value')),
#    ('work', _('work')),
#)

INVENTORY_RULE_CHOICES = (
    ('yes', _('Keep inventory')),
    ('no', _('Not worth it')),
    ('never', _('Does not apply')),
)

class EconomicResourceType(models.Model):
    name = models.CharField(_('name'), max_length=128, unique=True)
    #version = models.CharField(_('version'), max_length=32, blank=True)    
    parent = models.ForeignKey('self', blank=True, null=True, 
        verbose_name=_('parent'), related_name='children', editable=False)
    #stage = models.ForeignKey(Stage, blank=True, null=True, 
    #    verbose_name=_('stage'), related_name='resource_types')
    #category = models.ForeignKey(Category, 
    #    verbose_name=_('category'), related_name='resource_types',
    #    limit_choices_to=Q(applies_to='Anything') | Q(applies_to='EconomicResourceType'))
    unit = models.ForeignKey(Unit, blank=True, null=True,
        verbose_name=_('unit'), related_name="resource_units",
        help_text=_('if this resource has different units of use and inventory, this is the unit of inventory'))
    unit_of_use = models.ForeignKey(Unit, blank=True, null=True,
        verbose_name=_('unit of use'), related_name="units_of_use",
        help_text=_('if this resource has different units of use and inventory, this is the unit of use'))
    substitutable = models.BooleanField(_('substitutable'), default=True,
        help_text=_('Can any resource of this type be substituted for any other resource of this type?'))
    inventory_rule = models.CharField(_('inventory rule'), max_length=5,
        choices=INVENTORY_RULE_CHOICES, default='yes')
    photo = ThumbnailerImageField(_("photo"),
        upload_to='photos', blank=True, null=True)
    photo_url = models.CharField(_('photo url'), max_length=255, blank=True)
    url = models.CharField(_('url'), max_length=255, blank=True)
    description = models.TextField(_('description'), blank=True, null=True)
    rate = models.DecimalField(_('rate'), max_digits=6, decimal_places=2, default=Decimal("0.00"), editable=False)
    accounting_reference = models.ForeignKey(AccountingReference, blank=True, null=True,
        verbose_name=_('accounting reference'), related_name="resource_types",
        help_text=_('optional reference to an external account'))
    created_by = models.ForeignKey(User, verbose_name=_('created by'),
        related_name='resource_types_created', blank=True, null=True, editable=False)
    changed_by = models.ForeignKey(User, verbose_name=_('changed by'),
        related_name='resource_types_changed', blank=True, null=True, editable=False)
    created_date = models.DateField(auto_now_add=True, blank=True, null=True, editable=False)
    changed_date = models.DateField(auto_now=True, blank=True, null=True, editable=False)
    slug = models.SlugField(_("Page name"), editable=False)


    class Meta:
        ordering = ('name',)
        verbose_name = _('resource type')
    
    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('resource_type', (),
            { 'resource_type_id': str(self.id),})

    def label(self):
        return self.__unicode__()

    def save(self, *args, **kwargs):
        #unique_slugify(self, self.name)
        super(EconomicResourceType, self).save(*args, **kwargs)

    def children(self):
        return self.children.all()

    def node_id(self):
        return "-".join(["ResourceType", str(self.id)])

    def color(self):
        return "red"

    def onhand(self):
        return EconomicResource.goods.filter(
            resource_type=self,
            quantity__gt=0)

    def all_resources(self):
        return self.resources.all()

    def onhand_qty(self):
        return sum(oh.quantity for oh in self.onhand())

    def onhand_qty_for_commitment(self, commitment):
        oh_qty = self.onhand_qty()
        due_date = commitment.due_date
        priors = self.consuming_commitments().filter(due_date__lt=due_date)
        remainder = oh_qty - sum(p.quantity for p in priors)
        if remainder > 0:
            return remainder
        else:
            return Decimal("0")

    def scheduled_qty_for_commitment(self, commitment):
        #import pdb; pdb.set_trace()
        due_date = commitment.due_date
        sked_rcts = self.producing_commitments().filter(due_date__lte=due_date).exclude(id=commitment.id)
        sked_qty = sum(pc.quantity for pc in sked_rcts)
        if not sked_qty:
            return Decimal("0")
        priors = self.consuming_commitments().filter(due_date__lt=due_date)
        remainder = sked_qty - sum(p.quantity for p in priors)
        if remainder > 0:
            return remainder
        else:
            return Decimal("0")

    def producing_process_type_relationships(self):
        return self.process_types.filter(event_type__relationship='out')

    def main_producing_process_type_relationship(self):
        ptrts = self.producing_process_type_relationships()
        if ptrts:
            return ptrts[0]
        else:
            return None

    def producing_process_types(self):
        return [pt.process_type for pt in self.producing_process_type_relationships()]

    def main_producing_process_type(self):
        pts = self.producing_process_types()
        if pts:
            return pts[0]
        else:
            return None

    def is_process_output(self):
        #import pdb; pdb.set_trace()
        #todo: does this still return false positives?
        fvs = self.facets.all()
        for fv in fvs:
            pfvs = fv.facet_value.patterns.filter(
                event_type__related_to="process",
                event_type__relationship="out")
            if pfvs:
                for pf in pfvs:
                    pattern = pf.pattern
                    if self in pattern.output_resource_types():
                        return True
        return False

    def is_purchased(self):
        #import pdb; pdb.set_trace()
        #todo: does this still return false positives?
        fvs = self.facets.all()
        for fv in fvs:
            pfvs = fv.facet_value.patterns.filter(
                event_type__related_to="agent",
                event_type__relationship="in")
            if pfvs:
                for pf in pfvs:
                    pattern = pf.pattern
                    if self in pattern.input_resource_types():
                        return True
        return False
        
    def consuming_process_type_relationships(self):
        return self.process_types.filter(event_type__resource_effect='-')

    def citing_process_type_relationships(self):
        return self.process_types.filter(event_type__relationship='cite')

    def wanting_process_type_relationships(self):
        return self.process_types.exclude(event_type__relationship='out')

    def wanting_commitments(self):
        return self.commitments.filter(
            finished=False).exclude(event_type__relationship='out')

    def wanting_processes(self):
        processes = [c.process for c in self.wanting_commitments() if c.process]
        events = self.events.filter(quantity__gt=0).exclude(event_type__relationship='out')
        processes.extend([e.process for e in events if e.process])
        return list(set(processes))

    def consuming_commitments(self):
        return self.commitments.filter(
            finished=False, event_type__resource_effect='-')

    def wanting_process_type_relationships(self):
        return self.process_types.exclude(event_type__relationship='out')

    def wanting_process_types(self):
        return [pt.process_type for pt in self.wanting_process_type_relationships()]

    def consuming_process_types(self):
        return [pt.process_type for pt in self.consuming_process_type_relationships()]

    def producing_agent_relationships(self):
        return self.agents.filter(event_type__relationship='out')

    def consuming_agent_relationships(self):
        return self.agents.filter(event_type__relationship='in')

    def consuming_agents(self):
        return [art.agent for art in self.consuming_agent_relationships()]

    def producing_agents(self):
        return [art.agent for art in self.producing_agent_relationships()]

    def producer_relationships(self):
        return self.agents.filter(event_type__relationship='out')

    def producers(self):
        arts = self.producer_relationships()
        return [art.agent for art in arts]

    #todo: failures do not have commitments. If and when they do, the next two methods must change.
    def producing_commitments(self):
        return self.commitments.filter(
            event_type__relationship='out')

    def active_producing_commitments(self):
        return self.commitments.filter(
            event_type__relationship='out',
            process__finished=False)

    def consuming_commitments(self):
        return self.commitments.filter(
            event_type__relationship='consume')

    def citing_commitments(self):
        return self.commitments.filter(
            event_type__relationship='cite')

    def scheduled_qty(self):
        return sum(pc.quantity for pc in self.producing_commitments())

    def xbill_parents(self):
        answer = list(self.wanting_process_type_relationships())
        answer.extend(list(self.options.all()))
        #answer.append(self)
        return answer

    def xbill_children(self):
        answer = []
        answer.extend(self.producing_process_type_relationships())
        answer.extend(self.producer_relationships())
        return answer

    def xbill_child_object(self):
        return self

    def xbill_class(self):
        return "economic-resource-type"

    def xbill_parent_object(self):
        return self

    def xbill_explanation(self):
        return "Resource Type"

    def xbill_label(self):
        return ""

    def generate_xbill(self):
        from valuenetwork.valueaccounting.utils import explode_xbill_children, xbill_dfs, annotate_tree_properties
        nodes = []
        exploded = []
        #import pdb; pdb.set_trace()
        for kid in self.xbill_children():
            explode_xbill_children(kid, nodes, exploded)
        nodes = list(set(nodes))
        #import pdb; pdb.set_trace()
        to_return = []
        visited = []
        for kid in self.xbill_children():
            to_return.extend(xbill_dfs(kid, nodes, visited, 1))
        #import pdb; pdb.set_trace()
        annotate_tree_properties(to_return)
        return to_return

    def change_form(self):
        from valuenetwork.valueaccounting.forms import EconomicResourceTypeChangeForm
        return EconomicResourceTypeChangeForm(instance=self)

    def resource_create_form(self, prefix):
        from valuenetwork.valueaccounting.forms import EconomicResourceForm
        init = {"unit_of_quantity": self.unit,}
        return EconomicResourceForm(prefix=prefix, initial=init)

    def process_create_prefix(self):
        return "".join(["PC", str(self.id)])
        
    def process_create_form(self):
        from valuenetwork.valueaccounting.forms import XbillProcessTypeForm
        init = {"name": " ".join(["Make", self.name])}
        return XbillProcessTypeForm(initial=init, prefix=self.process_create_prefix())

    def source_create_prefix(self):
        return "".join(["SRC", str(self.id)])

    def source_create_form(self):
        from valuenetwork.valueaccounting.forms import AgentResourceTypeForm
        return AgentResourceTypeForm(prefix=self.source_create_prefix())

    def directional_unit(self, direction):
        answer = self.unit
        if self.unit_of_use:
            if direction == "use":
                answer = self.unit_of_use
        return answer

    def unit_for_use(self):
        return self.directional_unit("use")

    def process_input_unit(self):
        answer = self.unit
        if self.unit_of_use:
            answer = self.unit_of_use
        return answer

    def process_output_unit(self):
        return self.unit

    def is_deletable(self):
        answer = True
        if self.events.all():
            answer = False
        elif self.resources.all():
            answer = False
        elif self.commitments.all():
            answer = False
        return answer

    def is_orphan(self):
        answer = True
        if not self.is_deletable():
            answer = False
        if self.process_types.all():
            answer = False
        return answer

    def facet_list(self):
        return ", ".join([facet.facet_value.__unicode__() for facet in self.facets.all()])

    def facet_values_list(self):
        return ", ".join([facet.facet_value.value for facet in self.facets.all()])

    def has_facet_value(self, facet_value):
        answer = False
        for rt_fv in self.facets.all():
            if rt_fv.facet_value == facet_value:
                answer = True
                break
        return answer

    def matches_filter(self, facet_values):
        #import pdb; pdb.set_trace()
        answer = True
        incoming_facets = []
        for fv in facet_values:
            incoming_facets.append(fv.facet)
        filter_facets = set(incoming_facets)
        filter_facet_value_collections = []
        for f in filter_facets:
            fv_collection = []
            for fv in facet_values:
                if fv.facet == f:
                    fv_collection.append(fv)
            filter_facet_value_collections.append(fv_collection)
        filter_matches = []
        for (i, fac) in enumerate(filter_facets):
            fm = False
            for fv in filter_facet_value_collections[i]:
                if self.has_facet_value(fv):
                    fm = True
                    break
            filter_matches.append(fm)
        if False in filter_matches:
            answer = False
        return answer


class ResourceTypeFacetValue(models.Model):
    resource_type = models.ForeignKey(EconomicResourceType, 
        verbose_name=_('resource type'), related_name='facets')
    facet_value = models.ForeignKey(FacetValue,
        verbose_name=_('facet value'), related_name='resource_types')

    class Meta:
        unique_together = ('resource_type', 'facet_value')
        ordering = ('resource_type', 'facet_value')

    def __unicode__(self):
        return ": ".join([self.resource_type.name, self.facet_value.facet.name, self.facet_value.value])


class ProcessPatternManager(models.Manager):

    def production_patterns(self):
        #import pdb; pdb.set_trace()
        use_cases = PatternUseCase.objects.filter(
            Q(use_case__identifier='rand')|Q(use_case__identifier='design'))
        pattern_ids = [uc.pattern.id for uc in use_cases]
        return ProcessPattern.objects.filter(id__in=pattern_ids)

    def usecase_patterns(self, use_case):
        #import pdb; pdb.set_trace()
        use_cases = PatternUseCase.objects.filter(
            Q(use_case=use_case))
        pattern_ids = [uc.pattern.id for uc in use_cases]
        return ProcessPattern.objects.filter(id__in=pattern_ids)
        

class ProcessPattern(models.Model):
    name = models.CharField(_('name'), max_length=32)
    objects = ProcessPatternManager()

    class Meta:
        ordering = ('name',)

    def __unicode__(self):
        return self.name

    def event_types(self):
        facets = self.facets.all()
        slots = [facet.event_type for facet in facets]
        slots = list(set(slots))
        slots.sort(lambda x, y: cmp(x.label, y.label))
        slots = sorted(slots, key=attrgetter('label'))
        slots = sorted(slots, key=attrgetter('relationship'), reverse=True)
        return slots

    def slots(self):
        return [et.relationship for et in self.event_types()]

    def get_resource_types(self, event_type):
        """Matching logic:

            A Resource Type must have a matching value
            for each Facet in the Pattern.
            If a Pattern has more than one value for the same Facet,
            the Resource Type only needs to match one of them.
            And if the Resource Type has other Facets
            that are not in the Pattern, they do not matter.
        """
        
        pattern_facet_values = self.facets_for_event_type(event_type)
        facet_values = [pfv.facet_value for pfv in pattern_facet_values]
        facets = {}
        for fv in facet_values:
            if fv.facet not in facets:
                facets[fv.facet] = []
            facets[fv.facet].append(fv.value)  
           
        fv_ids = [fv.id for fv in facet_values]
        rt_facet_values = ResourceTypeFacetValue.objects.filter(facet_value__id__in=fv_ids)

        rts = {}
        for rtfv in rt_facet_values:
            rt = rtfv.resource_type
            if rt not in rts:
                rts[rt] = []
            rts[rt].append(rtfv.facet_value)
            
        #import pdb; pdb.set_trace()
        matches = []
        
        for rt, facet_values in rts.iteritems():
            match = True
            for facet, values in facets.iteritems():
                rt_fv = [fv for fv in facet_values if fv.facet == facet]
                if rt_fv:
                    rt_fv = rt_fv[0]
                    if rt_fv.value not in values:
                        match = False
                else:
                    match = False
            if match:
                matches.append(rt)
                
        answer_ids = [a.id for a in matches]        
        answer = EconomicResourceType.objects.filter(id__in=answer_ids)       
        return answer

    def resource_types_for_relationship(self, relationship):
        #import pdb; pdb.set_trace()
        ets = [f.event_type for f in self.facets.filter(event_type__relationship=relationship)] 
        if ets:
            ets = list(set(ets))
            if len(ets) == 1:
                return self.get_resource_types(ets[0])
            else:
                rts = []
                for et in ets:
                    rts.extend(list(self.get_resource_types(et)))
                rt_ids = [rt.id for rt in rts]
                return EconomicResourceType.objects.filter(id__in=rt_ids)
        else:
            return EconomicResourceType.objects.none()

    def all_resource_types(self):
        answer = []
        ets = self.event_types()
        for et in ets:
            answer.extend(self.get_resource_types(et))
        return answer
        
    def work_resource_types(self):
        return self.resource_types_for_relationship("work")

    def todo_resource_types(self):
        return self.resource_types_for_relationship("todo")

    def citable_resource_types(self):
        return self.resource_types_for_relationship("cite")

    def citables_with_resources(self):
        rts = [rt for rt in self.citable_resource_types() if rt.onhand()]
        rt_ids = [rt.id for rt in rts]
        return EconomicResourceType.objects.filter(id__in=rt_ids)

    def citable_resources(self):
        rts = [rt for rt in self.citable_resource_types() if rt.onhand()]
        return EconomicResource.objects.filter(resource_type__in=rts)
    
    def input_resource_types(self):
        return self.resource_types_for_relationship("in")

    def consumable_resource_types(self):
        return self.resource_types_for_relationship("consume")

    def consumables_with_resources(self):
        rts = [rt for rt in self.consumable_resource_types() if rt.onhand()]
        rt_ids = [rt.id for rt in rts]
        return EconomicResourceType.objects.filter(id__in=rt_ids)

    def usable_resource_types(self):
        return self.resource_types_for_relationship("use")

    def usables_with_resources(self):
        rts = [rt for rt in self.usable_resource_types() if rt.onhand()]
        rt_ids = [rt.id for rt in rts]
        return EconomicResourceType.objects.filter(id__in=rt_ids)

    def output_resource_types(self):
        return self.resource_types_for_relationship("out")

    def payment_resource_types(self):
        return self.resource_types_for_relationship("pay")

    def receipt_resource_types(self):
        return self.resource_types_for_relationship("receive")

    def expense_resource_types(self):
        #import pdb; pdb.set_trace()
        return self.resource_types_for_relationship("expense")

    def cash_contr_resource_types(self):
        return self.resource_types_for_relationship("cash")

    def material_contr_resource_types(self):
        return self.resource_types_for_relationship("resource")

    def facets_for_event_type(self, event_type):
        return self.facets.filter(event_type=event_type)

    def facet_values_for_relationship(self, relationship):
        return self.facets.filter(event_type__relationship=relationship)

    def output_facet_values(self):
        return self.facet_values_for_relationship("out")

    def citable_facet_values(self):
        return self.facet_values_for_relationship("cite")

    def input_facet_values(self):
        return self.facet_values_for_relationship("in")

    def consumable_facet_values(self):
        return self.facet_values_for_relationship("consume")

    def usable_facet_values(self):
        return self.facet_values_for_relationship("use")

    def work_facet_values(self):
        return self.facet_values_for_relationship("work")

    def input_facets(self):
        facets = [pfv.facet_value.facet for pfv in self.input_facet_values()]
        return list(set(facets))

    def consumable_facets(self):
        facets = [pfv.facet_value.facet for pfv in self.consumable_facet_values()]
        return list(set(facets))

    def usable_facets(self):
        facets = [pfv.facet_value.facet for pfv in self.usable_facet_values()]
        return list(set(facets))

    def citable_facets(self):
        facets = [pfv.facet_value.facet for pfv in self.citable_facet_values()]
        return list(set(facets))

    def work_facets(self):
        facets = [pfv.facet_value.facet for pfv in self.work_facet_values()]
        return list(set(facets))

    def output_facets(self):
        facets = [pfv.facet_value.facet for pfv in self.output_facet_values()]
        return list(set(facets))

    def base_event_type_for_resource_type(self, relationship, resource_type):
        rt_fvs = [x.facet_value for x in resource_type.facets.all()]
        pfvs = self.facet_values_for_relationship(relationship)
        pat_fvs = [x.facet_value for x in pfvs]
        #import pdb; pdb.set_trace()
        fv_intersect = set(rt_fvs) & set(pat_fvs)
        event_type = None
        if fv_intersect:
            fv = list(fv_intersect)[0]
            pfv = pfvs.get(facet_value=fv)
            event_type = pfv.event_type
        return event_type

    def event_type_for_resource_type(self, relationship, resource_type):
        event_type = self.base_event_type_for_resource_type(relationship, resource_type)
        if not event_type:
            ets = self.event_types()
            for et in ets:
                if et.relationship == relationship:
                    event_type=et
                    break
            if not event_type:
                ets = EventType.objects.filter(relationship=relationship)
                event_type = ets[0]
        return event_type

    def use_case_list(self):
        ucl = [uc.use_case.name for uc in self.use_cases.all()]
        return ", ".join(ucl)

    def use_case_count(self):
        return self.use_cases.all().count()

    def facets_by_relationship(self, relationship):
        pfvs = self.facet_values_for_relationship(relationship)
        facets = [pfv.facet_value.facet for pfv in pfvs]
        return list(set(facets))

    def facet_values_for_facet_and_relationship(self, facet, relationship):
        fvs_all = self.facet_values_for_relationship(relationship)
        fvs_for_facet = []
        for fv in fvs_all:
            if fv.facet_value.facet == facet:
                fvs_for_facet.append(fv.facet_value)
        return fvs_for_facet

        
class PatternFacetValue(models.Model):
    pattern = models.ForeignKey(ProcessPattern, 
        verbose_name=_('pattern'), related_name='facets')
    facet_value = models.ForeignKey(FacetValue,
        verbose_name=_('facet value'), related_name='patterns')
    event_type = models.ForeignKey(EventType,
        verbose_name=_('event type'), related_name='patterns',
        help_text=_('consumed means gone, used means re-usable'))

    class Meta:
        unique_together = ('pattern', 'facet_value', 'event_type')
        ordering = ('pattern', 'event_type', 'facet_value')

    def __unicode__(self):
        return ": ".join([self.pattern.name, self.facet_value.facet.name, self.facet_value.value])


class UseCaseManager(models.Manager):

    def get_by_natural_key(self, identifier):
        #import pdb; pdb.set_trace()
        return self.get(identifier=identifier)


class UseCase(models.Model):
    identifier = models.CharField(_('identifier'), max_length=12)
    name = models.CharField(_('name'), max_length=128)
    restrict_to_one_pattern = models.BooleanField(_('restrict_to_one_pattern'), default=False)

    objects = UseCaseManager()

    def __unicode__(self):
        return self.name

    def natural_key(self):
        return (self.identifier)

    @classmethod
    def create(cls, identifier, name, restrict_to_one_pattern=False, verbosity=2):
        """  
        Creates a new UseCase, updates an existing one, or does nothing.
        This is intended to be used as a post_syncdb manangement step.
        """
        try:
            use_case = cls._default_manager.get(identifier=identifier)
            updated = False
            if name != use_case.name:
                use_case.name = name
                updated = True
            if restrict_to_one_pattern != use_case.restrict_to_one_pattern:
                use_case.restrict_to_one_pattern = restrict_to_one_pattern
                updated = True
            if updated:
                use_case.save()
                if verbosity > 1:
                    print "Updated %s UseCase" % identifier
        except cls.DoesNotExist:
            cls(identifier=identifier, name=name, restrict_to_one_pattern=restrict_to_one_pattern).save()
            if verbosity > 1:
                print "Created %s UseCase" % identifier

    def allows_more_patterns(self):
        patterns_count = self.patterns.all().count()
        if patterns_count:
            if self.restrict_to_one_pattern:
                return False
        return True

    def allowed_event_types(self):
        ucets = UseCaseEventType.objects.filter(use_case=self)
        et_ids = []
        for ucet in ucets:
            if ucet.event_type.pk not in et_ids:
                et_ids.append(ucet.event_type.pk) 
        return EventType.objects.filter(pk__in=et_ids)

    def allowed_patterns(self): #patterns must not have event types not assigned to the use case
        #import pdb; pdb.set_trace()
        allowed_ets = self.allowed_event_types()
        all_ps = ProcessPattern.objects.all()
        allowed_ps = []
        for p in all_ps:
            allow_this_pattern = True
            for et in p.event_types():
                if et not in allowed_ets:
                    allow_this_pattern = False
            if allow_this_pattern:
                allowed_ps.append(p)
        return allowed_ps


from south.signals import post_migrate

def create_use_cases(app, **kwargs):
    if app != "valueaccounting":
        return
    UseCase.create('cash_contr', _('Cash Contribution'), True) 
    UseCase.create('non_prod', _('Non-production logging'), True)
    UseCase.create('rand', _('Process logging'))
    UseCase.create('recipe', _('Recipes'))
    UseCase.create('todo', _('Todos'), True)
    UseCase.create('cust_orders', _('Customer Orders'))
    UseCase.create('purchasing', _('Purchasing')) 
    UseCase.create('res_contr', _('Material Contribution'))
    UseCase.create('purch_contr', _('Purchase Contribution'))
    UseCase.create('exp_contr', _('Expense Contribution'), True)
    print "created use cases"

post_migrate.connect(create_use_cases)

def create_event_types(app, **kwargs):
    if app != "valueaccounting":
        return
    #Keep the first column (name) as unique
    EventType.create('Citation', _('cites'), _('cited by'), 'cite', 'process', '=', '')
    EventType.create('Resource Consumption', _('consumes'), _('consumed by'), 'consume', 'process', '-', 'quantity') 
    EventType.create('Cash Contribution', _('contributes cash'), _('cash contributed by'), 'cash', 'exchange', '+', 'value') 
    EventType.create('Resource Contribution', _('contributes resource'), _('resource contributed by'), 'resource', 'exchange', '+', 'quantity') 
    EventType.create('Damage', _('damages'), _('damaged by'), 'out', 'agent', '-', 'value')  
    EventType.create('Expense', _('expense'), '', 'expense', 'exchange', '=', 'value') 
    EventType.create('Failed quantity', _('fails'), '', 'out', 'process', '<', 'quantity') 
    EventType.create('Payment', _('pays'), _('paid by'), 'pay', 'exchange', '-', 'value') 
    EventType.create('Resource Production', _('produces'), _('produced by'), 'out', 'process', '+', 'quantity') 
    EventType.create('Work Provision', _('provides'), _('provided by'), 'out', 'agent', '+', 'time') 
    EventType.create('Receipt', _('receives'), _('received by'), 'receive', 'exchange', '+', 'quantity') 
    EventType.create('Sale', _('sells'), _('sold by'), 'out', 'agent', '=', '') 
    EventType.create('Shipment', _('ships'), _('shipped by'), 'out', 'agent', '-', 'quantity') 
    EventType.create('Supply', _('supplies'), _('supplied by'), 'out', 'agent', '=', '') 
    EventType.create('Todo', _('todo'), '', 'todo', 'agent', '=', '')
    EventType.create('Resource use', _('uses'), _('used by'), 'use', 'process', '=', 'time') 
    EventType.create('Time Contribution', _('work'), '', 'work', 'process', '=', 'time') 

    print "created event types"

post_migrate.connect(create_event_types)

class UseCaseEventType(models.Model):
    use_case = models.ForeignKey(UseCase,
        verbose_name=_('use case'), related_name='event_types')
    event_type = models.ForeignKey(EventType, 
        verbose_name=_('event type'), related_name='use_cases')

    def __unicode__(self):
        return ": ".join([self.use_case.name, self.event_type.name])

    @classmethod
    def create(cls, use_case_identifier, event_type_name):
        """  
        Creates a new UseCaseEventType, updates an existing one, or does nothing.
        This is intended to be used as a post_syncdb manangement step.
        """
        try:
            use_case = UseCase.objects.get(identifier=use_case_identifier)
            event_type = EventType.objects.get(name=event_type_name)
            ucet = cls._default_manager.get(use_case=use_case, event_type=event_type)
        except cls.DoesNotExist:
            cls(use_case=use_case, event_type=event_type).save()
            #import pdb; pdb.set_trace()
            print "Created %s UseCaseEventType" % (use_case_identifier + " " + event_type_name)

def create_usecase_eventtypes(app, **kwargs):
    if app != "valueaccounting":
        return
    UseCaseEventType.create('cash_contr', 'Time Contribution') 
    UseCaseEventType.create('cash_contr', 'Cash Contribution') 
    UseCaseEventType.create('non_prod', 'Time Contribution')
    UseCaseEventType.create('rand', 'Citation')
    UseCaseEventType.create('rand', 'Resource Consumption')
    UseCaseEventType.create('rand', 'Resource Production')
    UseCaseEventType.create('rand', 'Resource use')
    UseCaseEventType.create('rand', 'Time Contribution')
    UseCaseEventType.create('recipe','Citation')
    UseCaseEventType.create('recipe', 'Resource Consumption')
    UseCaseEventType.create('recipe', 'Resource Production')
    UseCaseEventType.create('recipe', 'Resource use')
    UseCaseEventType.create('recipe', 'Time Contribution')
    UseCaseEventType.create('todo', 'Todo')
    UseCaseEventType.create('cust_orders', 'Damage')
    UseCaseEventType.create('cust_orders', 'Payment')
    UseCaseEventType.create('cust_orders', 'Receipt')
    UseCaseEventType.create('cust_orders', 'Sale')
    UseCaseEventType.create('cust_orders', 'Shipment')
    UseCaseEventType.create('purchasing', 'Payment') 
    UseCaseEventType.create('purchasing', 'Receipt') 
    UseCaseEventType.create('res_contr', 'Time Contribution')
    UseCaseEventType.create('res_contr', 'Resource Contribution')
    UseCaseEventType.create('purch_contr', 'Time Contribution')
    UseCaseEventType.create('purch_contr', 'Expense')
    UseCaseEventType.create('purch_contr', 'Payment')
    UseCaseEventType.create('purch_contr', 'Receipt')
    UseCaseEventType.create('exp_contr', 'Time Contribution')
    UseCaseEventType.create('exp_contr', 'Expense')
    UseCaseEventType.create('exp_contr', 'Payment')

    print "created use case event type associations"

post_migrate.connect(create_usecase_eventtypes)


class PatternUseCase(models.Model):
    pattern = models.ForeignKey(ProcessPattern, 
        verbose_name=_('pattern'), related_name='use_cases')
    use_case = models.ForeignKey(UseCase,
        blank=True, null=True,
        verbose_name=_('use case'), related_name='patterns')

    def __unicode__(self):
        use_case_name = ""
        if self.use_case:
            use_case_name = self.use_case.name
        return ": ".join([self.pattern.name, use_case_name])


ORDER_TYPE_CHOICES = (
    ('customer', _('Customer order')),
    ('rand', _('Work order')),
    ('holder', _('Placeholder order')),
)

#todo: Order is used for both of the above types.
#maybe shd be renamed?
class Order(models.Model):
    order_type = models.CharField(_('order type'), max_length=12, 
        choices=ORDER_TYPE_CHOICES, default='customer')
    name = models.CharField(_('name'), max_length=255, blank=True,
        help_text=_("appended to process labels for Work orders"))
    receiver = models.ForeignKey(EconomicAgent,
        blank=True, null=True,
        related_name="purchase_orders", verbose_name=_('receiver'))
    provider = models.ForeignKey(EconomicAgent,
        blank=True, null=True,
        related_name="sales_orders", verbose_name=_('provider'))
    order_date = models.DateField(_('order date'), default=datetime.date.today)
    due_date = models.DateField(_('due date'))
    description = models.TextField(_('description'), null=True, blank=True)
    created_by = models.ForeignKey(User, verbose_name=_('created by'),
        related_name='orders_created', blank=True, null=True)
    changed_by = models.ForeignKey(User, verbose_name=_('changed by'),
        related_name='orders_changed', blank=True, null=True)
    created_date = models.DateField(auto_now_add=True, blank=True, null=True, editable=False)
    changed_date = models.DateField(auto_now=True, blank=True, null=True, editable=False)

    class Meta:
        ordering = ('due_date',)

    def __unicode__(self):
        provider_name = ""
        process_name = ""
        provider_label = ""
        receiver_label = ""
        process = self.process()
        if process:
            process_name = ", " + process.name
        if self.name:
            process_name = " ".join(["for", self.name])
        if self.provider:
            provider_name = self.provider.name
            provider_label = ", provider:"
        receiver_name = ""
        if self.receiver:
            receiver_name = self.receiver.name
            receiver_label = ", receiver:"
        if self.order_type == "customer":
            provider_label = ", Seller:"
            receiver_label = ", Buyer:"
        return " ".join(
            [self.get_order_type_display(), 
            str(self.id), 
            process_name,
            provider_label, 
            provider_name, 
            receiver_label, 
            receiver_name, 
            ", due:",
            self.due_date.strftime('%Y-%m-%d'),
            ])

    @models.permalink
    def get_absolute_url(self):
        return ('order_schedule', (),
            { 'order_id': str(self.id),})

    def node_id(self):
        return "-".join(["Order", str(self.id)])

    def timeline_title(self):
        return self.__unicode__()

    def timeline_description(self):
        return self.description

    def producing_commitments(self):
        return self.commitments.all()

    def order_items(self):
        return self.commitments.all()

    def consumed_input_requirements(self):
        return []

    def used_input_requirements(self):
        return []

    def work_requirements(self):
        return []

    def process(self):
        answer = None
        if self.order_type == 'rand':
            process = None
            for item in self.producing_commitments():
                if item.process:
                    answer = item.process
                    break
        return answer

    def add_commitment(self,
            resource_type,
            quantity,
            event_type,
            unit,
            due=None):
        #todo: needs process and project. Anything else?
        #might not be worth refactoring out.
        if not due:
            due=self.due_date
        ct = Commitment(
            order=self,
            independent_demand=self,
            event_type=event_type,
            resource_type=resource_type,
            quantity=quantity,
            unit_of_quantity=unit,
            due_date=due)
        ct.save()
        #todo: shd this generate_producing_process?
        return ct

    def all_processes(self):
        #import pdb; pdb.set_trace()
        deliverables = self.commitments.filter(event_type__relationship="out")
        processes = [d.process for d in deliverables if d.process]
        roots = []
        for p in processes:
            if not p.next_processes():
                roots.append(p)
        ordered_processes = []
        visited_resources = []
        for root in roots:
            root.all_previous_processes(ordered_processes, visited_resources, 0)
        ordered_processes = list(set(ordered_processes))
        ordered_processes.sort(lambda x, y: cmp(x.start_date, y.start_date))
        return ordered_processes


class GoodResourceManager(models.Manager):
    def get_query_set(self):
        return super(GoodResourceManager, self).get_query_set().exclude(quality__lt=0)

class FailedResourceManager(models.Manager):
    def get_query_set(self):
        return super(FailedResourceManager, self).get_query_set().filter(quality__lt=0)

class EconomicResource(models.Model):
    resource_type = models.ForeignKey(EconomicResourceType, 
        verbose_name=_('resource type'), related_name='resources')
    identifier = models.CharField(_('identifier'), blank=True, max_length=128)
    independent_demand = models.ForeignKey(Order,
        blank=True, null=True,
        related_name="dependent_resources", verbose_name=_('independent_demand'))
    url = models.CharField(_('url'), max_length=255, blank=True)
    author = models.ForeignKey(EconomicAgent, related_name="authored_resources",
        verbose_name=_('author'), blank=True, null=True)
    quantity = models.DecimalField(_('quantity'), max_digits=8, decimal_places=2, 
        default=Decimal("1.00"))
    unit_of_quantity = models.ForeignKey(Unit, blank=True, null=True,
        verbose_name=_('unit of quantity'), related_name="resource_qty_units")
    quality = models.DecimalField(_('quality'), max_digits=3, decimal_places=0, 
        default=Decimal("0"), blank=True, null=True)
    notes = models.TextField(_('notes'), blank=True, null=True)
    photo = ThumbnailerImageField(_("photo"),
        upload_to='photos', blank=True, null=True)
    photo_url = models.CharField(_('photo url'), max_length=255, blank=True)
    access_rules = models.TextField(_('access rules'), blank=True, null=True)
    current_location = models.ForeignKey(Location, 
        verbose_name=_('current location'), related_name='resources_at_location', 
        blank=True, null=True)
    created_date = models.DateField(_('created date'), default=datetime.date.today)
    created_by = models.ForeignKey(User, verbose_name=_('created by'),
        related_name='resources_created', blank=True, null=True, editable=False)
    changed_by = models.ForeignKey(User, verbose_name=_('changed by'),
        related_name='resources_changed', blank=True, null=True, editable=False)
    changed_date = models.DateField(auto_now=True, blank=True, null=True, editable=False)

    objects = models.Manager()
    goods = GoodResourceManager()
    failures = FailedResourceManager()

    class Meta:
        ordering = ('resource_type', 'identifier',)
    
    def __unicode__(self):
        id_str = self.identifier or str(self.id)
        return ": ".join([
            self.resource_type.name,
            id_str,
        ])

    @models.permalink
    def get_absolute_url(self):
        return ('resource', (),
            { 'resource_id': str(self.id),})

    def label(self):
        return self.identifier or str(self.id)

    def flow_type(self):
        return "Resource"

    def flow_class(self):
        return "resource"

    def flow_description(self):
        return self.__unicode__()

    def change_form(self):
        from valuenetwork.valueaccounting.forms import EconomicResourceForm
        return EconomicResourceForm(instance=self)

    #def change_role_formset(self):
    #    from valuenetwork.valueaccounting.forms import ResourceRoleAgentForm
    #    return EconomicResourceForm(instance=self)

    def is_orphan(self):
        o = True
        if self.agent_resource_roles.all():
            o = False
        if self.commitments.all():
            o = False
        if self.events.all():
            o = False
        return o

    def producing_events(self):
        if self.quality:
            if self.quality < 0:
               return self.events.filter(event_type__resource_effect='<') 
        return self.events.filter(event_type__resource_effect='+')

    def consuming_events(self):
        return self.events.filter(event_type__relationship='consume')

    def using_events(self):
        return self.events.filter(event_type__relationship="use")

    def all_usage_events(self):
        return self.events.exclude(event_type__relationship="out").exclude(event_type__relationship="receive").exclude(event_type__relationship="resource")

    def demands(self):
        return self.resource_type.commitments.exclude(event_type__relationship="out")

    def is_cited(self):
        ces = self.events.filter(event_type__relationship="cite")
        if ces:
            return True
        else:
            return False

    def label_with_cited(self):
        if self.is_cited:
            cited = ' (Cited)'
        else:
            cited = ''
        return (self.identifier or str(self.id)) + cited

    def is_deletable(self):
        if self.events.all():
            return False
        if self.quantity != 0:
            return False
        return True

    def incoming_value_flows(self):
        flows = []
        visited = []
        depth = 0
        self.depth = depth
        flows.append(self)
        self.incoming_value_flows_dfs(flows, visited, depth)
        return flows

    def incoming_value_flows_dfs(self, flows, visited, depth):
        if not self in visited:
            visited.append(self)
            depth += 1
            resources = []
            for event in self.producing_events():
                event.depth = depth
                flows.append(event)
                p = event.process
                if p:
                    if not p in visited:
                        depth += 1
                        p.depth = depth
                        flows.append(p)
                        depth += 1
                        for evt in p.incoming_events():
                            evt.depth = depth
                            flows.append(evt)
                            if evt.resource:
                                if evt.resource not in resources:
                                    resources.append(evt.resource)
            for resource in resources:
                resource.incoming_value_flows_dfs(flows, visited, depth)

    def form_prefix(self):
        return "-".join(["RES", str(self.id)])

    def consumption_event_form(self):        
        from valuenetwork.valueaccounting.forms import InputEventForm
        prefix=self.form_prefix()
        qty_help = " ".join(["unit:", self.unit_of_quantity.abbrev])
        return InputEventForm(qty_help=qty_help, prefix=prefix)

    def use_event_form(self):        
        from valuenetwork.valueaccounting.forms import TimeEventForm, InputEventForm
        prefix=self.form_prefix()
        unit = self.resource_type.directional_unit("use")
        if unit.unit_type == "time":
            return TimeEventForm(prefix=prefix)
        else:
            qty_help = " ".join(["unit:", unit.abbrev])
            return InputEventForm(qty_help=qty_help, prefix=prefix)  


class AgentResourceType(models.Model):
    agent = models.ForeignKey(EconomicAgent,
        verbose_name=_('agent'), related_name='resource_types')
    resource_type = models.ForeignKey(EconomicResourceType, 
        verbose_name=_('resource type'), related_name='agents')
    score = models.DecimalField(_('score'), max_digits=8, decimal_places=2, 
        default=Decimal("0.0"),
        help_text=_("the quantity of contributions of this resource type from this agent"))
    event_type = models.ForeignKey(EventType,
        verbose_name=_('event type'), related_name='agent_resource_types')
    lead_time = models.IntegerField(_('lead time'), 
        default=0, help_text=_("in days"))
    value = models.DecimalField(_('value'), max_digits=8, decimal_places=2, 
        default=Decimal("0.0"))
    unit_of_value = models.ForeignKey(Unit, blank=True, null=True,
        limit_choices_to={'unit_type': 'value'},
        verbose_name=_('unit of value'), related_name="agent_resource_value_units")
    description = models.TextField(_('description'), null=True, blank=True)
    created_by = models.ForeignKey(User, verbose_name=_('created by'),
        related_name='arts_created', blank=True, null=True, editable=False)
    changed_by = models.ForeignKey(User, verbose_name=_('changed by'),
        related_name='arts_changed', blank=True, null=True, editable=False)
    created_date = models.DateField(auto_now_add=True, blank=True, null=True, editable=False)
    changed_date = models.DateField(auto_now=True, blank=True, null=True, editable=False)

    def __unicode__(self):
        return ' '.join([
            self.agent.name,
            self.event_type.label,
            self.resource_type.name,
        ])

    def label(self):
        return "source"

    def timeline_title(self):
        return " ".join(["Get ", self.resource_type.name, "from ", self.agent.name])

    def inverse_label(self):
        return self.event_type.inverse_label()

    def xbill_label(self):
        #return self.event_type.infer_label()
        return ""

    def xbill_explanation(self):
        return "Possible source"

    def xbill_child_object(self):
        if self.event_type.relationship == 'out':
            return self.agent
        else:
            return self.resource_type

    def xbill_class(self):
        return self.xbill_child_object().xbill_class()

    def xbill_parent_object(self):
        if self.event_type.relationship == 'out':
            return self.resource_type
        else:
            return self.agent

    def node_id(self):
        return "-".join(["AgentResource", str(self.id)])

    def xbill_change_prefix(self):
        return "".join(["AR", str(self.id)])

    def xbill_change_form(self):
        from valuenetwork.valueaccounting.forms import AgentResourceTypeForm
        return AgentResourceTypeForm(instance=self, prefix=self.xbill_change_prefix())

    def total_required(self):
        commitments = Commitment.objects.unfinished().filter(resource_type=self.resource_type)
        return sum(req.unfilled_quantity() for req in commitments)

    def comparative_scores(self):
        scores = AgentResourceType.objects.filter(resource_type=self.resource_type).values_list('score', flat=True)
        average = str((sum(scores) / len(scores)).quantize(Decimal('.01'), rounding=ROUND_UP))
        return "".join([
            "Min: ", str(min(scores).quantize(Decimal('.01'), rounding=ROUND_UP)), 
            ", Average: ", average, 
            ", Max: ", str(max(scores).quantize(Decimal('.01'), rounding=ROUND_UP)),
            ]) 
   

class AgentResourceRoleType(models.Model):
    name = models.CharField(_('name'), max_length=128)
    description = models.TextField(_('description'), blank=True, null=True)

    def __unicode__(self):
        return self.name


class AgentResourceRole(models.Model):     
    agent = models.ForeignKey(EconomicAgent,
        verbose_name=_('agent'), related_name='agent_resource_roles')
    resource = models.ForeignKey(EconomicResource, 
        verbose_name=_('resource'), related_name='agent_resource_roles')
    role = models.ForeignKey(AgentResourceRoleType, 
        verbose_name=_('role'), related_name='agent_resource_roles')
    is_contact = models.BooleanField(_('is contact'), default=False)


class Project(models.Model):
    name = models.CharField(_('name'), max_length=128) 
    description = models.TextField(_('description'), blank=True, null=True)
    parent = models.ForeignKey('self', blank=True, null=True, 
        verbose_name=_('parent'), related_name='sub_projects')
    project_team = models.ForeignKey(EconomicAgent,
        blank=True, null=True,
        related_name="project_team", verbose_name=_('project team'))
    importance = models.DecimalField(_('importance'), max_digits=3, decimal_places=0, default=Decimal("0"))
    created_by = models.ForeignKey(User, verbose_name=_('created by'),
        related_name='projects_created', blank=True, null=True, editable=False)
    changed_by = models.ForeignKey(User, verbose_name=_('changed by'),
        related_name='projects_changed', blank=True, null=True, editable=False)
    created_date = models.DateField(auto_now_add=True, blank=True, null=True, editable=False)
    changed_date = models.DateField(auto_now=True, blank=True, null=True, editable=False)
    slug = models.SlugField(_("Page name"), editable=False)
    
    class Meta:
        ordering = ('name',)
    
    def __unicode__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        unique_slugify(self, self.name)
        super(Project, self).save(*args, **kwargs)

    def node_id(self):
        return "-".join(["Project", str(self.id)])

    def color(self):
        return "blue"

    def time_contributions(self):
        return sum(event.quantity for event in self.events.filter(
            is_contribution=True,
            event_type__relationship="work"))

    def contributions(self):
        return sum(event.quantity for event in self.events.filter(
            is_contribution=True))

    def contributions_count(self):
        return self.events.filter(is_contribution=True).count()

    def contribution_events(self):
        return self.events.filter(is_contribution=True)

    def contributors(self):
        ids = self.events.filter(is_contribution=True).values_list('from_agent').order_by('from_agent').distinct()
        id_list = [id[0] for id in ids]
        return EconomicAgent.objects.filter(id__in=id_list)

    def with_all_sub_projects(self):
        from valuenetwork.valueaccounting.utils import flattened_children
        return flattened_children(self, Project.objects.all(), [])

    def wip(self):
        return self.processes.all()

    def get_resource_types_with_recipe(self):
        return [pt.main_produced_resource_type() for pt in ProcessType.objects.filter(project=self)]

    def active_processes(self):
        return self.processes.filter(finished=False)


class ProcessType(models.Model):
    name = models.CharField(_('name'), max_length=128)
    parent = models.ForeignKey('self', blank=True, null=True, 
        verbose_name=_('parent'), related_name='sub_process_types', editable=False)
    process_pattern = models.ForeignKey(ProcessPattern,
        blank=True, null=True,
        verbose_name=_('process pattern'), related_name='process_types')
    project = models.ForeignKey(Project,
        blank=True, null=True,
        verbose_name=_('project'), related_name='process_types')
    description = models.TextField(_('description'), blank=True, null=True)
    url = models.CharField(_('url'), max_length=255, blank=True)
    estimated_duration = models.IntegerField(_('estimated duration'), 
        default=0, 
        help_text=_("in minutes, e.g. 3 hours = 180"))
    created_by = models.ForeignKey(User, verbose_name=_('created by'),
        related_name='process_types_created', blank=True, null=True, editable=False)
    changed_by = models.ForeignKey(User, verbose_name=_('changed by'),
        related_name='process_types_changed', blank=True, null=True, editable=False)
    created_date = models.DateField(auto_now_add=True, blank=True, null=True, editable=False)
    changed_date = models.DateField(auto_now=True, blank=True, null=True, editable=False)
    slug = models.SlugField(_("Page name"), editable=False)

    class Meta:
        ordering = ('name',)

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        unique_slugify(self, self.name)
        super(ProcessType, self).save(*args, **kwargs)

    def timeline_title(self):
        return " ".join([self.name, "Process to be planned"])

    def node_id(self):
        return "-".join(["ProcessType", str(self.id)])

    def color(self):
        return "blue"

    def produced_resource_type_relationships(self):
        return self.resource_types.filter(event_type__relationship='out')

    def produced_resource_types(self):
        return [ptrt.resource_type for ptrt in self.produced_resource_type_relationships()]

    def main_produced_resource_type(self):
        prts = self.produced_resource_types()
        if prts:
            return prts[0]
        else:
            return None

    def consumed_and_used_resource_type_relationships(self):
        return self.resource_types.filter(
            Q(event_type__relationship='consume')|Q(event_type__relationship='use'))

    def consumed_resource_type_relationships(self):
        return self.resource_types.filter(
            event_type__relationship='consume')

    def used_resource_type_relationships(self):
        return self.resource_types.filter(
            event_type__relationship='use')

    def cited_resource_type_relationships(self):
        return self.resource_types.filter(event_type__relationship='cite')

    def work_resource_type_relationships(self):
        return self.resource_types.filter(event_type__relationship='work')

    def consumed_resource_types(self):
        return [ptrt.resource_type for ptrt in self.consumed_resource_type_relationships()]

    def used_resource_types(self):
        return [ptrt.resource_type for ptrt in self.used_resource_type_relationships()]

    def cited_resource_types(self):
        return [ptrt.resource_type for ptrt in self.cited_resource_type_relationships()]

    def work_resource_types(self):
        return [ptrt.resource_type for ptrt in self.work_resource_type_relationships()]

    def all_input_resource_type_relationships(self):
        return self.resource_types.exclude(event_type__relationship='out').exclude(event_type__relationship='todo')

    def xbill_parents(self):
        return self.produced_resource_type_relationships()

    def xbill_children(self):
        kids = list(self.consumed_and_used_resource_type_relationships())
        kids.extend(self.cited_resource_type_relationships())
        kids.extend(self.work_resource_type_relationships())
        kids.extend(self.features.all())
        return kids

    def xbill_explanation(self):
        return "Process Type"

    def xbill_change_prefix(self):
        return "".join(["PT", str(self.id)])

    def xbill_change_form(self):
        from valuenetwork.valueaccounting.forms import XbillProcessTypeForm
        return XbillProcessTypeForm(instance=self, prefix=self.xbill_change_prefix())

    def xbill_input_prefix(self):
        return "".join(["PTINPUT", str(self.id)])

    def xbill_consumable_prefix(self):
        return "".join(["PTCONS", str(self.id)])

    def xbill_usable_prefix(self):
        return "".join(["PTUSE", str(self.id)])

    def xbill_citable_prefix(self):
        return "".join(["PTCITE", str(self.id)])

    def xbill_work_prefix(self):
        return "".join(["PTWORK", str(self.id)])

    def xbill_input_rt_prefix(self):
        return "".join(["PTINPUTRT", str(self.id)])

    def xbill_consumable_rt_prefix(self):
        return "".join(["PTCONSRT", str(self.id)])

    def xbill_usable_rt_prefix(self):
        return "".join(["PTUSERT", str(self.id)])

    def xbill_citable_rt_prefix(self):
        return "".join(["PTCITERT", str(self.id)])

    def xbill_input_rt_facet_prefix(self):
        return "".join(["PTINPUTRTF", str(self.id)])

    def xbill_consumable_rt_facet_prefix(self):
        return "".join(["PTCONSRTF", str(self.id)])

    def xbill_usable_rt_facet_prefix(self):
        return "".join(["PTUSERTF", str(self.id)])

    def xbill_citable_rt_facet_prefix(self):
        return "".join(["PTCITERTF", str(self.id)])

    def xbill_input_form(self):
        from valuenetwork.valueaccounting.forms import ProcessTypeInputForm
        return ProcessTypeInputForm(process_type=self, prefix=self.xbill_input_prefix())

    def xbill_consumable_form(self):
        from valuenetwork.valueaccounting.forms import ProcessTypeConsumableForm
        return ProcessTypeConsumableForm(process_type=self, prefix=self.xbill_consumable_prefix())

    def xbill_usable_form(self):
        from valuenetwork.valueaccounting.forms import ProcessTypeUsableForm
        return ProcessTypeUsableForm(process_type=self, prefix=self.xbill_usable_prefix())

    def xbill_citable_form(self):
        from valuenetwork.valueaccounting.forms import ProcessTypeCitableForm
        return ProcessTypeCitableForm(process_type=self, prefix=self.xbill_citable_prefix())

    def xbill_work_form(self):
        from valuenetwork.valueaccounting.forms import ProcessTypeWorkForm
        return ProcessTypeWorkForm(process_type=self, prefix=self.xbill_work_prefix())

    def xbill_input_rt_form(self):
        from valuenetwork.valueaccounting.forms import EconomicResourceTypeAjaxForm
        return EconomicResourceTypeAjaxForm(prefix=self.xbill_input_rt_prefix())

    def xbill_consumable_rt_form(self):
        from valuenetwork.valueaccounting.forms import EconomicResourceTypeAjaxForm
        return EconomicResourceTypeAjaxForm(prefix=self.xbill_consumable_rt_prefix())

    def xbill_usable_rt_form(self):
        from valuenetwork.valueaccounting.forms import EconomicResourceTypeAjaxForm
        return EconomicResourceTypeAjaxForm(prefix=self.xbill_usable_rt_prefix())

    def xbill_citable_rt_form(self):
        from valuenetwork.valueaccounting.forms import EconomicResourceTypeAjaxForm
        return EconomicResourceTypeAjaxForm(prefix=self.xbill_citable_rt_prefix())

    def xbill_input_rt_facet_formset(self):
        return self.create_facet_formset_filtered(slot="in", pre=self.xbill_input_rt_facet_prefix())

    def xbill_consumable_rt_facet_formset(self):
        return self.create_facet_formset_filtered(slot="consume", pre=self.xbill_consumable_rt_facet_prefix())

    def xbill_usable_rt_facet_formset(self):
        return self.create_facet_formset_filtered(slot="use", pre=self.xbill_usable_rt_facet_prefix())

    def xbill_citable_rt_facet_formset(self):
        return self.create_facet_formset_filtered(slot="cite", pre=self.xbill_citable_rt_facet_prefix())

    def create_facet_formset_filtered(self, pre, slot, data=None):
        from django.forms.models import formset_factory
        from valuenetwork.valueaccounting.forms import ResourceTypeFacetValueForm
        #import pdb; pdb.set_trace()
        RtfvFormSet = formset_factory(ResourceTypeFacetValueForm, extra=0)
        init = []
        if self.process_pattern == None:
            facets = Facet.objects.all()
        else:
            #facets = self.process_pattern.facets_by_relationship(slot)
            if slot == "consume":
                facets = self.process_pattern.consumable_facets()
            elif slot == "use":
                facets = self.process_pattern.usable_facets()
            elif slot == "cite":
                facets = self.process_pattern.citable_facets()
        for facet in facets:
            d = {"facet_id": facet.id,}
            init.append(d)
        formset = RtfvFormSet(initial=init, data=data, prefix=pre)
        for form in formset:
            id = int(form["facet_id"].value())
            facet = Facet.objects.get(id=id)
            form.facet_name = facet.name
            if self.process_pattern == None:
                fvs = facet.values.all()
            else:
                fvs = self.process_pattern.facet_values_for_facet_and_relationship(facet, slot)
            fvs = list(set(fvs))
            choices = [(fv.id, fv.value) for fv in fvs]
            form.fields["value"].choices = choices
        return formset

    def xbill_class(self):
        return "process-type"



#todo: rename to CommitmentType
class ProcessTypeResourceType(models.Model):
    process_type = models.ForeignKey(ProcessType,
        verbose_name=_('process type'), related_name='resource_types')
    resource_type = models.ForeignKey(EconomicResourceType, 
        verbose_name=_('resource type'), related_name='process_types')
    event_type = models.ForeignKey(EventType,
        verbose_name=_('event type'), related_name='process_resource_types')
    quantity = models.DecimalField(_('quantity'), max_digits=8, decimal_places=2, default=Decimal('0.00'))
    unit_of_quantity = models.ForeignKey(Unit, blank=True, null=True,
        verbose_name=_('unit'), related_name="process_resource_qty_units")
    description = models.TextField(_('description'), null=True, blank=True)
    created_by = models.ForeignKey(User, verbose_name=_('created by'),
        related_name='ptrts_created', blank=True, null=True, editable=False)
    changed_by = models.ForeignKey(User, verbose_name=_('changed by'),
        related_name='ptrts_changed', blank=True, null=True, editable=False)
    created_date = models.DateField(auto_now_add=True, blank=True, null=True, editable=False)
    changed_date = models.DateField(auto_now=True, blank=True, null=True, editable=False)

    class Meta:
        ordering = ('resource_type',)
        verbose_name = _('commitment type')

    def __unicode__(self):
        relname = ""
        if self.event_type:
            relname = self.event_type.label
        return " ".join([self.process_type.name, relname, str(self.quantity), self.resource_type.name])        

    def inverse_label(self):
        return self.event_type.inverse_label

    def xbill_label(self):
        if self.event_type.relationship == 'out':
            #return self.inverse_label()
            return ""
        else:
           abbrev = ""
           if self.unit_of_quantity:
               abbrev = self.unit_of_quantity.abbrev
           return " ".join([self.event_type.label, str(self.quantity), abbrev])

    def xbill_explanation(self):
        if self.event_type.relationship == 'out':
            return "Process Type"
        else:
            return "Input"

    def xbill_child_object(self):
        if self.event_type.relationship == 'out':
            return self.process_type
        else:
            return self.resource_type

    def xbill_class(self):
        return self.xbill_child_object().xbill_class()

    def xbill_parent_object(self):
        if self.event_type.relationship == 'out':
            return self.resource_type
            #if self.resource_type.category.name == 'option':
            #    return self
            #else:
            #    return self.resource_type
        else:
            return self.process_type

    def xbill_parents(self):
        return [self.resource_type, self]

    def node_id(self):
        return "-".join(["ProcessResource", str(self.id)])

    def xbill_change_prefix(self):
        return "".join(["PTRT", str(self.id)])

    def xbill_change_form(self):
        from valuenetwork.valueaccounting.forms import ProcessTypeInputForm, ProcessTypeCitableForm, ProcessTypeWorkForm
        if self.event_type.relationship == "work":
            return ProcessTypeWorkForm(instance=self, process_type=self.process_type, prefix=self.xbill_change_prefix())
        elif self.event_type.relationship == "cite":
            return ProcessTypeCitableForm(instance=self, process_type=self.process_type, prefix=self.xbill_change_prefix())
        else:
            return ProcessTypeInputForm(instance=self, process_type=self.process_type, prefix=self.xbill_change_prefix())

class ProcessManager(models.Manager):

    def unfinished(self):
        return Process.objects.filter(finished=False)

    def finished(self):
        return Process.objects.filter(finished=True)


class Process(models.Model):
    name = models.CharField(_('name'), max_length=128)
    parent = models.ForeignKey('self', blank=True, null=True, 
        verbose_name=_('parent'), related_name='sub_processes', editable=False)
    process_pattern = models.ForeignKey(ProcessPattern,
        blank=True, null=True,
        verbose_name=_('process pattern'), related_name='processes')
    process_type = models.ForeignKey(ProcessType,
        blank=True, null=True,
        verbose_name=_('process type'), related_name='processes',
        on_delete=models.SET_NULL)
    project = models.ForeignKey(Project,
        blank=True, null=True,
        verbose_name=_('project'), related_name='processes')
    url = models.CharField(_('url'), max_length=255, blank=True)
    start_date = models.DateField(_('start date'))
    end_date = models.DateField(_('end date'), blank=True, null=True)
    started = models.DateField(_('started'), blank=True, null=True)
    finished = models.BooleanField(_('finished'), default=False)
    managed_by = models.ForeignKey(EconomicAgent, related_name="managed_processes",
        verbose_name=_('managed by'), blank=True, null=True)
    owner = models.ForeignKey(EconomicAgent, related_name="owned_processes",
        verbose_name=_('owner'), blank=True, null=True)
    notes = models.TextField(_('notes'), blank=True)
    created_by = models.ForeignKey(User, verbose_name=_('created by'),
        related_name='processes_created', blank=True, null=True, editable=False)
    changed_by = models.ForeignKey(User, verbose_name=_('changed by'),
        related_name='processes_changed', blank=True, null=True, editable=False)
    created_date = models.DateField(auto_now_add=True, blank=True, null=True, editable=False)
    changed_date = models.DateField(auto_now=True, blank=True, null=True, editable=False)
    slug = models.SlugField(_("Page name"), editable=False)

    objects = ProcessManager()

    class Meta:
        ordering = ('-end_date',)
        verbose_name_plural = _("processes")

    def __unicode__(self):
        order_name = ""
        order = self.independent_demand()
        if order:
            order_name = order.name
            if order_name:
                order_name = " ".join(["for", order_name])
        return " ".join([
            self.name,
            order_name,
            "starting",
            self.start_date.strftime('%Y-%m-%d'),
            "ending",
            self.end_date.strftime('%Y-%m-%d'),
            ])

    def name_with_order(self):
        answer = self.name
        order = self.independent_demand()
        if order:
            order_name = order.name
            if order_name:
                answer = " ".join([self.name, "for", order_name])
        return answer
    
    @models.permalink
    def get_absolute_url(self):
        return ('process_details', (),
            { 'process_id': str(self.id),})

    def save(self, *args, **kwargs):
        pt_name = ""
        if self.process_type:
            pt_name = self.process_type.name
        slug = "-".join([
            pt_name,
            self.name,
            self.start_date.strftime('%Y-%m-%d'),
        ])
        unique_slugify(self, slug)
        super(Process, self).save(*args, **kwargs)

    def is_deletable(self):
        if self.events.all():
            return False
        return True

    def flow_type(self):
        return "Process"

    def flow_class(self):
        return "process"

    def flow_description(self):
        return self.__unicode__()

    def node_id(self):
        return "-".join(["Process", str(self.id)])

    def independent_demand(self):
        moc = self.main_outgoing_commitment()
        if moc:
            return moc.independent_demand
        else:
            ics = self.incoming_commitments()
            if ics:
                return ics[0].independent_demand
        return None

    def timeline_title(self):
        #return " ".join([self.name, "Process"])
        return self.name

    def timeline_description(self):
        if self.notes:
            return self.notes
        elif self.process_type:
            return self.process_type.description
        else:
            return ""

    def is_orphan(self):
        #todo: if agents on graph, stop excluding work
        answer = True
        if self.commitments.exclude(event_type__relationship='work').count():
            answer = False
        if self.events.exclude(event_type__relationship='work').count():
            answer = False
        return answer

    def incoming_commitments(self):
        return self.commitments.exclude(
            event_type__relationship='out')

    def schedule_requirements(self):
        return self.commitments.exclude(
            event_type__relationship='out')

    def outgoing_commitments(self):
        return self.commitments.filter(
            event_type__relationship='out')

    def output_resource_types(self):
        return [c.resource_type for c in self.outgoing_commitments()]

    def production_events(self):
        return self.events.filter(
            event_type__relationship='out')

    def uncommitted_production_events(self):
        return self.events.filter(
            event_type__relationship='out',
            commitment=None)

    def uncommitted_consumption_events(self):
        return self.events.filter(
            event_type__relationship='consume',
            commitment=None)

    def uncommitted_use_events(self):
        return self.events.filter(
            event_type__relationship='use',
            commitment=None)

    def uncommitted_citation_events(self):
        return self.events.filter(
            event_type__relationship='cite',
            commitment=None)

    def uncommitted_input_events(self):
        return self.events.filter(
            commitment=None).exclude(event_type__relationship='out')

    def incoming_events(self):
        return self.events.exclude(event_type__relationship='out')

    def uncommitted_work_events(self):
        return self.events.filter(
            event_type__relationship='work',
            commitment=None)

    def main_outgoing_commitment(self):
        cts = self.outgoing_commitments()
        if cts:
            return cts[0]
        else:
            return None

    def previous_processes(self):
        answer = []
        dmnd = None
        moc = self.main_outgoing_commitment()
        #import pdb; pdb.set_trace()
        if moc:
            dmnd = moc.independent_demand
        #output_rts = [oc.resource_type for oc in self.outgoing_commitments()]
        for ic in self.incoming_commitments():
            rt = ic.resource_type
            # this is maybe a better way to block cycles
            for pc in rt.producing_commitments():
                if pc.process != self:
                    if dmnd:
                        if pc.independent_demand == dmnd:
                            answer.append(pc.process)
                    else:
                        if not pc.independent_demand:
                            if pc.quantity >= ic.quantity:
                                if pc.due_date <= self.start_date:
                                    answer.append(pc.process)
        for ie in self.uncommitted_input_events():
            if ie.resource:
                for evt in ie.resource.producing_events():
                    if evt.process:
                        if evt.process != self:
                            if evt.process not in answer:
                                answer.append(evt.process)
        return answer

    def all_previous_processes(self, ordered_processes, visited_resources, depth):
        self.depth = depth * 2
        ordered_processes.append(self)
        output = self.main_outgoing_commitment()
        if not output:
            return []
        depth = depth + 1
        if output.resource_type not in visited_resources:
            visited_resources.append(output.resource_type)
            for process in self.previous_processes():
                process.all_previous_processes(ordered_processes, visited_resources, depth)

    def next_processes(self):
        answer = []
        #import pdb; pdb.set_trace()
        input_rts = [ic.resource_type for ic in self.incoming_commitments()]
        for oc in self.outgoing_commitments():
            dmnd = oc.independent_demand
            rt = oc.resource_type
            if rt not in input_rts:
                for cc in rt.wanting_commitments():
                    if dmnd:
                        if cc.independent_demand == dmnd:
                            if cc.process not in answer:
                                answer.append(cc.process)
                    else:
                        if not cc.independent_demand:
                            if cc.quantity >= oc.quantity:
                                compare_date = self.end_date
                                if not compare_date:
                                    compare_date = self.start_date
                                if cc.due_date >= compare_date:
                                    if cc.process not in answer:
                                        answer.append(cc.process)
        for oe in self.uncommitted_production_events():
            rt = oe.resource_type
            if rt not in input_rts:
                if oe.resource:
                    for evt in oe.resource.all_usage_events():
                        if evt.process:
                            if evt.process not in answer:
                                answer.append(evt.process)
        return answer

    def consumed_input_requirements(self):
        return self.commitments.filter(
            event_type__relationship='consume'
        )

    def used_input_requirements(self):
        return self.commitments.filter(
            event_type__relationship='use'
        )

    def citation_requirements(self):
        return self.commitments.filter(
            event_type__relationship='cite',
        )
    
    def work_requirements(self):
        return self.commitments.filter(
            event_type__relationship='work',
        )

    def unfinished_work_requirements(self):
        return self.commitments.filter(
            finished=False,
            event_type__relationship='work',
        )

    def non_work_requirements(self):
        return self.commitments.exclude(
            event_type__relationship='work',
        )

    def working_agents(self):
        reqs = self.work_requirements()
        return [req.from_agent for req in reqs if req.from_agent]

    def work_events(self):
        return self.events.filter(
            event_type__relationship='work')

    def outputs(self):
        return self.events.filter(
            event_type__relationship='out',
            quality__gte=0)

    def deliverables(self):
        return [output.resource for output in self.outputs() if output.resource]

    def failed_outputs(self):
        return self.events.filter(
            event_type__relationship='out',
            quality__lt=0)

    def consumed_inputs(self):
        return self.events.filter(
            event_type__relationship='consume')

    def used_inputs(self):
        return self.events.filter(
            event_type__relationship='use')

    def citations(self):
        return self.events.filter(
            event_type__relationship='cite')

    def outputs_from_agent(self, agent):
        answer = []
        for event in self.outputs():
            if event.from_agent == agent:
                answer.append(event)
        return answer

    def citations_by_agent(self, agent):
        answer = []
        for event in self.citations():
            if event.from_agent == agent:
                answer.append(event)
        return answer

    def inputs_consumed_by_agent(self, agent):
        answer = []
        for event in self.consumed_inputs():
            if event.to_agent == agent:
                answer.append(event)
        return answer

    def inputs_used_by_agent(self, agent):
        answer = []
        for event in self.used_inputs():
            if event.to_agent == agent:
                answer.append(event)
        return answer

    def failed_output_qty(self):
        return sum(evt.quantity for evt in self.events.filter(quality__lt=0))

    def failures_from_agent(self, agent):
        answer = []
        for event in self.failed_outputs():
            if event.from_agent == agent:
                answer.append(event)
        return answer

    def order_items(self):
        return []

    def add_commitment(self,
            resource_type,
            demand,
            quantity,
            event_type,
            unit,
            user,
            from_agent=None,
            to_agent=None):
        ct = Commitment(
            independent_demand=demand,
            process=self,
            project=self.project,
            event_type=event_type,
            resource_type=resource_type,
            quantity=quantity,
            unit_of_quantity=unit,
            due_date=self.start_date,
            from_agent=from_agent,
            to_agent=to_agent,
            created_by=user)
        ct.save()
        return ct

    def explode_demands(self, demand, user, visited):
        """This method assumes the output commitment from this process 

            has already been created.

        """
        #import pdb; pdb.set_trace()
        pt = self.process_type
        output = self.main_outgoing_commitment()
        #if not output:
            #import pdb; pdb.set_trace()
        if output.resource_type not in visited:
            visited.append(output.resource_type)
        for ptrt in pt.all_input_resource_type_relationships():   
            commitment = self.add_commitment(
                resource_type=ptrt.resource_type,
                demand=demand,
                quantity=output.quantity * ptrt.quantity,
                event_type=ptrt.event_type,
                unit=ptrt.resource_type.unit,
                user=user,
            )
            if ptrt.resource_type not in visited:
                visited.append(ptrt.resource_type)
                qty_to_explode = commitment.net()
                if qty_to_explode:
                    #todo: shd commitment.generate_producing_process?
                    #no, this an input commitment
                    #shd pt create process?
                    #shd pptr create next_commitment, and then 
                    #shd next_commitment.generate_producing_process?
                    pptr = ptrt.resource_type.main_producing_process_type_relationship()
                    if pptr:
                        next_pt = pptr.process_type
                        start_date = self.start_date - datetime.timedelta(minutes=next_pt.estimated_duration)
                        next_process = Process(          
                            name=next_pt.name,
                            process_type=next_pt,
                            process_pattern=next_pt.process_pattern,
                            project=next_pt.project,
                            url=next_pt.url,
                            end_date=self.start_date,
                            start_date=start_date,
                        )
                        next_process.save()
                        #this is the output commitment
                        next_commitment = next_process.add_commitment(
                            resource_type=pptr.resource_type,
                            demand=demand,
                            quantity=qty_to_explode * pptr.quantity,
                            event_type=pptr.event_type,
                            unit=pptr.resource_type.unit,
                            user=user,
                        )
                        next_process.explode_demands(demand, user, visited)

    def reschedule_forward(self, delta_days, user):
        #import pdb; pdb.set_trace()
        fps = self.previous_processes()
        if fps:
            slack =  99999
            for fp in fps:
                slax = self.start_date - fp.end_date
                slack = min(slack, slax.days)
            slack = max(slack, 0)
            delta_days -= slack
            delta_days = max(delta_days, 0)
            #munge for partial days
            delta_days += 1
        if delta_days:
            self.start_date = self.start_date + datetime.timedelta(days=delta_days)
            if self.end_date:
                self.end_date = self.end_date + datetime.timedelta(days=delta_days)
            else:
                 self.end_date = self.start_date
            self.changed_by = user
            self.save()
            self.reschedule_connections(delta_days, user)

    def reschedule_connections(self, delta_days, user):
        for ct in self.incoming_commitments():
            ct.reschedule_forward(delta_days, user)
        for ct in self.outgoing_commitments():
            ct.reschedule_forward(delta_days, user)
        for p in self.next_processes():
            p.reschedule_forward(delta_days, user)

    def too_late(self):
        if self.started:
            if self.finished:
                return False
            else:
                return self.end_date < datetime.date.today()
        else:
            return self.start_date < datetime.date.today()

    def bumped_processes(self):
        return [p for p in self.next_processes() if self.end_date > p.start_date]

    def schedule_form(self):
        from valuenetwork.valueaccounting.forms import ScheduleProcessForm
        init = {"start_date": self.start_date, "end_date": self.end_date, "notes": self.notes}
        return ScheduleProcessForm(prefix=str(self.id),initial=init)


class ExchangeManager(models.Manager):

    def financial_contributions(self):
        return Exchange.objects.exclude(use_case__identifier="res_contr")

class Exchange(models.Model):
    name = models.CharField(_('name'), blank=True, max_length=128)
    process_pattern = models.ForeignKey(ProcessPattern,
        blank=True, null=True,
        verbose_name=_('pattern'), related_name='exchanges')
    use_case = models.ForeignKey(UseCase,
        blank=True, null=True,
        verbose_name=_('use case'), related_name='exchanges')
    project = models.ForeignKey(Project,
        blank=True, null=True,
        verbose_name=_('project'), related_name='exchanges')
    url = models.CharField(_('url'), max_length=255, blank=True)
    start_date = models.DateField(_('start date'))
    notes = models.TextField(_('notes'), blank=True)
    supplier = models.ForeignKey(EconomicAgent,
        blank=True, null=True,
        related_name="exchange", verbose_name=_('supplier'))
    created_by = models.ForeignKey(User, verbose_name=_('created by'),
        related_name='exchanges_created', blank=True, null=True, editable=False)
    changed_by = models.ForeignKey(User, verbose_name=_('changed by'),
        related_name='exchanges_changed', blank=True, null=True, editable=False)
    created_date = models.DateField(auto_now_add=True, blank=True, null=True, editable=False)
    changed_date = models.DateField(auto_now=True, blank=True, null=True, editable=False)
    slug = models.SlugField(_("Page name"), editable=False)

    objects = ExchangeManager()

    class Meta:
        ordering = ('-start_date',)
        verbose_name_plural = _("exchanges")

    def __unicode__(self):
        return " ".join([
            self.process_pattern.name,
            "starting",
            self.start_date.strftime('%Y-%m-%d'),
            ])

    @models.permalink
    def get_absolute_url(self):
        return ('exchange_details', (),
            { 'exchange_id': str(self.id),})

    def save(self, *args, **kwargs):
        ext_name = ""
        #if self.exchange_type:
        #    ext_name = self.exchange_type.name
        slug = "-".join([
            self.name,
            self.start_date.strftime('%Y-%m-%d'),
        ])
        unique_slugify(self, slug)
        super(Exchange, self).save(*args, **kwargs)

    def is_deletable(self):
        answer = True
        if self.events.all():
            answer = False
        #elif self.resources.all():
        #    answer = False
        #elif self.commitments.all():
        #    answer = False
        return answer

    def receipt_commitments(self):
        return self.commitments.filter(
            event_type__relationship='receive')

    def payment_commitments(self):
        return self.commitments.filter(
            event_type__relationship='pay')

    def receipt_events(self):
        return self.events.filter(
            event_type__relationship='receive')

    def uncommitted_receipt_events(self):
        return self.events.filter(
            event_type__relationship='receive',
            commitment=None)

    def payment_events(self):
        return self.events.filter(
            event_type__relationship='pay')

    def uncommitted_payment_events(self):
        return self.events.filter(
            event_type__relationship='pay',
            commitment=None)

    def work_events(self):
        return self.events.filter(
            event_type__relationship='work')

    def expense_events(self):
        return self.events.filter(
            event_type__relationship='expense')

    def material_contribution_events(self):
        return self.events.filter(
            event_type__relationship='resource')
        
    def cash_contribution_events(self):
        return self.events.filter(
            event_type__relationship='cash')

    def sorted_events(self):
        events = self.events.all().order_by("event_type__name")
        return events


class Feature(models.Model):
    name = models.CharField(_('name'), max_length=128)
    #todo: replace with ___? something
    #option_category = models.ForeignKey(Category,
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

    def __unicode__(self):
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

    #def xbill_category(self):
    #    return Category(name="features")

    def node_id(self):
        return "-".join(["Feature", str(self.id)])

    def xbill_parents(self):
        return [self.process_type, self]

    def options_form(self):
        from valuenetwork.valueaccounting.forms import OptionsForm
        return OptionsForm(feature=self)

    def options_change_form(self):
        from valuenetwork.valueaccounting.forms import OptionsForm
        option_ids = self.options.values_list('component__id', flat=True)
        init = {'options': option_ids,}
        return OptionsForm(feature=self, initial=init)

    def xbill_change_prefix(self):
        return "".join(["FTR", str(self.id)])

    def xbill_change_form(self):
        from valuenetwork.valueaccounting.forms import FeatureForm
        #return FeatureForm(instance=self, prefix=self.xbill_change_prefix())
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

    def __unicode__(self):
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

    #def xbill_category(self):
    #    return Category(name="features")

    def node_id(self):
        return "-".join(["Option", str(self.id)])

    def xbill_parents(self):
        return [self.feature, self]


class CommitmentManager(models.Manager):

    def unfinished(self):
        return Commitment.objects.filter(finished=False)

    def finished(self):
        return Commitment.objects.filter(finished=True)

    def todos(self):
        return Commitment.objects.filter(
            event_type__relationship="todo",
            finished=False)

    def finished_todos(self):
        return Commitment.objects.filter(
            event_type__relationship="todo",
            finished=True)

    def to_buy(self):
        reqs = Commitment.objects.filter(
            Q(event_type__relationship='consume')|Q(event_type__relationship='use')).order_by("resource_type__name")
        answer = []
        for req in reqs:
            qtb = req.quantity_to_buy()
            if req.quantity_to_buy():
                if req.resource_type.is_purchased():
                    req.purchase_quantity = qtb
                    answer.append(req)
        return answer


class Commitment(models.Model):
    order = models.ForeignKey(Order,
        blank=True, null=True,
        related_name="commitments", verbose_name=_('order'))
    independent_demand = models.ForeignKey(Order,
        blank=True, null=True,
        related_name="dependent_commitments", verbose_name=_('independent_demand'))
    event_type = models.ForeignKey(EventType, 
        related_name="commitments", verbose_name=_('event type'))
    #relationship = models.ForeignKey(ResourceRelationship,
    #    verbose_name=_('relationship'), related_name='commitments')
    commitment_date = models.DateField(_('commitment date'), default=datetime.date.today)
    start_date = models.DateField(_('start date'), blank=True, null=True)
    due_date = models.DateField(_('due date'))
    finished = models.BooleanField(_('finished'), default=False)
    from_agent_type = models.ForeignKey(AgentType,
        blank=True, null=True,
        related_name="given_commitments", verbose_name=_('from agent type'))
    from_agent = models.ForeignKey(EconomicAgent,
        blank=True, null=True,
        related_name="given_commitments", verbose_name=_('from'))
    to_agent = models.ForeignKey(EconomicAgent,
        blank=True, null=True,
        related_name="taken_commitments", verbose_name=_('to'))
    resource_type = models.ForeignKey(EconomicResourceType, 
        blank=True, null=True,
        verbose_name=_('resource type'), related_name='commitments')
    resource = models.ForeignKey(EconomicResource, 
        blank=True, null=True,
        verbose_name=_('resource'), related_name='commitments')
    process = models.ForeignKey(Process,
        blank=True, null=True,
        verbose_name=_('process'), related_name='commitments')
    exchange = models.ForeignKey(Exchange,
        blank=True, null=True,
        verbose_name=_('exchange'), related_name='commitments')
    project = models.ForeignKey(Project,
        blank=True, null=True,
        verbose_name=_('project'), related_name='commitments')
    description = models.TextField(_('description'), null=True, blank=True)
    url = models.CharField(_('url'), max_length=255, blank=True)
    quantity = models.DecimalField(_('quantity'), max_digits=8, decimal_places=2)
    unit_of_quantity = models.ForeignKey(Unit, blank=True, null=True,
        verbose_name=_('unit'), related_name="commitment_qty_units")
    quality = models.DecimalField(_('quality'), max_digits=3, decimal_places=0, default=Decimal("0"))
    value = models.DecimalField(_('value'), max_digits=8, decimal_places=2, 
        default=Decimal("0.0"))
    unit_of_value = models.ForeignKey(Unit, blank=True, null=True,
        verbose_name=_('unit of value'), related_name="commitment_value_units")
    created_by = models.ForeignKey(User, verbose_name=_('created by'),
        related_name='commitments_created', blank=True, null=True, editable=False)
    changed_by = models.ForeignKey(User, verbose_name=_('changed by'),
        related_name='commitments_changed', blank=True, null=True, editable=False)
    created_date = models.DateField(auto_now_add=True, blank=True, null=True, editable=False)
    changed_date = models.DateField(auto_now=True, blank=True, null=True, editable=False)
    slug = models.SlugField(_("Page name"), editable=False)

    objects = CommitmentManager()

    class Meta:
        ordering = ('due_date',)

    def __unicode__(self):
        quantity_string = str(self.quantity)
        resource_name = ""
        abbrev = ""
        process_name = ""
        if self.unit_of_quantity:
           abbrev = self.unit_of_quantity.abbrev
        if self.resource_type:
            resource_name = self.resource_type.name
        if self.process:
            process_name = self.process.name
        if self.order:
            from_agt = 'Unassigned'
            if self.from_agent:
                from_agt = self.from_agent.name
            to_agt = 'Unassigned'
            if self.to_agent:
                to_agt = self.to_agent.name
            if self.event_type.relationship == "out":
                name1 = from_agt
                name2 = to_agt
                prep = "for"
            else:
                name2 = from_agt
                name1 = to_agt
                prep = "from"
            return ' '.join([
                name1,
                self.event_type.name,
                quantity_string,
                abbrev,
                resource_name,
                self.due_date.strftime('%Y-%m-%d'),          
                prep,
                name2,
            ])
        else:
            return ' '.join([
                process_name,
                self.event_type.label,
                quantity_string,
                abbrev,
                resource_name,
                self.due_date.strftime('%Y-%m-%d'),          
        ])

    def save(self, *args, **kwargs):
        from_id = "Unassigned"
        if self.from_agent:
            from_id = str(self.from_agent.id)
        slug = "-".join([
            str(self.event_type.id),
            from_id,
            self.due_date.strftime('%Y-%m-%d'),
        ])
        unique_slugify(self, slug)
        #notify_here?
        super(Commitment, self).save(*args, **kwargs)

    def label(self):
        return self.event_type.get_relationship_display()

    def commitment_type(self):
        rt = self.resource_type
        pt = None
        if self.process:
            pt = self.process.process_type
        if pt:
            try:
                return ProcessTypeResourceType.objects.get(
                    resource_type=rt, process_type=pt)
            except ProcessTypeResourceType.DoesNotExist:
                return None
        return None

    def feature_label(self):
        if not self.order:
            return ""
        features = self.resource_type.features.all()
        if not features:
            return ""
        inputs = [ct.resource_type for ct in self.process.incoming_commitments()]
        selected_options = []
        for feature in features:
            options = feature.options.all()
            for option in options:
                if option.component in inputs:
                    selected_options.append(option.component)
        names = ', '.join([so.name for so in selected_options])
        prefix = "with option"
        if len(selected_options) > 1:
              prefix = "with options"
        return " ".join([prefix, names])    

    def timeline_title(self):
        quantity_string = str(self.quantity)
        from_agt = 'Unassigned'
        if self.from_agent:
            from_agt = self.from_agent.name
        process = "Unknown"
        if self.process:
            process = self.process.name
        return ' '.join([
            self.resource_type.name,
            'from',
            from_agt,
            'to',
            process,
        ])

    def form_prefix(self):
        return "-".join(["CT", str(self.id)])

    def commitment_form(self):
        from valuenetwork.valueaccounting.forms import CommitmentForm
        prefix=self.form_prefix()
        return CommitmentForm(instance=self, prefix=prefix)
   
    def change_form(self):
        from valuenetwork.valueaccounting.forms import ChangeCommitmentForm
        prefix=self.form_prefix()
        return ChangeCommitmentForm(instance=self, prefix=prefix)

    def change_work_form(self):
        from valuenetwork.valueaccounting.forms import ChangeWorkCommitmentForm
        prefix=self.form_prefix()
        return ChangeWorkCommitmentForm(instance=self, prefix=prefix)

    def resource_create_form(self):
        return self.resource_type.resource_create_form(self.form_prefix())

    def resource_change_form(self):
        resource = self.output_resource()
        if resource:
            return resource.change_form(self.form_prefix())
        else:
            return self.resource_type.resource_create_form(self.form_prefix())

    def todo_change_form(self):
        #import pdb; pdb.set_trace()
        from valuenetwork.valueaccounting.forms import TodoForm
        prefix=self.form_prefix()
        return TodoForm(instance=self, prefix=prefix)

    def work_event_form(self, data=None):        
        from valuenetwork.valueaccounting.forms import TimeEventForm, InputEventForm
        prefix=self.form_prefix()
        unit = self.resource_type.unit
        if unit.unit_type == "time":
            return TimeEventForm(prefix=prefix, data=data)
        else:
            qty_help = " ".join(["unit:", unit.abbrev])
            return InputEventForm(qty_help=qty_help, prefix=prefix, data=data)

    def consumption_event_form(self):        
        from valuenetwork.valueaccounting.forms import InputEventForm
        prefix=self.form_prefix()
        qty_help = " ".join(["unit:", self.unit_of_quantity.abbrev])
        return InputEventForm(qty_help=qty_help, prefix=prefix)

    def use_event_form(self):        
        from valuenetwork.valueaccounting.forms import TimeEventForm, InputEventForm
        prefix=self.form_prefix()
        unit = self.resource_type.directional_unit("use")
        if unit.unit_type == "time":
            return TimeEventForm(prefix=prefix)
        else:
            qty_help = " ".join(["unit:", unit.abbrev])
            return InputEventForm(qty_help=qty_help, prefix=prefix)

    def fulfilling_events(self):
        return self.fulfillment_events.all()

    def todo_event(self):
        events = self.fulfilling_events()
        if events:
            return events[0]
        else:
            return None

    def is_deletable(self):
        if self.fulfilling_events():
            return False
        else:
            return True

    def fulfilling_events_from_agent(self, agent):
        return self.fulfillment_events.filter(from_agent=agent)

    def failed_outputs(self):
        answer = []
        events = self.process.failed_outputs()
        for event in events:
            if event.resource_type == self.resource_type:
                answer.append(event)
        return answer

    def failed_output_qty(self):
        return sum(evt.quantity for evt in self.failed_outputs())

    def agent_has_labnotes(self, agent):
        #import pdb; pdb.set_trace()
        if self.fulfillment_events.filter(from_agent=agent):
            return True
        else:
            return False

    def fulfilled_quantity(self):
        return sum(evt.quantity for evt in self.fulfilling_events())

    def unfilled_quantity(self):
        return self.quantity - self.fulfilled_quantity()

    def onhand(self):
        #todo: filter resources by r.order==self.independent_demand
        #if not RT.substitutable
        answer = []
        rt = self.resource_type
        resources = EconomicResource.goods.filter(resource_type=self.resource_type)
        if not rt.substitutable:
            resources = resources.filter(independent_demand=self.independent_demand)
        for resource in resources:
            if resource.quantity > 0:
                answer.append(resource)
            else:
                if self.fulfillment_events.filter(resource=resource):
                    answer.append(resource)
        return answer

    def onhand_with_fulfilled_quantity(self):
        #import pdb; pdb.set_trace()
        resources = self.onhand()
        for resource in resources:
            events = self.fulfillment_events.filter(resource=resource)
            resource.fulfilled_quantity = sum(evt.quantity for evt in events)
        return resources

    def consumable_resources(self):
        answer = []
        if self.event_type.consumes_resources():
            events = self.fulfillment_events.all()
            event_resources = [event.resource for event in events]
            event_resources = set(event_resources)
            resources = self.resource_type.all_resources()
            for r in resources:
                if r.quantity:
                    answer.append(r)
                else:
                    if r in event_resources:
                        answer.append(r)
        return answer

    def quantity_to_buy(self):
        return self.net()

    def net(self):
        #import pdb; pdb.set_trace()
        rt = self.resource_type
        if not rt.substitutable:
            #todo: or, get resources where r.order == self.independent_demand
            #in rt.ohqfc?
            #or not rt.substitutable means will never be netted anyway so don't bother?
            return self.quantity
        oh_qty = rt.onhand_qty_for_commitment(self)
        if oh_qty >= self.quantity:
            return 0
        sked_qty = rt.scheduled_qty_for_commitment(self)      
        if self.event_type.resource_effect == "-":
            remainder = self.quantity - oh_qty
            if sked_qty >= remainder:
                return Decimal("0")
            return remainder - sked_qty
        else:
            if oh_qty + sked_qty:
                return Decimal("0")
            elif self.event_type.resource_effect == "=":   
                return Decimal("1")
            else: 
                return self.quantity
  
    def creates_resources(self):
        return self.event_type.creates_resources()

    def consumes_resources(self):
        return self.event_type.consumes_resources()

    def output_resources(self):
        answer = None
        if self.event_type.relationship == "out":
            answer = [event.resource for event in self.fulfilling_events()]
        return answer

    def output_resource(self):
        #todo: this is a hack, cd be several resources
        answer = None
        if self.event_type.relationship == "out":
            events = self.fulfilling_events()
            if events:
                event = events[0]
                answer = event.resource
        return answer

    def generate_producing_process(self, user, visited, explode=False):
        qty_required = self.quantity
        rt = self.resource_type
        if not self.order:
            qty_required = self.net()
        process=None
        if qty_required:            
            ptrt = rt.main_producing_process_type_relationship()
            demand = self.independent_demand
            if ptrt:
                pt = ptrt.process_type
                start_date = self.due_date - datetime.timedelta(minutes=pt.estimated_duration)
                process = Process(
                    name=pt.name,
                    process_type=pt,
                    process_pattern=pt.process_pattern,
                    project=pt.project,
                    url=pt.url,
                    end_date=self.due_date,
                    start_date=start_date,
                    created_by=user,
                )
                process.save()
                self.process=process
                self.save()
                if explode:
                    process.explode_demands(demand, user, visited)
        return process

    def sources(self):
        arts = self.resource_type.producing_agent_relationships()
        for art in arts:
            art.order_release_date = self.due_date - datetime.timedelta(days=art.lead_time)
            art.too_late = art.order_release_date < datetime.date.today()
            art.commitment = self
        return arts

    def possible_source_users(self):
        srcs = self.sources()
        agents = [src.agent for src in srcs]
        users = [a.user() for a in agents if a.user()]
        return [u.user for u in users]

    def reschedule_forward(self, delta_days, user):
        #import pdb; pdb.set_trace()
        self.due_date = self.due_date + datetime.timedelta(days=delta_days)
        self.changed_by = user
        self.save()
        order = self.order
        if order:
            #import pdb; pdb.set_trace()
            order.due_date  += datetime.timedelta(days=delta_days)
            order.save()

    def reschedule_forward_from_source(self, lead_time, user):
        lag = datetime.date.today() - self.due_date
        delta_days = lead_time + lag.days + 1
        #todo: next line may need to be removed
        #if process.reschedule_connections is revived
        self.reschedule_forward(delta_days, user)
        self.process.reschedule_forward(delta_days, user)

    def associated_wanting_commitments(self):
        wanters = self.resource_type.wanting_commitments().exclude(id=self.id)
        return [ct for ct in wanters if ct.independent_demand == self.independent_demand]

    def associated_producing_commitments(self):
        producers = self.resource_type.producing_commitments().exclude(id=self.id)
        return [ct for ct in producers if ct.independent_demand == self.independent_demand]

    def scheduled_receipts(self):
        rt = self.resource_type
        if rt.substitutable:
            return rt.active_producing_commitments()
        else:
            return self.associated_producing_commitments()
        
    
#todo: not used.
class Reciprocity(models.Model):
    """One Commitment reciprocating another.

    The EconomicAgents in the reciprocal commitments
    must be opposites.  
    That is, the from_agent of one commitment must be
    the to-agent of the other commitment, and vice versa.
    Reciprocal commitments have a M:M relationship:
    that is, one commitment can be reciprocated by many other commitments,
    and the other commitment can reciprocate many initiating commitments.

    """
    initiating_commitment = models.ForeignKey(Commitment, 
        related_name="initiated_commitments", verbose_name=_('initiating commitment'))
    reciprocal_commitment = models.ForeignKey(Commitment, 
        related_name="reciprocal_commitments", verbose_name=_('reciprocal commitment'))
    reciprocity_date = models.DateField(_('reciprocity date'), default=datetime.date.today)

    class Meta:
        ordering = ('reciprocity_date',)

    def __unicode__(self):
        return ' '.join([
            'inititating commmitment:',
            self.initiating_commmitment.__unicode__(),
            'reciprocal commmitment:',
            self.reciprocal_commitment.__unicode__(),
            self.reciprocity_date.strftime('%Y-%m-%d'),
        ])

    def clean(self):
        #import pdb; pdb.set_trace()
        if self.initiating_commitment.from_agent.id != self.reciprocal_commitment.to_agent.id:
            raise ValidationError('Initiating commitment from_agent must be the reciprocal commitment to_agent.')
        if self.initiating_commitment.to_agent.id != self.reciprocal_commitment.from_agent.id:
            raise ValidationError('Initiating commitment to_agent must be the reciprocal commitment from_agent.')


class SelectedOption(models.Model):
    commitment = models.ForeignKey(Commitment, 
        related_name="options", verbose_name=_('commitment'))
    option = models.ForeignKey(Option, 
        related_name="commitments", verbose_name=_('option'))

    class Meta:
        ordering = ('commitment', 'option')

    def __unicode__(self):
        return " ".join([self.option.name, "option for", self.commitment.resource_type.name])


def update_summary(agent, project, resource_type):
    events = EconomicEvent.objects.filter(
        from_agent=agent,
        project=project,
        resource_type=resource_type,
        is_contribution=True)
    total = sum(event.quantity for event in events)
    summary, created = CachedEventSummary.objects.get_or_create(
        agent=agent,
        project=project,
        resource_type=resource_type)
    summary.quantity = total
    if summary.quantity:
        summary.save() 
    else:
        summary.delete()


class EconomicEvent(models.Model):
    event_type = models.ForeignKey(EventType, 
        related_name="events", verbose_name=_('event type'))
    event_date = models.DateField(_('event date'))
    from_agent = models.ForeignKey(EconomicAgent,
        blank=True, null=True,
        related_name="given_events", verbose_name=_('from'))
    to_agent = models.ForeignKey(EconomicAgent,
        blank=True, null=True,
        related_name="taken_events", verbose_name=_('to'))
    resource_type = models.ForeignKey(EconomicResourceType, 
        verbose_name=_('resource type'), related_name='events')
    resource = models.ForeignKey(EconomicResource, 
        blank=True, null=True,
        verbose_name=_('resource'), related_name='events')
    process = models.ForeignKey(Process,
        blank=True, null=True,
        verbose_name=_('process'), related_name='events',
        on_delete=models.SET_NULL)
    exchange = models.ForeignKey(Exchange,
        blank=True, null=True,
        verbose_name=_('exchange'), related_name='events',
        on_delete=models.SET_NULL)
    project = models.ForeignKey(Project,
        blank=True, null=True,
        verbose_name=_('project'), related_name='events',
        on_delete=models.SET_NULL)
    url = models.CharField(_('url'), max_length=255, blank=True)
    description = models.TextField(_('description'), null=True, blank=True)
    quantity = models.DecimalField(_('quantity'), max_digits=8, decimal_places=2)
    unit_of_quantity = models.ForeignKey(Unit, blank=True, null=True,
        verbose_name=_('unit'), related_name="event_qty_units")
    quality = models.DecimalField(_('quality'), max_digits=3, decimal_places=0, default=Decimal("0"))
    value = models.DecimalField(_('value'), max_digits=8, decimal_places=2, 
        default=Decimal("0.0"))
    unit_of_value = models.ForeignKey(Unit, blank=True, null=True,
        verbose_name=_('unit of value'), related_name="event_value_units")
    commitment = models.ForeignKey(Commitment, blank=True, null=True,
        verbose_name=_('fulfills commitment'), related_name="fulfillment_events",
        on_delete=models.SET_NULL)
    is_contribution = models.BooleanField(_('is contribution'), default=False)
    created_by = models.ForeignKey(User, verbose_name=_('created by'),
        related_name='events_created', blank=True, null=True, editable=False)
    changed_by = models.ForeignKey(User, verbose_name=_('changed by'),
        related_name='events_changed', blank=True, null=True, editable=False)
    
    slug = models.SlugField(_("Page name"), editable=False)

    class Meta:
        ordering = ('-event_date',)

    def __unicode__(self):
        if self.unit_of_quantity:
            quantity_string = " ".join([str(self.quantity), self.unit_of_quantity.abbrev])
        else:
            quantity_string = str(self.quantity)
        from_agt = 'Unassigned'
        if self.from_agent:
            from_agt = self.from_agent.name
        to_agt = 'Unassigned'
        if self.to_agent:
            to_agt = self.to_agent.name
        resource_string = self.resource_type.name
        if self.resource:
            resource_string = str(self.resource)
        return ' '.join([
            self.event_type.name,
            self.event_date.strftime('%Y-%m-%d'),
            'from',
            from_agt,
            'to',
            to_agt,
            quantity_string,
            resource_string,
        ])
        
    def save(self, *args, **kwargs):
        #import pdb; pdb.set_trace()
        from_agt = 'Unassigned'
        agent = self.from_agent
        project = self.project
        resource_type = self.resource_type
        delta = self.quantity
        agent_change = False
        project_change = False
        resource_type_change = False
        if self.pk:
            prev_agent = self.from_agent
            prev_project = self.project
            prev_resource_type = self.resource_type
            prev = EconomicEvent.objects.get(pk=self.pk)
            if prev.quantity != self.quantity:
                delta = self.quantity - prev.quantity
            if prev.from_agent != self.from_agent:
                agent_change = True
                prev_agent = prev.from_agent
            if prev.project != self.project:
                project_change = True
                prev_project = prev.project 
            if prev.resource_type != self.resource_type:
                resource_type_change = True
                prev_resource_type = prev.resource_type
        if agent:
            from_agt = agent.name
            if delta:
                #todo: suppliers shd also get ART scores
                if self.event_type.relationship == "work" or self.event_type.related_to == "agent":
                    try:
                        art, created = AgentResourceType.objects.get_or_create(
                            agent=agent,
                            resource_type=resource_type,
                            event_type=self.event_type)
                    except:
                        #todo: this shd not happen, but it does...
                        arts = AgentResourceType.objects.filter(
                            agent=agent,
                            resource_type=resource_type,
                            event_type=self.event_type)
                        art = arts[0]
                    art.score += delta
                    art.save()
        
        slug = "-".join([
            str(self.event_type.name),
            from_agt,
            self.event_date.strftime('%Y-%m-%d'),
        ])
        unique_slugify(self, slug)
        super(EconomicEvent, self).save(*args, **kwargs)
        update_summary(agent, project, resource_type)
        if agent_change or project_change or resource_type_change:
            update_summary(prev_agent, prev_project, prev_resource_type)

    def delete(self, *args, **kwargs):
        if self.event_type.relationship == "work":
            if self.is_contribution:
                agent = self.from_agent
                project = self.project
                resource_type = self.resource_type
                if agent and project and resource_type:
                    try:
                        summary = CachedEventSummary.objects.get(
                            agent=agent,
                            project=project,
                            resource_type=resource_type)
                        summary.quantity -= self.quantity
                        if summary.quantity:
                            summary.save() 
                        else:
                            summary.delete()
                    except CachedEventSummary.DoesNotExist:
                        pass
        super(EconomicEvent, self).delete(*args, **kwargs)

    def flow_type(self):
        return self.event_type.name

    def flow_class(self):
        return self.event_type.relationship

    def flow_description(self):
        quantity_string = ""
        if self.event_type.relationship != "cite":
            if self.unit_of_quantity:
                quantity_string = " ".join([str(self.quantity), self.unit_of_quantity.abbrev])
            else:
                quantity_string = str(self.quantity)
        from_agt = ''
        if self.from_agent:
            from_agt = ' '.join(["from", self.from_agent.name])
        to_agt = ''
        if self.to_agent:
            to_agt = ' '.join(["to", self.to_agent.name])
        resource_string = self.resource_type.name
        if self.resource:
            resource_string = str(self.resource)
        return ' '.join([
            self.event_date.strftime('%Y-%m-%d'),
            from_agt,
            to_agt,
            quantity_string,
            resource_string,
        ])
        
    def my_compensations(self):
        return self.initiated_compensations.all()

    def compensation(self):
        return sum(c.compensating_value for c in self.my_compensations())

    def value_due(self):
        return self.value - self.compensation()

    def is_compensated(self):
        if self.value_due() > 0:
            return False
        return True

    def unit(self):
        if self.unit_of_quantity:
            return self.unit_of_quantity.abbrev
        else:
            return self.resource_type.unit_of_quantity.abbrev

    def quantity_formatted(self):
        return " ".join([
            str(self.quantity.quantize(Decimal('.01'), rounding=ROUND_UP)),
            self.unit(),
            ])

    def work_event_change_form(self):
        from valuenetwork.valueaccounting.forms import WorkEventChangeForm
        return WorkEventChangeForm(instance=self)

    def unplanned_work_event_change_form(self):
        from valuenetwork.valueaccounting.forms import UnplannedWorkEventForm
        return UnplannedWorkEventForm(instance=self, prefix=str(self.id))

    def change_date_form(self):
        from valuenetwork.valueaccounting.forms import EventChangeDateForm
        return EventChangeDateForm(instance=self, prefix=str(self.id))

    def change_quantity_form(self):
        from valuenetwork.valueaccounting.forms import EventChangeQuantityForm
        return EventChangeQuantityForm(instance=self, prefix=str(self.id))

    def doer(self):
        if self.event_type.consumes_resources():
            return self.to_agent
        else:
            return self.from_agent

    def does_todo(self):
        if self.commitment:
            if self.commitment.event_type.relationship == "todo":
                return True
        return False

    def creates_resources(self):
        return self.event_type.creates_resources()

    def consumes_resources(self):
        return self.event_type.consumes_resources()


#todo: not used
class Compensation(models.Model):
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
    initiating_event = models.ForeignKey(EconomicEvent, 
        related_name="initiated_compensations", verbose_name=_('initiating event'))
    compensating_event = models.ForeignKey(EconomicEvent, 
        related_name="compensations", verbose_name=_('compensating event'))
    compensation_date = models.DateField(_('compensation date'), default=datetime.date.today)
    compensating_value = models.DecimalField(_('compensating value'), max_digits=8, decimal_places=2)

    class Meta:
        ordering = ('compensation_date',)

    def __unicode__(self):
        value_string = '$' + str(self.compensating_value)
        return ' '.join([
            'inititating event:',
            self.initiating_event.__unicode__(),
            'compensating event:',
            self.compensating_event.__unicode__(),
            'value:',
            value_string,
        ])

    def clean(self):
        #import pdb; pdb.set_trace()
        if self.initiating_event.from_agent.id != self.compensating_event.to_agent.id:
            raise ValidationError('Initiating event from_agent must be the compensating event to_agent.')
        if self.initiating_event.to_agent.id != self.compensating_event.from_agent.id:
            raise ValidationError('Initiating event to_agent must be the compensating event from_agent.')
        #if self.initiating_event.unit_of_value.id != self.compensating_event.unit_of_value.id:
        #    raise ValidationError('Initiating event and compensating event must have the same units of value.')



class EventSummary(object):
    def __init__(self, agent, project, resource_type, quantity, value=Decimal('0.0')):
        self.agent = agent
        self.project = project
        self.resource_type = resource_type
        self.quantity = quantity
        self.value=value

    def key(self):
        return "-".join([str(self.agent.id), str(self.resource_type.id)])

    def quantity_formatted(self):
        return self.quantity.quantize(Decimal('.01'), rounding=ROUND_UP)



class CachedEventSummary(models.Model):
    agent = models.ForeignKey(EconomicAgent,
        blank=True, null=True,
        related_name="cached_events", verbose_name=_('agent'))
    project = models.ForeignKey(Project,
        blank=True, null=True,
        verbose_name=_('project'), related_name='cached_events')
    resource_type = models.ForeignKey(EconomicResourceType,
        blank=True, null=True,
        verbose_name=_('resource type'), related_name='cached_events')
    resource_type_rate = models.DecimalField(_('resource type rate'), max_digits=8, decimal_places=2, default=Decimal("1.0"))
    importance = models.DecimalField(_('importance'), max_digits=3, decimal_places=0, default=Decimal("1"))
    reputation = models.DecimalField(_('reputation'), max_digits=8, decimal_places=2, 
        default=Decimal("1.00"))
    quantity = models.DecimalField(_('quantity'), max_digits=8, decimal_places=2, 
        default=Decimal("0.0"))
    value = models.DecimalField(_('value'), max_digits=8, decimal_places=2, 
        default=Decimal("0.0"))

    class Meta:
        ordering = ('agent', 'project', 'resource_type')

    def __unicode__(self):
        agent_name = "Unknown"
        if self.agent:
            agent_name = self.agent.name
        project_name = "Unknown"
        if self.project:
            project_name = self.project.name
        resource_type_name = "Unknown"
        if self.resource_type:
            resource_type_name = self.resource_type.name
        return ' '.join([
            'Agent:',
            agent_name,
            'Project:',
            project_name,
            'Resource Type:',
            resource_type_name,
        ])

    @classmethod
    def summarize_events(cls, project):
        #import pdb; pdb.set_trace()
        #todo: this code is obsolete, we don't want to roll up sub-projects anymore
        all_subs = project.with_all_sub_projects()
        event_list = EconomicEvent.objects.filter(project__in=all_subs)
        summaries = {}
        for event in event_list:
            key = "-".join([str(event.from_agent.id), str(event.project.id), str(event.resource_type.id)])
            if not key in summaries:
                summaries[key] = EventSummary(event.from_agent, event.project, event.resource_type, Decimal('0.0'))
            summaries[key].quantity += event.quantity
        summaries = summaries.values()
        for summary in summaries:
            ces = cls(
                agent=summary.agent,
                project=summary.project,
                resource_type=summary.resource_type,
                resource_type_rate=summary.resource_type.rate,
                importance=summary.project.importance,
                quantity=summary.quantity,
            )
            ces.save()
        return cls.objects.all()

    @classmethod
    def summarize_all_events(cls):
        #import pdb; pdb.set_trace()
        old_summaries = CachedEventSummary.objects.all()
        old_summaries.delete()
        event_list = EconomicEvent.objects.filter(is_contribution="true")
        summaries = {}
        #todo: very temporary hack
        project = Project.objects.get(name="Not defined")
        for event in event_list:
            #todo: very temporary hack
            if not event.project:
                event.project=project
                event.save()
            try:
                key = "-".join([str(event.from_agent.id), str(event.project.id), str(event.resource_type.id)])
                if not key in summaries:
                    summaries[key] = EventSummary(event.from_agent, event.project, event.resource_type, Decimal('0.0'))
                summaries[key].quantity += event.quantity
            except AttributeError:
                #todo: the event errors shd be fixed
                import pdb; pdb.set_trace()
        summaries = summaries.values()
        for summary in summaries:
            ces = cls(
                agent=summary.agent,
                project=summary.project,
                resource_type=summary.resource_type,
                resource_type_rate=summary.resource_type.rate,
                importance=summary.project.importance,
                quantity=summary.quantity,
            )
            ces.save()
        return cls.objects.all()


    def quantity_formatted(self):
        return self.quantity.quantize(Decimal('.01'), rounding=ROUND_UP)

    def value_formatted(self):
        return self.value.quantize(Decimal('.01'), rounding=ROUND_UP)


