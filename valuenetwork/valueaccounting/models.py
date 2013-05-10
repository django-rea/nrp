import datetime
import re
from decimal import *

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
)

class Help(models.Model):
    page = models.CharField(_('page'), max_length=16, choices=PAGE_CHOICES, unique=True)
    description = models.TextField(_('description'), blank=True, null=True)

    class Meta:
        verbose_name_plural = _('help')
        ordering = ('page',)
     
    def __unicode__(self):
        return self.get_page_display()


CATEGORIZATION_CHOICES = (
    ('Anything', _('Anything')),
    ('EconomicResourceType', _('EconomicResourceType')),
)


class Category(models.Model):
    name = models.CharField(_('name'), max_length=128)
    #todo: should applies_to go away?
    applies_to = models.CharField(_('applies to'), max_length=128, 
        choices=CATEGORIZATION_CHOICES,
        default='EconomicResourceType')
    description = models.TextField(_('description'), blank=True, null=True)
    orderable = models.BooleanField(_('orderable'), default=False,
        help_text=_('Should appear in Order form?'))

    class Meta:
        verbose_name_plural = _('categories')
        ordering = ('name',)
     
    def __unicode__(self):
        return self.name


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

    @classmethod
    def add_new_form(cls):
        return None

#todo: rethink?
ACTIVITY_CHOICES = (
    ('active', _('active contributor')),
    ('affiliate', _('close affiliate')),
    ('inactive', _('inactive contributor')),
    ('agent', _('active agent')),
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
        return self.resource_types.filter(relationship__direction='out')

    def produced_resource_types(self):
        return [ptrt.resource_type for ptrt in self.produced_resource_type_relationships()]

    def consumed_resource_type_relationships(self):
        return self.resource_types.filter(relationship__direction='in')

    def consumed_resource_types(self):
        return [ptrt.resource_type for ptrt in self.consumed_resource_type_relationships()]

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


RESOURCE_EFFECT_CHOICES = (
    ('+', _('increase')),
    ('-', _('decrease')),
    ('x', _('transfer')), #means - for from_agent, + for to_agent
    ('=', _('no effect')),
    ('<', _('failure')),
)

class EventType(models.Model):
    name = models.CharField(_('name'), max_length=128)
    resource_effect = models.CharField(_('resource effect'), 
        max_length=12, choices=RESOURCE_EFFECT_CHOICES)
    unit_type = models.CharField(_('unit type'), 
        max_length=12, choices=UNIT_TYPE_CHOICES,
        blank=True)
    slug = models.SlugField(_("Page name"), editable=False)

    class Meta:
        ordering = ('name',)

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        unique_slugify(self, self.name)
        super(EventType, self).save(*args, **kwargs)

    def creates_resources(self):
        return self.resource_effect == "+"

    def consumes_resources(self):
        return self.resource_effect == "-"


MATERIALITY_CHOICES = (
    ('material', _('material')),
    ('purchmatl', _('purchased material')),
    ('intellectual', _('intellectual')),
    ('work', _('work')),
    ('tool', _('tool')),
    ('purchtool', _('purchased tool')),
    ('space', _('space')),
    ('value', _('value')),
)

class EconomicResourceTypeManager(models.Manager):

    def types_of_work(self):
        return EconomicResourceType.objects.filter(materiality="work")

    def intellectual_resource_types(self):
        return EconomicResourceType.objects.filter(materiality="intellectual")

    def output_choices(self):
        rels = ResourceRelationship.objects.filter(direction="out", related_to="process")
        return [rel.materiality for rel in rels]

    def input_choices(self):
        rels = ResourceRelationship.objects.filter(direction="in", related_to="process")
        return [rel.materiality for rel in rels]

    def citable_choices(self):
        rels = ResourceRelationship.objects.filter(direction="cite", related_to="process")
        return [rel.materiality for rel in rels]

    def process_inputs(self):
        #import pdb; pdb.set_trace()
        choices = self.input_choices()
        return EconomicResourceType.objects.filter(materiality__in=choices)

    def process_outputs(self):
        choices = self.output_choices()
        return EconomicResourceType.objects.filter(materiality__in=choices)

    def process_citables_with_resources(self):
        choices = self.citable_choices()
        return [rt for rt in EconomicResourceType.objects.filter(materiality__in=choices) if rt.onhand()]


    def process_citables(self):
        choices = self.citable_choices()
        return EconomicResourceType.objects.filter(materiality__in=choices)

    def agent_outputs(self):
        ert_ids = [ert.id for ert in EconomicResourceType.objects.all() if ert.is_agent_output()]
        return EconomicResourceType.objects.filter(id__in=ert_ids)

    def agent_inputs(self):
        ert_ids = [ert.id for ert in EconomicResourceType.objects.all() if ert.is_agent_input()]
        return EconomicResourceType.objects.filter(id__in=ert_ids)



class EconomicResourceType(models.Model):
    name = models.CharField(_('name'), max_length=128)
    #version = models.CharField(_('version'), max_length=32, blank=True)    
    parent = models.ForeignKey('self', blank=True, null=True, 
        verbose_name=_('parent'), related_name='children', editable=False)
    #stage = models.ForeignKey(Stage, blank=True, null=True, 
    #    verbose_name=_('stage'), related_name='resource_types')
    category = models.ForeignKey(Category, 
        verbose_name=_('category'), related_name='resource_types',
        limit_choices_to=Q(applies_to='Anything') | Q(applies_to='EconomicResourceType'))
    #todo: needs better name.  Technically, is supertype.
    materiality = models.CharField(_('behavior'), 
        max_length=12, choices=MATERIALITY_CHOICES,
        default='material')
    unit = models.ForeignKey(Unit, blank=True, null=True,
        verbose_name=_('unit'), related_name="resource_units",
        help_text=_('if this resource has different units of use and inventory, this is the unit of use'))
    photo = ThumbnailerImageField(_("photo"),
        upload_to='photos', blank=True, null=True)
    photo_url = models.CharField(_('photo url'), max_length=255, blank=True)
    url = models.CharField(_('url'), max_length=255, blank=True)
    description = models.TextField(_('description'), blank=True, null=True)
    rate = models.DecimalField(_('rate'), max_digits=6, decimal_places=2, default=Decimal("0.00"), editable=False)
    created_by = models.ForeignKey(User, verbose_name=_('created by'),
        related_name='resource_types_created', blank=True, null=True, editable=False)
    changed_by = models.ForeignKey(User, verbose_name=_('changed by'),
        related_name='resource_types_changed', blank=True, null=True, editable=False)
    created_date = models.DateField(auto_now_add=True, blank=True, null=True, editable=False)
    changed_date = models.DateField(auto_now=True, blank=True, null=True, editable=False)
    slug = models.SlugField(_("Page name"), editable=False)
    
    objects = EconomicResourceTypeManager()

    class Meta:
        #ordering = ('category', 'name', 'stage')
        #unique_together = ('name', 'version', 'stage')
        ordering = ('category', 'name')
        unique_together = ('name', 'category')
        verbose_name = _('resource type')
    
    def __unicode__(self):
        #stage_name = ""
        #if self.stage:
        #    stage_name = self.stage.name
        #return " ".join([self.category.name, self.name, self.version, stage_name])
        return " - ".join([self.category.name, self.name])

    def label(self):
        return self.__unicode__()
    
    @classmethod
    def add_new_form(cls):
        from valuenetwork.valueaccounting.forms import EconomicResourceTypeWithPopupForm
        return EconomicResourceTypeWithPopupForm

    def save(self, *args, **kwargs):
        unique_slugify(self, self.name)
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

    def onhand_qty(self):
        return sum(oh.quantity for oh in self.onhand())

    def onhand_qty_for_commitment(self, commitment):
        oh_qty = self.onhand_qty()
        due_date = commitment.due_date
        priors = self.wanting_commitments().filter(due_date__lt=due_date)
        remainder = oh_qty - sum(p.quantity for p in priors)
        if remainder > 0:
            return remainder
        else:
            return Decimal("0")

    def scheduled_qty_for_commitment(self, commitment):
        sked_qty = self.scheduled_qty()
        due_date = commitment.due_date
        priors = self.wanting_commitments().filter(due_date__lt=due_date)
        remainder = sked_qty - sum(p.quantity for p in priors)
        if remainder > 0:
            return remainder
        else:
            return Decimal("0")

    def producing_process_type_relationships(self):
        return self.process_types.filter(relationship__direction='out')

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
        rels = ResourceRelationship.objects.filter(
            materiality=self.materiality,
            direction="out",
            related_to="process")
        return (rels.count() > 0)

    def is_process_input(self):
        rels = ResourceRelationship.objects.filter(
            materiality=self.materiality,
            direction="in",
            related_to="process")
        return (rels.count() > 0)

    def is_agent_output(self):
        rels = ResourceRelationship.objects.filter(
            materiality=self.materiality,
            direction="out",
            related_to="agent")
        return (rels.count() > 0)

    def is_agent_input(self):
        rels = ResourceRelationship.objects.filter(
            materiality=self.materiality,
            direction="in",
            related_to="agent")
        return (rels.count() > 0)

    def consuming_process_type_relationships(self):
        return self.process_types.filter(relationship__direction='in')

    def wanting_commitments(self):
        return self.commitments.filter(
            finished=False,
            relationship__direction='in')

    def consuming_process_types(self):
        return [pt.process_type for pt in self.consuming_process_type_relationships()]

    def producing_agent_relationships(self):
        return self.agents.filter(relationship__direction='out')

    def consuming_agent_relationships(self):
        return self.agents.filter(relationship__direction='in')

    def consuming_agents(self):
        return [art.agent for art in self.consuming_agent_relationships()]

    def producing_agents(self):
        return [art.agent for art in self.producing_agent_relationships()]

    #todo: hacks based on name 'distributes' which is user-changeable
    def distributor_relationships(self):
        return self.agents.filter(relationship__name='distributes')

    def distributors(self):
        return [art.agent for art in self.distributor_relationships()]

    def producer_relationships(self):
        return self.agents.filter(relationship__direction='out').exclude(relationship__name='distributes')

    def producers(self):
        arts = self.producer_relationships()
        return [art.agent for art in arts]

    #todo: failures do not have commitments. If and when they do, the next two methods must change.
    def producing_commitments(self):
        return self.commitments.filter(
            relationship__event_type__resource_effect='+')

    def consuming_commitments(self):
        return self.commitments.filter(
            relationship__event_type__resource_effect='-')

    def scheduled_qty(self):
        return sum(pc.quantity for pc in self.producing_commitments())

    def xbill_parents(self):
        answer = list(self.consuming_process_type_relationships())
        answer.extend(list(self.options.all()))
        #answer.append(self)
        return answer

    def xbill_children(self):
        answer = []
        answer.extend(self.producing_process_type_relationships())
        answer.extend(self.producer_relationships())
        answer.extend(self.distributor_relationships())
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

    def xbill_category(self):
        return self.category

    def change_form(self):
        from valuenetwork.valueaccounting.forms import EconomicResourceTypeForm
        return EconomicResourceTypeForm(instance=self)

    def resource_create_form(self, prefix):
        from valuenetwork.valueaccounting.forms import EconomicResourceForm
        init = {"unit_of_quantity": self.unit,}
        return EconomicResourceForm(prefix=prefix, initial=init)

    def directional_unit(self, direction):
        answer = self.unit
        try:
            rel = ResourceRelationship.objects.get(
                materiality=self.materiality,
                related_to='process',
                direction=direction)
            if rel.unit:
                answer = rel.unit
        except ResourceRelationship.DoesNotExist:
            pass
        return answer

    def process_input_unit(self):
        answer = self.unit
        try:
            rel = ResourceRelationship.objects.get(
                materiality=self.materiality,
                related_to='process',
                direction='in')
            if rel.unit:
                answer = rel.unit
        except ResourceRelationship.DoesNotExist:
            pass
        return answer

    def process_output_unit(self):
        answer = self.unit
        try:
            rel = ResourceRelationship.objects.get(
                materiality=self.materiality,
                related_to='process',
                direction='out')
            if rel.unit:
                answer = rel.unit
        except ResourceRelationship.DoesNotExist:
            pass
        return answer

    def is_deletable(self):
        answer = True
        if self.events.all():
            answer = False
        elif self.resources.all():
            answer = False
        elif self.commitments.all():
            answer = False
        return answer

    def production_resource_relationship(self):
        try:
            rel = ResourceRelationship.objects.get(
                materiality=self.materiality,
                related_to='process',
                direction='out')
        except ResourceRelationship.DoesNotExist:
            rel = None
        return rel

    def citation_resource_relationship(self):
        try:
            rel = ResourceRelationship.objects.get(
                materiality=self.materiality,
                related_to='process',
                direction='cite')
        except ResourceRelationship.DoesNotExist:
            rel = None
        return rel

    def work_resource_relationship(self):
        try:
            rel = ResourceRelationship.objects.get(
                materiality='work',
                related_to='process',
                direction='in')
        except ResourceRelationship.DoesNotExist:
            rel = None
        return rel
        

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
    url = models.CharField(_('url'), max_length=255, blank=True)
    author = models.ForeignKey(EconomicAgent, related_name="authored_resources",
        verbose_name=_('author'), blank=True, null=True)
    owner = models.ForeignKey(EconomicAgent, related_name="owned_resources",
        verbose_name=_('owner'), blank=True, null=True)
    custodian = models.ForeignKey(EconomicAgent, related_name="custody_resources",
        verbose_name=_('custodian'), blank=True, null=True)
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
        return " ".join([
            self.resource_type.name,
            id_str,
        ])

    def label(self):
        return self.identifier or str(self.id)

    def change_form(self, prefix):
        from valuenetwork.valueaccounting.forms import EconomicResourceForm
        return EconomicResourceForm(prefix=prefix, instance=self)

    def producing_events(self):
        if self.quality:
            if self.quality < 0:
               return self.events.filter(event_type__resource_effect='<') 
        return self.events.filter(event_type__resource_effect='+')

    def using_events(self):
        return []

    def is_cited(self):
        #import pdb; pdb.set_trace()
        answer = False
        rel = ResourceRelationship.objects.get(
            materiality=self.resource_type.materiality,
            direction='cite')
        for event in self.events.all():
            if event.event_type == rel.event_type:
                answer = True
        return answer

    def label_with_cited(self):
        if self.is_cited:
            cited = ' (Cited)'
        else:
            cited = ''
        return (self.identifier or str(self.id)) + cited


DIRECTION_CHOICES = (
    ('in', _('input')),
    ('out', _('output')),
    ('cite', _('citation')),
    ('todo', _('todo')),
)

RELATED_CHOICES = (
    ('process', _('process')),
    ('agent', _('agent')),
)

class ResourceRelationship(models.Model):
    name = models.CharField(_('name'), max_length=32)
    inverse_name = models.CharField(_('inverse name'), max_length=40, blank=True)
    direction = models.CharField(_('direction'), 
        max_length=12, choices=DIRECTION_CHOICES, default='in')
    related_to = models.CharField(_('related to'), 
        max_length=12, choices=RELATED_CHOICES, default='process')
    materiality = models.CharField(_('behavior'), 
        max_length=12, choices=MATERIALITY_CHOICES,
        default='material',
        help_text=_('this links Economic Resource Types to Resource Relationships'))
    event_type = models.ForeignKey(EventType,
        blank=True, null=True,
        verbose_name=_('event type'), related_name='resource_relationships')
    unit = models.ForeignKey(Unit, blank=True, null=True,
        verbose_name=_('unit'), related_name="relationship_units",
        help_text=_('optional - overriding the Resource Type unit'))

    class Meta:
        unique_together = ('related_to', 'direction', 'materiality')
        ordering = ('name', )

    def __unicode__(self):
        return self.name

    @classmethod
    def add_new_form(cls):
        return None

    def inverse_label(self):
        if self.inverse_name:
            return self.inverse_name
        else:
            return self.name

    def infer_label(self):
        #todo: need to consider new direction choices?
        if self.direction == "out":
            return self.inverse_name
        else:
            return self.name

    def doing_agent(self):
        if self.direction == "out":
            return "from"
        else:
            return "to"


class AgentResourceType(models.Model):
    agent = models.ForeignKey(EconomicAgent,
        verbose_name=_('agent'), related_name='resource_types')
    resource_type = models.ForeignKey(EconomicResourceType, 
        verbose_name=_('resource type'), related_name='agents')
    score = models.DecimalField(_('score'), max_digits=8, decimal_places=2, 
        default=Decimal("0.0"),
        help_text=_("the quantity of contributions of this resource type from this agent"))
    relationship = models.ForeignKey(ResourceRelationship,
        verbose_name=_('relationship'), related_name='agent_resource_types')
    lead_time = models.IntegerField(_('lead time'), 
        default=0, help_text=_("in days"))
    value = models.DecimalField(_('value'), max_digits=8, decimal_places=2, 
        default=Decimal("0.0"))
    unit_of_value = models.ForeignKey(Unit, blank=True, null=True,
        limit_choices_to={'unit_type': 'value'},
        verbose_name=_('unit of value'), related_name="agent_resource_value_units")
    created_by = models.ForeignKey(User, verbose_name=_('created by'),
        related_name='arts_created', blank=True, null=True, editable=False)
    changed_by = models.ForeignKey(User, verbose_name=_('changed by'),
        related_name='arts_changed', blank=True, null=True, editable=False)
    created_date = models.DateField(auto_now_add=True, blank=True, null=True, editable=False)
    changed_date = models.DateField(auto_now=True, blank=True, null=True, editable=False)

    def __unicode__(self):
        return ' '.join([
            self.agent.name,
            self.relationship.name,
            self.resource_type.name,
        ])

    def label(self):
        return "source"

    def timeline_title(self):
        return " ".join(["Get ", self.resource_type.name, "from ", self.agent.name])

    def inverse_label(self):
        return self.relationship.inverse_label()

    def xbill_label(self):
        return self.relationship.infer_label()

    def xbill_explanation(self):
        return "Source"

    def xbill_child_object(self):
        if self.relationship.direction == 'out':
            return self.agent
        else:
            return self.resource_type

    def xbill_class(self):
        return self.xbill_child_object().xbill_class()

    def xbill_category(self):
        return Category(name="sources")

    def xbill_parent_object(self):
        if self.relationship.direction == 'out':
            return self.resource_type
        else:
            return self.agent

    def node_id(self):
        return "-".join(["AgentResource", str(self.id)])

    def xbill_change_prefix(self):
        return "".join(["AR", str(self.id)])

    def xbill_change_form(self):
        from valuenetwork.valueaccounting.forms import AgentResourceTypeForm
        #return AgentResourceTypeForm(instance=self, prefix=self.xbill_change_prefix())
        return AgentResourceTypeForm(instance=self)

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
        

class Project(models.Model):
    name = models.CharField(_('name'), max_length=128) 
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
            resource_type__materiality="work"))

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


class ProcessType(models.Model):
    name = models.CharField(_('name'), max_length=128)
    parent = models.ForeignKey('self', blank=True, null=True, 
        verbose_name=_('parent'), related_name='sub_process_types', editable=False)
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
        return self.resource_types.filter(relationship__direction='out')

    def produced_resource_types(self):
        return [ptrt.resource_type for ptrt in self.produced_resource_type_relationships()]

    def main_produced_resource_type(self):
        prts = self.produced_resource_types()
        if prts:
            return prts[0]
        else:
            return None

    def consumed_resource_type_relationships(self):
        return self.resource_types.filter(relationship__direction='in')

    def consumed_resource_types(self):
        return [ptrt.resource_type for ptrt in self.consumed_resource_type_relationships()]

    def xbill_parents(self):
        return self.produced_resource_type_relationships()

    def xbill_children(self):
        kids = list(self.consumed_resource_type_relationships())
        kids.extend(self.features.all())
        return kids

    def xbill_explanation(self):
        return "Process Type"

    def xbill_change_prefix(self):
        return "".join(["PT", str(self.id)])

    def xbill_change_form(self):
        from valuenetwork.valueaccounting.forms import ChangeProcessTypeForm
        #return ChangeProcessTypeForm(instance=self, prefix=self.xbill_change_prefix())
        return ChangeProcessTypeForm(instance=self)

    def xbill_input_prefix(self):
        return "".join(["PTINPUT", str(self.id)])

    def xbill_input_form(self):
        from valuenetwork.valueaccounting.forms import ProcessTypeResourceTypeForm
        return ProcessTypeResourceTypeForm(prefix=self.xbill_input_prefix())
        #return ProcessTypeResourceTypeForm()

    def xbill_class(self):
        return "process-type"

#todo: better name?  Maybe ProcessTypeInputOutput?
class ProcessTypeResourceType(models.Model):
    process_type = models.ForeignKey(ProcessType,
        verbose_name=_('process type'), related_name='resource_types')
    resource_type = models.ForeignKey(EconomicResourceType, 
        verbose_name=_('resource type'), related_name='process_types')
    relationship = models.ForeignKey(ResourceRelationship,
        verbose_name=_('relationship'), related_name='process_resource_types')
    quantity = models.DecimalField(_('quantity'), max_digits=8, decimal_places=2, default=Decimal('0.00'))
    unit_of_quantity = models.ForeignKey(Unit, blank=True, null=True,
        verbose_name=_('unit'), related_name="process_resource_qty_units")
    created_by = models.ForeignKey(User, verbose_name=_('created by'),
        related_name='ptrts_created', blank=True, null=True, editable=False)
    changed_by = models.ForeignKey(User, verbose_name=_('changed by'),
        related_name='ptrts_changed', blank=True, null=True, editable=False)
    created_date = models.DateField(auto_now_add=True, blank=True, null=True, editable=False)
    changed_date = models.DateField(auto_now=True, blank=True, null=True, editable=False)

    class Meta:
        ordering = ('resource_type',)

    def __unicode__(self):
        relname = ""
        if self.relationship:
            relname = self.relationship.name
        return " ".join([self.process_type.name, relname, str(self.quantity), self.resource_type.name])        

    def inverse_label(self):
        return self.relationship.inverse_label()

    def xbill_label(self):
        if self.relationship.direction == 'out':
            return self.inverse_label()
        else:
           abbrev = ""
           if self.unit_of_quantity:
               abbrev = self.unit_of_quantity.abbrev
           return " ".join([self.relationship.name, str(self.quantity), abbrev])

    def xbill_explanation(self):
        if self.relationship.direction == 'out':
            return "Process Type"
        else:
            return "Input"

    def xbill_child_object(self):
        if self.relationship.direction == 'out':
            return self.process_type
        else:
            return self.resource_type

    def xbill_class(self):
        return self.xbill_child_object().xbill_class()

    def xbill_parent_object(self):
        if self.relationship.direction == 'out':
            return self.resource_type
            #if self.resource_type.category.name == 'option':
            #    return self
            #else:
            #    return self.resource_type
        else:
            return self.process_type

    def xbill_parents(self):
        return [self.resource_type, self]

    def xbill_category(self):
        if self.relationship.direction == 'out':
            return Category(name="processes")
        else:
            return self.resource_type.category

    def node_id(self):
        return "-".join(["ProcessResource", str(self.id)])

    def xbill_change_prefix(self):
        return "".join(["PTRT", str(self.id)])

    def xbill_change_form(self):
        from valuenetwork.valueaccounting.forms import ProcessTypeResourceTypeForm, LaborInputForm
        if self.resource_type.materiality == "work":
            return LaborInputForm(instance=self, prefix=self.xbill_change_prefix())
        else:
            return ProcessTypeResourceTypeForm(instance=self, prefix=self.xbill_change_prefix())

class ProcessManager(models.Manager):

    def unfinished(self):
        return Process.objects.filter(finished=False)

    def finished(self):
        return Process.objects.filter(finished=True)


class Process(models.Model):
    name = models.CharField(_('name'), max_length=128)
    parent = models.ForeignKey('self', blank=True, null=True, 
        verbose_name=_('parent'), related_name='sub_processes', editable=False)
    process_type = models.ForeignKey(ProcessType,
        blank=True, null=True,
        verbose_name=_('process type'), related_name='processes')
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
        ordering = ('name',)
        verbose_name_plural = _("processes")

    def __unicode__(self):
        return " ".join([
            self.name,
            "ending",
            self.end_date.strftime('%Y-%m-%d'),
            "starting",
            self.start_date.strftime('%Y-%m-%d'),
            ])

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

    def label(self):
        return "process"

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

    def incoming_commitments(self):
        return self.commitments.filter(
            relationship__direction='in')

    def schedule_requirements(self):
        return self.commitments.exclude(
            relationship__direction='out')

    def outgoing_commitments(self):
        return self.commitments.filter(
            relationship__direction='out')

    def main_outgoing_commitment(self):
        cts = self.outgoing_commitments()
        if cts:
            return cts[0]
        else:
            return None

    #todo: both prev and next processes need more testing
    def previous_processes_old(self):
        answer = []
        dmnd = None
        moc = self.main_outgoing_commitment()
        #import pdb; pdb.set_trace()
        if moc:
            dmnd = moc.independent_demand
        output_rts = [oc.resource_type for oc in self.outgoing_commitments()]
        for ic in self.incoming_commitments():
            rt = ic.resource_type
            # this is to block cycles
            if rt not in output_rts:
                for pc in rt.producing_commitments():
                    if dmnd:
                        if pc.independent_demand == dmnd:
                            answer.append(pc.process)
                    else:
                        if not pc.independent_demand:
                            if pc.quantity >= ic.quantity:
                                if pc.due_date >= self.start_date:
                                    answer.append(pc.process)
        return answer

    def previous_processes(self):
        answer = []
        dmnd = None
        moc = self.main_outgoing_commitment()
        #import pdb; pdb.set_trace()
        if moc:
            dmnd = moc.independent_demand
        output_rts = [oc.resource_type for oc in self.outgoing_commitments()]
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
                                if pc.due_date >= self.start_date:
                                    answer.append(pc.process)
        return answer

    def next_processes(self):
        answer = []
        #import pdb; pdb.set_trace()
        input_rts = [ic.resource_type for ic in self.incoming_commitments()]
        for oc in self.outgoing_commitments():
            dmnd = oc.independent_demand
            rt = oc.resource_type
            if rt not in input_rts:
                for cc in rt.consuming_commitments():
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
        return answer

    def material_requirements(self):
        answer = list(self.commitments.filter(
            #finished=False,
            relationship__direction='in',
            resource_type__materiality="material",
        ))
        answer.extend(self.commitments.filter(
            #finished=False,
            relationship__direction='in',
            resource_type__materiality="purchmatl",
        ))
        return answer


    def intellectual_requirements(self):
        return self.commitments.filter(
            #finished=False,
            relationship__direction='in',
            resource_type__materiality="intellectual",
        )

    def citation_requirements(self):
        return self.commitments.filter(
            relationship__direction='cite',
        )

    def tool_requirements(self):
        answer = list(self.commitments.filter(
            relationship__direction='in',
            resource_type__materiality='tool',
        ))
        answer.extend(list(self.commitments.filter(
            relationship__direction='in',
            resource_type__materiality='purchtool',
        )))
        return answer

    def space_requirements(self):
        return self.commitments.filter(
            relationship__direction='in',
            resource_type__materiality='space',
        )

    def work_requirements(self):
        return self.commitments.filter(
            relationship__direction='in',
            resource_type__materiality='work',
        )

    def unfinished_work_requirements(self):
        return self.commitments.filter(
            finished=False,
            relationship__direction='in',
            resource_type__materiality='work',
        )

    def non_work_requirements(self):
        return self.commitments.exclude(
            relationship__direction='in',
            resource_type__materiality='work',
        )

    def work_events(self):
        reqs = self.work_requirements()
        events = []
        for req in reqs:
            events.extend(req.fulfillment_events.all())
        return events

    def outputs(self):
        answer = []
        events = self.events.filter(quality__gte=0)
        for event in events:
            rels = ResourceRelationship.objects.filter(
                direction='out',
                related_to='process',
                event_type=event.event_type)
            if rels:
                answer.append(event)
        return answer

    def deliverables(self):
        return [output.resource for output in self.outputs() if output.resource]

    def failed_outputs(self):
        answer = []
        events = self.events.filter(quality__lt=0)
        for event in events:
            rels = ResourceRelationship.objects.filter(
                direction='out',
                related_to='process')
            if rels:
                answer.append(event)
        return answer

    def inputs(self):
        answer = []
        events = self.events.all()
        for event in events:
            rels = ResourceRelationship.objects.filter(
                direction='in',
                related_to='process',
                event_type=event.event_type)
            if rels:
                answer.append(event)
        return answer

    def citations(self):
        answer = []
        events = self.events.all()
        for event in events:
            rels = ResourceRelationship.objects.filter(
                direction='cite',
                event_type=event.event_type)
            if rels:
                answer.append(event)
        return answer

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

    def inputs_used_by_agent(self, agent):
        answer = []
        for event in self.inputs():
            if event.to_agent == agent:
                if event.resource_type.materiality != 'work':
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


class Feature(models.Model):
    name = models.CharField(_('name'), max_length=128)
    option_category = models.ForeignKey(Category,
        verbose_name=_('option category'), related_name='features',
        blank=True, null=True,
        help_text=_("option selections will be limited to this category"),
        limit_choices_to=Q(applies_to='Anything') | Q(applies_to='EconomicResourceType'))
    product = models.ForeignKey(EconomicResourceType, 
        related_name="features", verbose_name=_('product'))
    process_type = models.ForeignKey(ProcessType,
        blank=True, null=True,
        verbose_name=_('process type'), related_name='features')
    relationship = models.ForeignKey(ResourceRelationship,
        verbose_name=_('relationship'), related_name='features')
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

    def xbill_category(self):
        return Category(name="features")

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

    def xbill_category(self):
        return Category(name="features")

    def node_id(self):
        return "-".join(["Option", str(self.id)])

    def xbill_parents(self):
        return [self.feature, self]


ORDER_TYPE_CHOICES = (
    ('customer', _('Customer order')),
    ('rand', _('R&D order')),
    ('holder', _('Placeholder order')),
)

#todo: Order is used for both of the above types.
#maybe shd be renamed?
class Order(models.Model):
    order_type = models.CharField(_('order type'), max_length=12, 
        choices=ORDER_TYPE_CHOICES, default='customer')
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
        provider_name = "Unknown"
        process_name = ""
        process = self.process()
        if process:
            process_name = ", " + process.name
        if self.provider:
            provider_name = self.provider.name
        receiver_name = "Unknown"
        if self.receiver:
            receiver_name = self.receiver.name
        return " ".join(
            [self.get_order_type_display(), 
            str(self.id), 
            process_name,
            ", provider:", 
            provider_name, 
            "receiver:", 
            receiver_name, 
            "due:",
            self.due_date.strftime('%Y-%m-%d'),
            ])

    @models.permalink
    def get_absolute_url(self):
        return ('order_schedule', (),
            { 'order_id': str(self.id),})

    def timeline_title(self):
        return self.__unicode__()

    def timeline_description(self):
        return self.description

    def producing_commitments(self):
        return self.commitments.all()

    def order_items(self):
        return self.commitments.all()

    def material_requirements(self):
        return []

    def tool_requirements(self):
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


class CommitmentManager(models.Manager):

    def unfinished(self):
        return Commitment.objects.filter(finished=False)

    def finished(self):
        return Commitment.objects.filter(finished=True)

    def todos(self):
        return Commitment.objects.filter(
            relationship__direction="todo",
            finished=False)


class Commitment(models.Model):
    order = models.ForeignKey(Order,
        blank=True, null=True,
        related_name="commitments", verbose_name=_('order'))
    independent_demand = models.ForeignKey(Order,
        blank=True, null=True,
        related_name="dependent_commitments", verbose_name=_('independent_demand'))
    event_type = models.ForeignKey(EventType, 
        related_name="commitments", verbose_name=_('event type'))
    relationship = models.ForeignKey(ResourceRelationship,
        verbose_name=_('relationship'), related_name='commitments')
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
            if self.relationship.direction == "out":
                name1 = from_agt
                name2 = to_agt
                prep = "for"
            else:
                name2 = from_agt
                name1 = to_agt
                prep = "from"
            return ' '.join([
                name1,
                self.relationship.name,
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
                self.relationship.name,
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
        super(Commitment, self).save(*args, **kwargs)

    def label(self):
        return self.relationship.get_direction_display()

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
        answer = []
        resources = EconomicResource.goods.filter(resource_type=self.resource_type)
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

    def quantity_to_buy(self):
        onhand = self.onhand()       
        if self.resource_type.materiality == "material":
            if not self.resource_type.producing_commitments():
                qty =  self.unfilled_quantity() - sum(oh.quantity for oh in self.onhand())
                if qty > Decimal("0"):
                    return qty
        else:
            if not onhand:
                if not self.resource_type.producing_commitments():
                    return Decimal("1")
        return Decimal("0")

    def net(self):
        rt = self.resource_type
        oh_qty = rt.onhand_qty_for_commitment(self)
        if oh_qty >= self.quantity:
            return 0
        remainder = self.quantity - oh_qty
        sked_qty = rt.scheduled_qty_for_commitment(self)
        if sked_qty >= remainder:
            return 0
        return remainder - sked_qty
  
    def creates_resources(self):
        return self.event_type.creates_resources()

    def consumes_resources(self):
        return self.event_type.consumes_resources()

    def output_resources(self):
        answer = None
        if self.relationship.direction == "out":
            answer = [event.resource for event in self.fulfilling_events()]
        return answer

    def output_resource(self):
        #todo: this is a hack, cd be several resources
        answer = None
        if self.relationship.direction == "out":
            events = self.fulfilling_events()
            if events:
                event = events[0]
                answer = event.resource
        return answer


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
        quantity_string = str(self.quantity)
        from_agt = 'Unassigned'
        if self.from_agent:
            from_agt = self.from_agent.name
        to_agt = 'Unassigned'
        if self.to_agent:
            to_agt = self.to_agent.name
        return ' '.join([
            self.event_type.name,
            self.event_date.strftime('%Y-%m-%d'),
            'from',
            from_agt,
            'to',
            to_agt,
            quantity_string,
            self.resource_type.name,
        ])

    def save(self, *args, **kwargs):
        from_agt = 'Unassigned'
        if self.from_agent:
            from_agt = self.from_agent.name
            if self.commitment:
                relationship = self.commitment.relationship 
                art, created = AgentResourceType.objects.get_or_create(
                    agent=self.from_agent,
                    resource_type=self.resource_type,
                    relationship=relationship)
                art.score += self.quantity
                art.save()
        slug = "-".join([
            str(self.event_type.name),
            str(from_agt.id),
            self.event_date.strftime('%Y-%m-%d'),
        ])
        unique_slugify(self, slug)
        super(EconomicEvent, self).save(*args, **kwargs)


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
            if self.commitment.relationship.direction == "todo":
                return True
        return False


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
        return ' '.join([
            'Agent:',
            self.agent.name,
            'Project:',
            self.project.name,
            'Resource Type:',
            self.resource_type.name,
        ])

    @classmethod
    def summarize_events(cls, project):
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


    def quantity_formatted(self):
        return self.quantity.quantize(Decimal('.01'), rounding=ROUND_UP)

    def value_formatted(self):
        return self.value.quantize(Decimal('.01'), rounding=ROUND_UP)
