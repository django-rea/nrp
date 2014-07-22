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

def collect_trash(commitment, trash):
    # this method works for output commitments
    # collect_lower_trash works for inputs
    #import pdb; pdb.set_trace()
    order_item = commitment.order_item
    process = commitment.process
    if process:
        if process in trash:
            return trash
        trash.append(process)
        for inp in process.incoming_commitments():
            pcs = inp.associated_producing_commitments()
            if pcs:
                for pc in pcs:
                    if pc.order_item == order_item:
                        collect_trash(pc, trash)
    return trash

def collect_lower_trash(commitment, trash):
    # this method works for input commitments
    # collect_trash works for outputs
    order_item = commitment.order_item
    pcs = commitment.associated_producing_commitments()
    if pcs:
        for pc in pcs:
            if pc.order_item == order_item:
                collect_trash(pc, trash)
    return trash
    
#class Stage(models.Model):
#    name = models.CharField(_('name'), max_length=32)
#    sequence = models.IntegerField(_('sequence'), default=0)
    

#    class Meta:
#        ordering = ('sequence',)
     
#    def __unicode__(self):
#        return self.name
       

class HomePageLayout(models.Model):
    banner = models.TextField(_('banner'), blank=True, null=True,
        help_text=_("HTML text for top Banner"))
    use_work_panel = models.BooleanField(_('use work panel'), default=False,
        help_text=_("Work panel, if used, will be Panel 1"))
    work_panel_headline = models.TextField(_('work panel headline'), blank=True, null=True)
    use_needs_panel = models.BooleanField(_('use needs panel'), default=False,
        help_text=_("Needs panel, if used, will be Panel 2"))
    needs_panel_headline = models.TextField(_('needs panel headline'), blank=True, null=True)
    use_creations_panel = models.BooleanField(_('use creations panel'), default=False,
        help_text=_("Creations panel, if used, will be Panel 3"))
    creations_panel_headline = models.TextField(_('creations panel headline'), blank=True, null=True)
    panel_1 = models.TextField(_('panel 1'), blank=True, null=True,
        help_text=_("HTML text for Panel 1"))
    panel_2 = models.TextField(_('panel 2'), blank=True, null=True,
        help_text=_("HTML text for Panel 2"))
    panel_3 = models.TextField(_('panel 3'), blank=True, null=True,
        help_text=_("HTML text for Panel 3"))
    footer = models.TextField(_('footer'), blank=True, null=True)
    
    class Meta:
        verbose_name_plural = _('home page layout')
    

#for help text
PAGE_CHOICES = (
    ('agent', _('Agent')),
    ('all_work', _('All Work')),
    ('create_exchange', _('Create Exchange')),
    ('demand', _('Demand')),
    ('ed_asmbly_recipe', _('Edit Assembly Recipes')),
    ('ed_wf_recipe', _('Edit Workflow Recipes')),
    ('exchange', _('Exchange')),
    ('home', _('Home')),
    ('inventory', _('Inventory')),
    ('labnotes', _('Labnotes Form')),
    ('associations', _('Maintain Associations')),
    ('my_work', _('My Work')),
    ('non_production', _('Non-production time logging')),
    ('projects', _('Organization')),
    ("plan_from_recipe", _('Plan from recipe')),
    ("plan_from_rt", _('Plan from Resource Type')),
    ("plan_fr_rt_rcpe", _('Plan from Resource Type Recipe')),
    ('process', _('Process')),
    ('process_select', _('Process Selections')),
    ('recipes', _('Recipes')),
    ('resource_types', _('Resource Types')),
    ('resource_type', _('Resource Type')),
    ('supply', _('Supply')),
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
    ('team', _('project')),
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

        
class AgentTypeManager(models.Manager):
    
    def context_agent_types(self):
        return AgentType.objects.filter(is_context=True)
        
    def context_types_string(self):
        return " or ".join([ at.name for at in self.context_agent_types()])
        
    def non_context_agent_types(self):
        return AgentType.objects.filter(is_context=False)
        
class AgentType(models.Model):
    name = models.CharField(_('name'), max_length=128)
    parent = models.ForeignKey('self', blank=True, null=True, 
        verbose_name=_('parent'), related_name='sub-agents', editable=False)
    #member_type = models.CharField(_('member type'), 
    #    max_length=12, choices=ACTIVITY_CHOICES,
    #    default='active')
    party_type = models.CharField(_('party type'), 
        max_length=12, choices=SIZE_CHOICES,
        default='individual')
    description = models.TextField(_('description'), blank=True, null=True)
    is_context = models.BooleanField(_('is context'), default=False)
    objects = AgentTypeManager()

    class Meta:
        ordering = ('name',)

    def __unicode__(self):
        return self.name   
        
    @classmethod
    def create(cls, name, party_type, is_context, verbosity=2):
        """  
        Creates a new AgentType, updates an existing one, or does nothing.
        This is intended to be used as a post_syncdb manangement step.
        """
        try:
            agent_type = cls._default_manager.get(name=name)
            updated = False
            if party_type != agent_type.party_type:
                agent_type.party_type = party_type
                updated = True
            if is_context != agent_type.is_context:
                agent_type.is_context = is_context
                updated = True
            if updated:
                agent_type.save()
                if verbosity > 1:
                    print "Updated %s AgentType" % name
        except cls.DoesNotExist:
            cls(name=name, party_type=party_type, is_context=is_context).save()
            if verbosity > 1:
                print "Created %s AgentType" % name

        
class AgentAccount(object):
    def __init__(self, agent, event_type, count, quantity, events):
        self.agent = agent
        self.event_type = event_type
        self.count = count
        self.quantity = quantity
        self.events=events

    def example(self):
        return self.events[0]
        
        
class AgentManager(models.Manager):

    def without_user(self):
        #import pdb; pdb.set_trace()
        all_agents = EconomicAgent.objects.all()
        ua_ids = []
        for agent in all_agents:
            if agent.users.all():
                ua_ids.append(agent.id)
        return EconomicAgent.objects.exclude(id__in=ua_ids)

    def individuals_without_user(self):
        #import pdb; pdb.set_trace()
        all_agents = self.individuals()
        ua_ids = []
        for agent in all_agents:
            if agent.users.all():
                ua_ids.append(agent.id)
        return all_agents.exclude(id__in=ua_ids)
    
    def projects(self):
        return EconomicAgent.objects.filter(agent_type__party_type="team")
    
    def individuals(self):
        return EconomicAgent.objects.filter(agent_type__party_type="individual")
        
    def organizations(self):
        return EconomicAgent.objects.filter(agent_type__party_type="org")

    def networks(self):
        return EconomicAgent.objects.filter(agent_type__party_type="network")
    
    #def projects_and_networks(self):
    #    return EconomicAgent.objects.filter(Q(agent_type__party_type="network") | Q(agent_type__party_type="team"))
        
    def context_agents(self):
        return EconomicAgent.objects.filter(agent_type__is_context=True)
        
    def non_context_agents(self):
        return EconomicAgent.objects.filter(agent_type__is_context=False)
        
    def resource_role_agents(self):
        return EconomicAgent.objects.filter(Q(agent_type__is_context=True)|Q(agent_type__party_type="individual"))
    
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
        
    @models.permalink
    def get_absolute_url(self):
        return ('agent', (),
        { 'agent_id': str(self.id),})
            
    def seniority(self):
        return (datetime.date.today() - self.created_date).days

    def node_id(self):
        if self.agent_type.party_type == "team":
            return "-".join(["Project", str(self.id)])
        else:
            return "-".join(["Agent", str(self.id)])

    def color(self): #todo: not tested
        if self.agent_type.party_type == "team":
            return "blue"
        else:
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
        
    def active_worked_processes(self):
        aps = [p for p in self.worked_processes() if p.finished==False]
        return aps
        
    def context_processes(self):
        return self.processes.all()
        
    def active_context_processes(self):
        return self.context_processes().filter(finished=False)
        
    def is_individual(self):
        return self.agent_type.party_type == "individual"
        
    def active_processes(self):
        if self.is_individual():
            return self.active_worked_processes()
        else:
            return self.active_context_processes()
            
    def all_processes(self):
        if self.is_individual():
            return self.worked_processes()
        else:
            return self.context_processes()
    
    def resources_created(self):
        creations = []
        for p in self.all_processes():
            creations.extend(p.deliverables())
        return list(set(creations))
        
    def resource_relationships(self):
        return self.agent_resource_roles.all()
    
    #from here these were copied from project - todo: fix these to work correctly using context agent relationships (these are in various stages of fix and test)
    def time_contributions(self):
        return sum(event.quantity for event in self.events.filter(
            is_contribution=True,
            event_type__relationship="work"))
 
    def context_contributions(self):
        return sum(event.quantity for event in self.events.filter(
            is_contribution=True))
        
    def contributions_count(self):
        if self.is_individual():
            return self.contributions().count()
        else:
            return self.contribution_events().count()
        
    def contribution_events(self):
        return self.events.filter(is_contribution=True)
        
    def contributors(self):
        ids = self.events.filter(is_contribution=True).values_list('from_agent').order_by('from_agent').distinct()
        id_list = [id[0] for id in ids]
        return EconomicAgent.objects.filter(id__in=id_list)
        
    def events_by_event_type(self):
        agent_events = EconomicEvent.objects.filter(
            Q(from_agent=self)|Q(to_agent=self))
        ets = EventType.objects.all()
        answer = []
        for et in ets:
            events = agent_events.filter(event_type=et)
            if events:
                count = events.count()
                quantity = sum(e.quantity for e in events)
                aa = AgentAccount(self, et, count, quantity, events)
                answer.append(aa)
        return answer
        
    def sales_and_distributions_count(self):
        return Exchange.objects.sales_and_distributions().filter(context_agent=self).count()
               
    def with_all_sub_agents(self):
        from valuenetwork.valueaccounting.utils import flattened_children_by_association
        return flattened_children_by_association(self, AgentAssociation.objects.all(), [])
        
    def with_all_associations(self):
        from valuenetwork.valueaccounting.utils import group_dfs_by_has_associate, group_dfs_by_is_associate
        if self.is_individual():
            agents = [self,]
            agents.extend([ag.has_associate for ag in self.is_associate_of.all()])
            agents.extend([ag.is_associate for ag in self.has_associates.all()])
        else:     
            associations = AgentAssociation.objects.all().order_by("-association_type")
            associations = associations.exclude(is_associate__agent_type__party_type="individual")
            #associations = associations.exclude(association_type__identifier="supplier")
            gas = group_dfs_by_has_associate(self, self, associations, [], 1)
            gas.extend(group_dfs_by_is_associate(self, self, associations, [], 1))
            agents = [self,]
            for ga in gas:
                if ga not in agents:
                    agents.append(ga)
        return agents
        
    def child_tree(self):
        from valuenetwork.valueaccounting.utils import agent_dfs_by_association
        #todo: figure out why this failed when AAs were ordered by from_agent
        aas = AgentAssociation.objects.all().order_by("id")
        return agent_dfs_by_association(self, aas, 1)
        
    def wip(self):
        return self.active_processes()
        
    def get_resource_types_with_recipe(self):
        rts = [pt.main_produced_resource_type() for pt in ProcessType.objects.filter(context_agent=self) if pt.main_produced_resource_type()]
        #import pdb; pdb.set_trace()
        parents = []
        parent = self.parent()
        while parent:
            parents.append(parent)
            parent = parent.parent()
        for p in parents:
            rts.extend([pt.main_produced_resource_type() for pt in ProcessType.objects.filter(context_agent=p) if pt.main_produced_resource_type()])
        return list(set(rts))
                
    #from here are new methods for context agent code
    def parent(self):
        #assumes only one parent
        #import pdb; pdb.set_trace()
        associations = self.is_associate_of.filter(association_type__identifier="child").filter(state="active")
        parent = None
        if associations.count() > 0:
            parent = associations[0].has_associate
        return parent
        
    def all_ancestors(self):
        parent_ids = []
        parent_ids.append(self.id)
        parent = self.parent()
        while parent:
            parent_ids.append(parent.id)
            parent = parent.parent()
        parents = EconomicAgent.objects.filter(pk__in=parent_ids)
        return parents
                
    def children(self): #returns a list or None
        associations = self.has_associates.filter(association_type__identifier="child").filter(state="active")
        children = None
        if associations.count() > 0:
            children = []
            for association in associations:
                children.append(association.from_agent)
        return children
        
    def is_root(self):
        if self.parent():
            return False
        else:
            return True
            
    def suppliers(self):
        #import pdb; pdb.set_trace()
        agent_ids = self.has_associates.filter(association_type__identifier="supplier").filter(state="active").values_list('is_associate')
        return EconomicAgent.objects.filter(pk__in=agent_ids)
        
    def exchange_firms(self):
        #import pdb; pdb.set_trace()
        agent_ids = self.has_associates.filter(association_type__identifier="legal").filter(state="active").values_list('is_associate')
        return EconomicAgent.objects.filter(pk__in=agent_ids)
        
    def members(self): 
        #import pdb; pdb.set_trace()
        agent_ids = self.has_associates.filter(association_type__identifier="member").filter(state="active").values_list('is_associate')
        return EconomicAgent.objects.filter(pk__in=agent_ids)
        
    def affiliates(self):
        #import pdb; pdb.set_trace()
        agent_ids = self.has_associates.filter(association_type__identifier="affiliate").filter(state="active").values_list('is_associate')
        return EconomicAgent.objects.filter(pk__in=agent_ids)
        
    def customers(self):
        #import pdb; pdb.set_trace()
        agent_ids = self.has_associates.filter(association_type__identifier="customer").filter(state="active").values_list('is_associate')
        return EconomicAgent.objects.filter(pk__in=agent_ids)
        
    def potential_customers(self):
        #import pdb; pdb.set_trace()
        agent_ids = self.has_associates.filter(association_type__identifier="customer").filter(state="potential").values_list('is_associate')
        return EconomicAgent.objects.filter(pk__in=agent_ids)
        
    def all_has_associates_by_type(self, assoc_type_identifier):
        #import pdb; pdb.set_trace()
        agent_ids = self.has_associates.filter(association_type__identifier=assoc_type_identifier).exclude(state="inactive").values_list('is_associate')
        return EconomicAgent.objects.filter(pk__in=agent_ids)
        
    def has_associates_of_type(self, assoc_type_identifier): #returns boolean
        #import pdb; pdb.set_trace()
        if self.all_has_associates_by_type(assoc_type_identifier).count() > 0: #todo: can this be made more efficient, return count from sql?
            return True
        else:
            return False
            
    def associate_count_of_type(self, assoc_type_identifier):
        return self.all_has_associates_by_type(assoc_type_identifier).count()
            
    def agent_association_types(self):
        my_aats = []
        all_aats = AgentAssociationType.objects.all()
        for aat in all_aats:
            if self.has_associates_of_type(aat.identifier):
                my_aats.append(aat)
        return my_aats

    def has_group_associates(self):
        atgs = self.has_associates.exclude(is_associate__agent_type__party_type="individual")
        return atgs
        
    def is_associated_with_groups(self):
        afgs = self.is_associate_of.exclude(has_associate__agent_type__party_type="individual")
        return afgs
        
    def exchange_firm(self):
        xs = self.exchange_firms()
        if xs:
            return xs[0]
        parent = self.parent()
        while parent:
            xs = parent.exchange_firms()
            if xs:
                return xs[0]
            parent = parent.parent()
        return None
        
    def default_agent(self):
        return self.exchange_firm() or self
        
    def all_suppliers(self):
        sups = list(self.suppliers())
        parent = self.parent()
        while parent:
            sups.extend(parent.suppliers())
            parent = parent.parent()
        sup_ids = [sup.id for sup in sups]
        return EconomicAgent.objects.filter(pk__in=sup_ids)
        
    def all_customers(self):
        #import pdb; pdb.set_trace()
        custs = list(self.customers())
        parent = self.parent()
        while parent:
            custs.extend(parent.customers())
            parent = parent.parent()
        cust_ids = [cust.id for cust in custs]
        return EconomicAgent.objects.filter(pk__in=cust_ids)
                
    def all_members(self): 
        mems = self.all_members_list()
        mem_ids = [mem.id for mem in mems]
        return EconomicAgent.objects.filter(pk__in=mem_ids)
        
    def all_members_list(self):
        mems = list(self.members())
        parent = self.parent()
        while parent:
            mems.extend(parent.members())
            parent = parent.parent()
        return mems
        
    def all_ancestors_and_members(self):
        #import pdb; pdb.set_trace()
        agent_list = list(self.all_ancestors())
        agent_list.extend(self.all_members_list())
        agent_ids = [agent.id for agent in agent_list]
        return EconomicAgent.objects.filter(pk__in=agent_ids)
        
    def all_has_associates(self):
        return self.has_associates.all().order_by('association_type__name', 'is_associate__nick')
        
    def all_is_associates(self):
        return self.is_associate_of.all().order_by('association_type__name', 'has_associate__nick')
        
    def all_associations(self):
        return AgentAssociation.objects.filter(
            Q(has_associate=self ) | Q(is_associate=self))
            
        
class AgentUser(models.Model):
    agent = models.ForeignKey(EconomicAgent,
        verbose_name=_('agent'), related_name='users')
    user = models.OneToOneField(User, 
        verbose_name=_('user'), related_name='agent')


class AgentAssociationType(models.Model):
    identifier = models.CharField(_('identifier'), max_length=12, unique=True)
    name = models.CharField(_('name'), max_length=128)
    plural_name = models.CharField(_('plural name'), default="", max_length=128)
    description = models.TextField(_('description'), blank=True, null=True)
    label = models.CharField(_('label'), max_length=32, null=True)
    inverse_label = models.CharField(_('inverse label'), max_length=40, null=True)
    
    def __unicode__(self):
        return self.name
        
    @classmethod
    def create(cls, identifier, name, plural_name, label, inverse_label, verbosity=2):
        """  
        Creates a new AgentType, updates an existing one, or does nothing.
        This is intended to be used as a post_syncdb manangement step.
        """
        try:
            agent_association_type = cls._default_manager.get(identifier=identifier)
            updated = False
            if name != agent_association_type.name:
                agent_association_type.name = name
                updated = True
            if plural_name != agent_association_type.plural_name:
                agent_association_type.plural_name = plural_name
                updated = True
            if label != agent_association_type.label:
                agent_association_type.label = label
                updated = True
            if inverse_label != agent_association_type.inverse_label:
                agent_association_type.inverse_label = inverse_label
                updated = True
            if updated:
                agent_association_type.save()
                if verbosity > 1:
                    print "Updated %s AgentAssociationType" % name
        except cls.DoesNotExist:
            cls(identifier=identifier, name=name, label=label, inverse_label=inverse_label).save()
            if verbosity > 1:
                print "Created %s AgentAssociationType" % name

from south.signals import post_migrate
        
def create_agent_types(app, **kwargs):
    if app != "valueaccounting":
        return
    AgentType.create('Individual', 'individual', False) 
    AgentType.create('Organization', 'org', False) 
    AgentType.create('Network', 'network', True) 
    print "created agent types"
    
post_migrate.connect(create_agent_types) 

def create_agent_association_types(app, **kwargs):
    if app != "valueaccounting":
        return
    AgentAssociationType.create('child', 'Child', 'Children', 'is child of', 'has child') 
    AgentAssociationType.create('member', 'Member', 'Members', 'is member of', 'has member')  
    AgentAssociationType.create('supplier', 'Supplier', 'Suppliers', 'is supplier of', 'has supplier') 
    AgentAssociationType.create('customer', 'Customer', 'Customers', 'is customer of', 'has customer') 
    print "created agent association types"
    
post_migrate.connect(create_agent_association_types)  
        
RELATIONSHIP_STATE_CHOICES = (
    ('active', _('active')),
    ('inactive', _('inactive')),
    ('potential', _('potential')),
)

class AgentAssociation(models.Model):
    #is_associate = models.ForeignKey(EconomicAgent,
    #    verbose_name=_('is associate of'), related_name='associations_from')
    #has_associate = models.ForeignKey(EconomicAgent,
    #    verbose_name=_('has associate'), related_name='associations_to')
    is_associate = models.ForeignKey(EconomicAgent,
        verbose_name=_('is associate of'), related_name='is_associate_of')
    has_associate = models.ForeignKey(EconomicAgent,
        verbose_name=_('has associate'), related_name='has_associates')
    association_type = models.ForeignKey(AgentAssociationType,
        verbose_name=_('association type'), related_name='associations')
    description = models.TextField(_('description'), blank=True, null=True)
    state = models.CharField(_('state'), 
        max_length=12, choices=RELATIONSHIP_STATE_CHOICES,
        default='active')
        
    class Meta:
        ordering = ('is_associate',)
        
    def __unicode__(self):
        return self.is_associate.nick + " " + self.association_type.label + " " + self.has_associate.nick
        

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
    ('receivecash', _('cash receipt')),
    ('shipment', _('shipment')),
    ('distribute', _('distribution')),
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
    ('+~', _('create to change')),
    ('>~', _('to be changed')),
    ('~>', _('change')),
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
        return (self.name,)

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
        
    def is_change_related(self):
        if "~" in self.resource_effect:
            return True
        else:
            return False
            
    def applies_stage(self):
        return self.resource_effect == "+~"
        
    def changes_stage(self):
        return self.resource_effect == "~>"
        
    def stage_to_be_changed(self):
        return self.resource_effect == ">~"
        
    def is_work(self):
        if self.relationship == "work":
            return True
        else:
            return False
        

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

class ResourceState(models.Model):
    name = models.CharField(_('name'), max_length=128, unique=True)
    description = models.TextField(_('description'), blank=True, null=True)
        

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

    def main_producing_process_type_relationship(self, stage=None, state=None):
        #import pdb; pdb.set_trace()
        ptrts = self.producing_process_type_relationships()
        if stage or state:
            ptrts = ptrts.filter(stage=stage, state=state)
        if ptrts:
            one_ptrt = ptrts[0]
            if stage or state:
                return one_ptrt
            else:
                if one_ptrt.stage:
                    stages = self.staged_commitment_type_sequence()
                    if stages:
                        one_ptrt = stages[-1]
                    else:
                        return None
                return one_ptrt
        else:
            return None
            
    def recipe_is_staged(self):
        staged_commitments = self.process_types.filter(stage__isnull=False)
        if staged_commitments:
            return True
        else:
            return False

    def producing_process_types(self):
        return [pt.process_type for pt in self.producing_process_type_relationships()]

    def main_producing_process_type(self, stage=None, state=None):
        ptrt = self.main_producing_process_type_relationship(stage, state)
        if ptrt:
            return ptrt.process_type
        else:
            return None
            
    def all_staged_commitment_types(self):
        return self.process_types.filter(stage__isnull=False)
        
    def all_staged_process_types(self):
        cts = self.all_staged_commitment_types()
        pts = [ct.process_type for ct in cts]
        return list(set(pts))
        
    def staged_commitment_type_sequence(self):
        #import pdb; pdb.set_trace()
        staged_commitments = self.process_types.filter(stage__isnull=False)
        if not staged_commitments:
            return []
        creation_et = EventType.objects.get(name='Create Changeable') 
        chain = []
        creation = None
        try:
            creation = self.process_types.get(
                stage__isnull=False,
                event_type=creation_et)
        except ProcessTypeResourceType.DoesNotExist:
            try:
                creation = self.process_types.get(
                    stage__isnull=True)
            except ProcessTypeResourceType.DoesNotExist:
                pass
        if creation:
            creation.follow_stage_chain(chain)
        return chain
        
    def staged_process_type_sequence(self):
        pts = []
        stages = self.staged_commitment_type_sequence()
        for stage in stages:
            if stage.process_type not in pts:
                pts.append(stage.process_type)
        return pts
        
    def recipe_needs_starting_resource(self):
        if not self.recipe_is_staged():
            return False
        seq = self.staged_commitment_type_sequence()
        ct0 = seq[0]
        if ct0.event_type.name == 'To Be Changed':
            return True
        else:
            return False

    def generate_staged_work_order(self, order_name, start_date, user):
        pts = self.staged_process_type_sequence()
        #import pdb; pdb.set_trace()
        order = Order(
            order_type="rand",
            name=order_name,
            order_date=datetime.date.today(),
            due_date=start_date,
            created_by=user)
        order.save()
        processes = []
        new_start_date = start_date
        for pt in pts:
            p = pt.create_process(new_start_date, user)
            new_start_date = p.end_date
            processes.append(p)
        if processes:
            last_process = processes[-1]
            octs = last_process.outgoing_commitments()
            order_item = None
            for ct in octs:
                ct.order = order
                if not order_name:
                    order_name = " ".join([order_name, ct.resource_type.name])
                    order.name = order_name
                ct.save()
            #import pdb; pdb.set_trace()
            assert octs.count() == 1, 'generate_staged_work_order assumes one and only output'
            order_item = octs[0]
            order.due_date = last_process.end_date
            order.save()
        #flow todo: order_item fields set, but problem may arise
        #if multiple order items exist.
        #None exist now, but may in future.
        #Thus the assert statement above.
        for process in processes:
            for ct in process.commitments.all():
                ct.independent_demand = order
                ct.order_item = order_item
                ct.save()
        return order
        
    def generate_staged_order_item(self, order, start_date, user):
        pts = self.staged_process_type_sequence()
        #import pdb; pdb.set_trace()
        processes = []
        new_start_date = start_date
        for pt in pts:
            p = pt.create_process(new_start_date, user)
            new_start_date = p.end_date
            processes.append(p)
        if processes:
            last_process = processes[-1]
            octs = last_process.outgoing_commitments()
            order_item = None
            for ct in octs:
                ct.order = order
                if not order_name:
                    order_name = " ".join([order_name, ct.resource_type.name])
                    order.name = order_name
                ct.save()
            #import pdb; pdb.set_trace()
            assert octs.count() == 1, 'generate_staged_work_order assumes one and only one output'
            order_item = octs[0]
            #order.due_date = last_process.end_date
            #order.save()
        #flow todo: order_item fields set, but problem may arise
        #if multiple order items exist.
        #None exist now, but may in future.
        #Thus the assert statement above.
        for process in processes:
            for ct in process.commitments.all():
                ct.independent_demand = order
                ct.order_item = order_item
                ct.save()
        return order
    
    def generate_staged_work_order_from_resource(self, resource, order_name, start_date, user):
        pts = self.staged_process_type_sequence()
        #import pdb; pdb.set_trace()
        order = Order(
            order_type="rand",
            name=order_name,
            order_date=datetime.date.today(),
            due_date=start_date,
            created_by=user)
        order.save()
        processes = []
        new_start_date = start_date
        for pt in pts:
            p = pt.create_process(new_start_date, user)
            new_start_date = p.end_date
            processes.append(p)
        if processes:
            last_process = processes[-1]
            octs = last_process.outgoing_commitments()
            order_item = None
            for ct in octs:
                order_qty = ct.quantity
                ct.order = order
                if not order_name:
                    order_name = " ".join([order_name, ct.resource_type.name])
                    order.name = order_name
                ct.save()
            assert octs.count() == 1, 'generate_staged_work_order_from_resource assumes one and only one output'
            order_item = octs[0]
            order.due_date = last_process.end_date
            order.save()
            resource.independent_demand = order
            resource.order_item = order_item
            resource.save()
        for process in processes:
            for commitment in process.commitments.all():
                commitment.independent_demand = order
                commitment.order_item = order_item
                if commitment.resource_type == self:
                    commitment.quantity = resource.quantity
                elif commitment.is_work():
                    if commitment.quantity == order_qty and commitment.unit_of_quantity == self.unit:
                        commitment.quantity = resource.quantity
                commitment.save()

        return order 
    
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
        
    def is_work(self):
        #import pdb; pdb.set_trace()
        #todo: does this still return false positives?
        fvs = self.facets.all()
        for fv in fvs:
            pfvs = fv.facet_value.patterns.filter(
                event_type__related_to="process",
                event_type__relationship="work")
            if pfvs:
                for pf in pfvs:
                    pattern = pf.pattern
                    if self in pattern.work_resource_types():
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
    #flow todo: workflow items will have more than one of these
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
        
    def process_stream_create_form(self):
        from valuenetwork.valueaccounting.forms import RecipeProcessTypeForm
        init = {"name": " ".join(["Make", self.name])}
        return RecipeProcessTypeForm(initial=init, prefix=self.process_create_prefix())
            
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
        
    def recipe_patterns(self):
        #import pdb; pdb.set_trace()
        use_cases = PatternUseCase.objects.filter(use_case__identifier='recipe')
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
        #slots.sort(lambda x, y: cmp(x.label, y.label))
        #slots = sorted(slots, key=attrgetter('label'))
        slots = sorted(slots, key=attrgetter('relationship'), reverse=True)
        return slots

    def slots(self):
        return [et.relationship for et in self.event_types()]
        
    def change_event_types(self):
        return [et for et in self.event_types() if et.is_change_related()]
        
    def non_change_event_type_names(self):
        return [et.name for et in self.event_types() if not et.is_change_related()]

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
        
    def receipt_resource_types_with_resources(self):
        rts = [rt for rt in self.resource_types_for_relationship("receive") if rt.onhand()]
        rt_ids = [rt.id for rt in rts]
        return EconomicResourceType.objects.filter(id__in=rt_ids)

    def expense_resource_types(self):
        #import pdb; pdb.set_trace()
        return self.resource_types_for_relationship("expense")

    def cash_contr_resource_types(self):
        return self.resource_types_for_relationship("cash")
    
    def shipment_resource_types(self):
        return self.resource_types_for_relationship("shipment")
        
    def shipment_resources(self):
        #import pdb; pdb.set_trace()
        rts = self.shipment_resource_types()
        resources = []
        for rt in rts:
            rt_resources = rt.all_resources()
            for res in rt_resources:
                resources.append(res)
        resource_ids = [res.id for res in resources]
        return EconomicResource.objects.filter(id__in=resource_ids)
                
    def material_contr_resource_types(self):
        return self.resource_types_for_relationship("resource")
        
    def cash_receipt_resource_types(self):
        return self.resource_types_for_relationship("receivecash")
            
    def distribution_resource_types(self):
        return self.resource_types_for_relationship("distribute")
        
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
        return (self.identifier,)

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
    UseCase.create('sale', _('Sale'))
    UseCase.create('distribution', _('Distribution'), True)
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
    EventType.create('Shipment', _('ships'), _('shipped by'), 'shipment', 'exchange', '-', 'quantity') 
    EventType.create('Supply', _('supplies'), _('supplied by'), 'out', 'agent', '=', '') 
    EventType.create('Todo', _('todo'), '', 'todo', 'agent', '=', '')
    EventType.create('Resource use', _('uses'), _('used by'), 'use', 'process', '=', 'time') 
    EventType.create('Time Contribution', _('work'), '', 'work', 'process', '=', 'time') 
    EventType.create('Create Changeable', _('creates changeable'), 'changeable created', 'out', 'process', '+~', 'quantity')  
    EventType.create('To Be Changed', _('to be changed'), '', 'in', 'process', '>~', 'quantity')  
    EventType.create('Change', _('changes'), 'changed', 'out', 'process', '~>', 'quantity') 
    EventType.create('Cash Receipt', _('receives cash'), _('cash received by'), 'receivecash', 'exchange', '+', 'value')
    EventType.create('Distribution', _('distributes'), _('distributed by'), 'distribute', 'exchange', '-', 'value')  

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
    UseCaseEventType.create('rand', 'To Be Changed')
    UseCaseEventType.create('rand', 'Change')
    UseCaseEventType.create('rand', 'Create Changeable')
    UseCaseEventType.create('recipe','Citation')
    UseCaseEventType.create('recipe', 'Resource Consumption')
    UseCaseEventType.create('recipe', 'Resource Production')
    UseCaseEventType.create('recipe', 'Resource use')
    UseCaseEventType.create('recipe', 'Time Contribution')
    UseCaseEventType.create('recipe', 'To Be Changed')
    UseCaseEventType.create('recipe', 'Change')
    UseCaseEventType.create('recipe', 'Create Changeable')
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
    UseCaseEventType.create('sale', 'Shipment')
    UseCaseEventType.create('sale', 'Cash Receipt')
    UseCaseEventType.create('sale', 'Time Contribution')
    UseCaseEventType.create('distribution', 'Distribution')
    UseCaseEventType.create('distribution', 'Time Contribution')

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


class OrderManager(models.Manager):
    
    def customer_orders(self):
        return Order.objects.filter(order_type="customer")
        
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

    objects = OrderManager()
    
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
            process_name = " ".join(["to", self.name])
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
        due_label = " due:"
        if provider_name or receiver_name:
            due_label = ", due:"
        return " ".join(
            [self.get_order_type_display(), 
            str(self.id), 
            process_name,
            provider_label, 
            provider_name, 
            receiver_label, 
            receiver_name, 
            due_label,
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
        #todo: why rand, what difference does it make?
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
            stage=None,
            state=None,
            due=None):
        #todo: needs process and project. Anything else? >>context agent
        #might not be worth refactoring out.
        if not due:
            due=self.due_date
        ct = Commitment(
            order=self,
            independent_demand=self,
            event_type=event_type,
            resource_type=resource_type,
            stage=stage,
            state=state,
            quantity=quantity,
            unit_of_quantity=unit,
            due_date=due)
        ct.save()
        ct.order_item = ct
        ct.save()
        #todo: shd this generate_producing_process?
        return ct

    def all_processes(self):
        #import pdb; pdb.set_trace()
        deliverables = self.commitments.filter(event_type__relationship="out")
        if deliverables:
            processes = [d.process for d in deliverables if d.process]
        else:
            processes = []
            commitments = Commitment.objects.filter(independent_demand=self)
            for c in commitments:
                processes.append(c.process)
            processes = list(set(processes))
        roots = []
        for p in processes:
            if not p.next_processes():
                roots.append(p)
        ordered_processes = []
        for root in roots:
            visited = []
            root.all_previous_processes(ordered_processes, visited, 0)
        ordered_processes = list(set(ordered_processes))
        ordered_processes = sorted(ordered_processes, key=attrgetter('end_date'))
        ordered_processes = sorted(ordered_processes, key=attrgetter('start_date'))
        return ordered_processes      
    
    def last_process_in_order(self):
        processes = self.all_processes()
        if processes:
            return processes[-1]
        else:
            return None
    
    def is_workflow_order(self):
        last_process = self.last_process_in_order()
        if last_process:
            return last_process.is_staged()
        else:
            return False
            
    def process_types(self):
        pts = []
        for process in self.all_processes():
            if process.process_type:
                pts.append(process.process_type)
        return pts
            
    def available_workflow_process_types(self):
        all_pts = ProcessType.objects.workflow_process_types()
        my_pts = self.process_types()
        available_pt_ids = []
        for pt in all_pts:
            if pt not in my_pts:
                available_pt_ids.append(pt.id)
        return ProcessType.objects.filter(id__in=available_pt_ids)
        
    def workflow_quantity(self):
        if self.is_workflow_order():
            return self.last_process_in_order().main_outgoing_commitment().quantity
        else:
            return None
        
    def workflow_unit(self):
        if self.is_workflow_order():
            return self.last_process_in_order().main_outgoing_commitment().unit_of_quantity
        else:
            return None  
    
    def change_commitment_quantities(self, qty):
        #import pdb; pdb.set_trace()
        if self.is_workflow_order():
            processes = self.all_processes()
            for process in processes:
                for commitment in process.commitments.all():
                    if commitment.is_change_related():
                        commitment.quantity = qty
                        commitment.save()
                    elif commitment.is_work():
                        if commitment.quantity == self.workflow_quantity() and commitment.unit_of_quantity == self.workflow_unit():
                            commitment.quantity = qty
                            commitment.save()
        return self
        
    def adjust_workflow_commitments_process_added(self, process, user): #process added to the end of the order
        #import pdb; pdb.set_trace()
        last_process = self.last_process_in_order() 
        process.add_stream_commitments(last_process=last_process, user=user)
        last_commitment = last_process.main_outgoing_commitment()
        last_commitment.remove_order()
        return self
        
    def adjust_workflow_commitments_process_inserted(self, process, next_process, user):
        #import pdb; pdb.set_trace()
        all_procs = self.all_processes()
        process_index = all_procs.index(next_process)
        if process_index > 0:
            last_process = all_procs[process_index - 1]
        else:
            last_process = None
        next_commitment = next_process.to_be_changed_requirements()[0]
        if last_process:
            process.insert_stream_commitments(last_process=last_process, user=user)
        else:
            process.insert_first_stream_commitments(next_commitment=next_commitment, user=user)
        next_commitment.update_stage(process.process_type)
        return self
        
    def adjust_workflow_commitments_process_deleted(self, process, user):
        all_procs = self.all_processes()
        process_index = all_procs.index(process)
        last_process = None
        next_commitment = None
        if process_index > 0:
            last_process = all_procs[process_index - 1]
        if process == self.last_process_in_order():
            if last_process:
                last_commitment = last_process.main_outgoing_commitment()
                last_commitment.order = self
                last_commitment.save()
        else:
            next_process = all_procs[process_index + 1]
            next_commitment = next_process.to_be_changed_requirements()[0]
        if last_process and next_commitment:    
            next_commitment.update_stage(last_process.process_type)
        return self
        

class ProcessTypeManager(models.Manager):
    
    def workflow_process_types(self):
        pts = ProcessType.objects.all()
        workflow_pts = []
        for pt in pts:
            if pt.is_workflow_process_type():
                workflow_pts.append(pt)
        return workflow_pts
                
class ProcessType(models.Model):
    name = models.CharField(_('name'), max_length=128)
    parent = models.ForeignKey('self', blank=True, null=True, 
        verbose_name=_('parent'), related_name='sub_process_types', editable=False)
    process_pattern = models.ForeignKey(ProcessPattern,
        blank=True, null=True,
        verbose_name=_('process pattern'), related_name='process_types')
    context_agent = models.ForeignKey(EconomicAgent,
        blank=True, null=True,
        verbose_name=_('context agent'), related_name='process_types')
    description = models.TextField(_('description'), blank=True, null=True)
    url = models.CharField(_('url'), max_length=255, blank=True)
    estimated_duration = models.IntegerField(_('estimated duration'), 
        default=0, help_text=_("in minutes, e.g. 3 hours = 180"))
    created_by = models.ForeignKey(User, verbose_name=_('created by'),
        related_name='process_types_created', blank=True, null=True, editable=False)
    changed_by = models.ForeignKey(User, verbose_name=_('changed by'),
        related_name='process_types_changed', blank=True, null=True, editable=False)
    created_date = models.DateField(auto_now_add=True, blank=True, null=True, editable=False)
    changed_date = models.DateField(auto_now=True, blank=True, null=True, editable=False)
    slug = models.SlugField(_("Page name"), editable=False)
    
    objects = ProcessTypeManager()
    
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
        
    def create_process(self, start_date, user):
        end_date = start_date + datetime.timedelta(minutes=self.estimated_duration)
        process = Process(          
            name=self.name,
            process_type=self,
            process_pattern=self.process_pattern,
            context_agent=self.context_agent,
            url=self.url,
            start_date=start_date,
            end_date=end_date,
        )
        process.save()
        input_ctypes = self.all_input_resource_type_relationships()
        for ic in input_ctypes:
            ic.create_commitment_for_process(process, user)
        output_ctypes = self.produced_resource_type_relationships()
        for oc in output_ctypes:
            oc.create_commitment_for_process(process, user)
        process.name = " ".join([process.name, oc.resource_type.name])
        process.save()
        return process
                            
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
        return self.resource_types.filter(Q(event_type__relationship='consume')|Q(event_type__relationship='use'))
                                                    
    def consumed_resource_type_relationships(self):
        return self.resource_types.filter(event_type__relationship='consume')
                                                        
    def used_resource_type_relationships(self):
        return self.resource_types.filter(event_type__relationship='use')
                                                            
    def cited_resource_type_relationships(self):
        return self.resource_types.filter(event_type__relationship='cite')
                                                                
    def work_resource_type_relationships(self):
        return self.resource_types.filter(event_type__relationship='work')
        
    def to_be_changed_resource_type_relationships(self):
        return self.resource_types.filter(event_type__name='To Be Changed')       
        
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
        
    def all_input_except_change_resource_type_relationships(self):
        return self.resource_types.exclude(event_type__relationship='out').exclude(event_type__relationship='todo').exclude(event_type__name='To Be Changed')
        
    def all_input_resource_types(self):
        return [ptrt.resource_type for ptrt in self.all_input_resource_type_relationships()]
        
    def stream_resource_type_relationships(self):
        return self.resource_types.filter(Q(event_type__name='To Be Changed')|Q(event_type__name='Change')|Q(event_type__name='Create Changeable'))
        
    def input_stream_resource_type_relationship(self):
        return self.resource_types.filter(event_type__name='To Be Changed')
        
    def has_create_changeable_output(self):
        #import pdb; pdb.set_trace()
        if self.produced_resource_type_relationships():
            if self.produced_resource_type_relationships()[0].event_type.name == "Create Changeable":
                return True
            else:
                return False
        else:
            return False
            
    def is_workflow_process_type(self):
        if self.stream_resource_type_relationships():
            return True
        else:
            if self.resource_types.all().exists():
                return False
            else:
                return True
        
    def previous_process_types(self):
        return []
        
    def next_process_types(self):
        return []
                                                                                        
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
    
    def recipe_change_form(self):
        from valuenetwork.valueaccounting.forms import RecipeProcessTypeChangeForm
        return RecipeProcessTypeChangeForm(instance=self, prefix=self.xbill_change_prefix())

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
        #import pdb; pdb.set_trace()
        from valuenetwork.valueaccounting.forms import ProcessTypeCitableForm
        return ProcessTypeCitableForm(process_type=self, prefix=self.xbill_citable_prefix())
     
    def stream_recipe_citable_form(self):
        from valuenetwork.valueaccounting.forms import ProcessTypeCitableStreamRecipeForm
        return ProcessTypeCitableStreamRecipeForm(process_type=self, prefix=self.xbill_citable_prefix())
        
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
        
    def stream_process_type_create_prefix(self):
        return "".join(["PTP", str(self.id)])
            
    def stream_process_type_create_form(self):
        #import pdb; pdb.set_trace()
        from valuenetwork.valueaccounting.forms import RecipeProcessTypeForm
        rt = self.stream_resource_type()
        init = {"name": " ".join(["Make", rt.name])}
        return RecipeProcessTypeForm(initial=init, prefix=self.stream_process_type_create_prefix())
        
    def stream_resource_type(self):
        #import pdb; pdb.set_trace()
        answer = None
        ptrts = self.resource_types.all()
        for ptrt in ptrts:
            if ptrt.is_change_related():
                answer = ptrt.resource_type
        return answer
        
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
        related_name="dependent_resources", verbose_name=_('independent demand'))
    order_item = models.ForeignKey("Commitment",
        blank=True, null=True,
        related_name="stream_resources", verbose_name=_('order item'))
    stage = models.ForeignKey(ProcessType, related_name="resources_at_stage",
        verbose_name=_('stage'), blank=True, null=True)
    state = models.ForeignKey(ResourceState, related_name="resources_at_state",
        verbose_name=_('state'), blank=True, null=True)
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
        rt_name = self.resource_type.name
        if self.stage:
            rt_name = "@".join([rt_name, self.stage.name])
        return ": ".join([
            rt_name,
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
        return self.events.filter(event_type__relationship='out')

    def consuming_events(self):
        return self.events.filter(event_type__relationship='consume')

    def using_events(self):
        return self.events.filter(event_type__relationship="use")

    def all_usage_events(self):
        return self.events.exclude(event_type__relationship="out").exclude(event_type__relationship="receive").exclude(event_type__relationship="resource")

    def demands(self):
        answer = self.resource_type.commitments.exclude(event_type__relationship="out")
        if self.stage:
            answer = answer.filter(stage=self.stage)
        return answer

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
        qty_help = " ".join(["unit:", self.unit_of_quantity.abbrev, ", up to 2 decimal places"])
        return InputEventForm(qty_help=qty_help, prefix=prefix)

    def use_event_form(self, data=None):        
        from valuenetwork.valueaccounting.forms import InputEventForm
        prefix=self.form_prefix()
        unit = self.resource_type.directional_unit("use")
        qty_help = " ".join(["unit:", unit.abbrev, ", up to 2 decimal places"])
        return InputEventForm(qty_help=qty_help, prefix=prefix, data=data)
            
    def input_event_form(self, data=None):
        from valuenetwork.valueaccounting.forms import InputEventForm
        prefix=self.form_prefix()
        qty_help = " ".join(["unit:", self.unit_of_quantity.abbrev, ", up to 2 decimal places"])
        return InputEventForm(qty_help=qty_help, prefix=prefix, data=data)
            
    def owner(self):
        owner_roles = self.agent_resource_roles.filter(role__is_owner=True)
        # todo: this allows one and only one owner
        if owner_roles:
            return owner_roles[0].agent
        return None
             


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
    is_owner = models.BooleanField(_('is owner'), default=False)

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
    owner_percentage = models.IntegerField(_('owner percentage'), null=True)

    def __unicode__(self):
        return " ".join([self.agent.name, self.role.name, self.resource.__unicode__()])
        

#todo: rename to CommitmentType
class ProcessTypeResourceType(models.Model):
    process_type = models.ForeignKey(ProcessType,
        verbose_name=_('process type'), related_name='resource_types')
    resource_type = models.ForeignKey(EconomicResourceType, 
        verbose_name=_('resource type'), related_name='process_types')
    event_type = models.ForeignKey(EventType,
        verbose_name=_('event type'), related_name='process_resource_types')
    stage = models.ForeignKey(ProcessType, related_name="commitmenttypes_at_stage",
        verbose_name=_('stage'), blank=True, null=True)
    state = models.ForeignKey(ResourceState, related_name="commitmenttypes_at_state",
        verbose_name=_('state'), blank=True, null=True)
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
        rt_name = self.resource_type.name
        if self.stage:
            rt_name = "".join([rt_name, "@", self.stage.name])
        return " ".join([self.process_type.name, relname, str(self.quantity), rt_name])        

    def inverse_label(self):
        return self.event_type.inverse_label
        
    def cycle_id(self):
        stage_id = ""
        if self.stage:
            stage_id = str(self.stage.id)
        state_id = ""
        if self.state:
            state_id = str(self.state.id)
        return "-".join([str(self.resource_type.id), stage_id, state_id])
       
    def is_change_related(self):
        return self.event_type.is_change_related()
        
    def follow_stage_chain(self, chain):
        if self.event_type.is_change_related():
            chain.append(self)
            if self.event_type.relationship == "out":
                next_in_chain = ProcessTypeResourceType.objects.filter(
                    resource_type=self.resource_type,
                    stage=self.stage,
                    event_type__resource_effect=">~")
            if self.event_type.relationship == "in":
                next_in_chain = ProcessTypeResourceType.objects.filter(
                    resource_type=self.resource_type,
                    stage=self.process_type,
                    event_type__resource_effect="~>")
            if next_in_chain:
                next_in_chain[0].follow_stage_chain(chain)
                    
    def create_commitment_for_process(self, process, user):
        if self.event_type.relationship == "out":
            due_date = process.end_date
        else:
            due_date = process.start_date
        unit = self.resource_type.directional_unit(self.event_type.relationship)
        commitment = Commitment(
            process=process,
            stage=self.stage,
            state=self.state,
            context_agent=process.context_agent,
            event_type=self.event_type,
            resource_type=self.resource_type,
            quantity=self.quantity,
            unit_of_quantity=unit,
            due_date=due_date,
            #from_agent=from_agent,
            #to_agent=to_agent,
            created_by=user)
        commitment.save()
        return commitment
        
    def create_commitment(self, due_date, user):
        commitment = Commitment(
            stage=self.stage,
            state=self.state,
            context_agent=self.process_type.context_agent,
            event_type=self.event_type,
            resource_type=self.resource_type,
            quantity=self.quantity,
            unit_of_quantity=self.resource_type.unit,
            due_date=due_date,
            #from_agent=from_agent,
            #to_agent=to_agent,
            created_by=user)
        commitment.save()
        return commitment
        
    def stream_label(self):
        relname = ""
        if self.event_type:
            relname = self.event_type.label
        rt_name = self.resource_type.name
        if self.stage:
            rt_name = "".join([rt_name, "@", self.stage.name])
        abbrev = ""
        if self.unit_of_quantity:
            abbrev = self.unit_of_quantity.abbrev
        return " ".join([relname, str(self.quantity), abbrev, rt_name]) 
                        
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
        #todo: where is this used? Did I break it with this change?
        #(adding stage and state)
        answer = "-".join(["ProcessResource", str(self.id)])
        if self.stage:
            answer = "-".join([answer, str(self.stage.id)])
        if self.state:
            answer = "-".join([answer, self.state.name])
        return answer

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
    context_agent = models.ForeignKey(EconomicAgent,
        blank=True, null=True,
        verbose_name=_('context agent'), related_name='processes')
    url = models.CharField(_('url'), max_length=255, blank=True)
    start_date = models.DateField(_('start date'))
    end_date = models.DateField(_('end date'), blank=True, null=True)
    started = models.DateField(_('started'), blank=True, null=True)
    finished = models.BooleanField(_('finished'), default=False)
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
                order_name = " ".join(["to", order_name])
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
    
    def class_label(self):
        return "Process"
    
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

    def default_agent(self):
        if self.context_agent:
            return self.context_agent.exchange_firm() or self.context_agent
        return None
        
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

    def order_item(self):
        moc = self.main_outgoing_commitment()
        if moc:
            return moc.order_item
        else:
            ics = self.incoming_commitments()
            if ics:
                return ics[0].order_item
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
        if self.commitments.exclude(event_type__relationship='work'):
            answer = False
        if self.events.all():
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
            
    def has_events(self):
        #import pdb; pdb.set_trace()
        if self.events.count() > 0:
            return True
        else:
            return False

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
            dmnd = moc.order_item
        #output_rts = [oc.resource_type for oc in self.outgoing_commitments()]
        for ic in self.incoming_commitments():
            rt = ic.resource_type
            stage = ic.stage
            state = ic.state
            # this is maybe a better way to block cycles
            for pc in rt.producing_commitments():
                if pc.process != self:
                    if pc.stage == stage and pc.state == state:
                        if dmnd:
                            if pc.order_item == dmnd:
                                answer.append(pc.process)
                        else:
                            if not pc.order_item:
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

    def all_previous_processes(self, ordered_processes, visited, depth):
        #import pdb; pdb.set_trace()
        self.depth = depth * 2
        ordered_processes.append(self)
        output = self.main_outgoing_commitment()
        if not output:
            return []
        depth = depth + 1
        if output.cycle_id() not in visited:
            visited.append(output.cycle_id())
            for process in self.previous_processes():
                process.all_previous_processes(ordered_processes, visited, depth)

    def next_processes(self):
        answer = []
        #import pdb; pdb.set_trace()
        input_ids = [ic.cycle_id() for ic in self.incoming_commitments()]
        for oc in self.outgoing_commitments():
            dmnd = oc.order_item
            stage = oc.stage
            state = oc.state
            rt = oc.resource_type
            if oc.cycle_id() not in input_ids:
                for cc in rt.wanting_commitments():
                    if cc.stage == stage and cc.state == state:
                        if dmnd:
                            if cc.order_item == dmnd:
                                if cc.process not in answer:
                                    answer.append(cc.process)
                        else:
                            if not cc.order_item:
                                if cc.quantity >= oc.quantity:
                                    compare_date = self.end_date
                                    if not compare_date:
                                        compare_date = self.start_date
                                    if cc.due_date >= compare_date:
                                        if cc.process not in answer:
                                            answer.append(cc.process)
        for oe in self.uncommitted_production_events():
            rt = oe.resource_type
            if oe.cycle_id() not in input_ids:
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
        
    def create_changeable_requirements(self):
        return self.commitments.filter(
        event_type__name="Create Changeable")        
        
    def to_be_changed_requirements(self):
        return self.commitments.filter(
            event_type__name="To Be Changed")
        
    def changeable_requirements(self):
        return self.commitments.filter(
            event_type__name="Change")
            
    def paired_change_requirements(self):
        return self.to_be_changed_requirements(), self.changeable_requirements()
        
    def is_staged(self):
        if self.create_changeable_requirements() or self.changeable_requirements():
            return True
        else:
            return False

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
            order_item=None,
            stage=None,
            state=None,
            from_agent=None,
            to_agent=None,
            order=None,
            ):
        ct = Commitment(
            independent_demand=demand,
            order=order,
            order_item=order_item,
            process=self,
            context_agent=self.context_agent,
            event_type=event_type,
            resource_type=resource_type,
            stage=stage,
            state=state,
            quantity=quantity,
            unit_of_quantity=unit,
            due_date=self.start_date, #ask bob: why is this? in vs out commitments?
            from_agent=from_agent,
            to_agent=to_agent,
            created_by=user)
        ct.save()
        return ct
        
    def add_stream_commitments(self, last_process, user): #for adding to the end of the order
        last_commitment = last_process.main_outgoing_commitment()
        ets = self.process_pattern.change_event_types()
        for et in ets:
            if et.relationship == "out":
                stage = self.process_type
                order = last_commitment.independent_demand
            else:
                stage = last_process.process_type
                order = None
            ct = self.add_commitment(
                resource_type=last_commitment.resource_type, 
                demand=last_commitment.independent_demand,
                order_item=last_commitment.order_item,
                order=order,
                quantity=last_commitment.quantity, 
                event_type=et,
                unit=last_commitment.unit_of_quantity, 
                user=user,
                stage=stage,
            )
            
    def insert_stream_commitments(self, last_process, user): #for inserting in order (not first and not last process in order)
        last_commitment = last_process.main_outgoing_commitment()
        ets = self.process_pattern.change_event_types()
        for et in ets:
            if et.relationship == "out":
                stage = self.process_type
            else:
                stage = last_process.process_type
            ct = self.add_commitment(
                resource_type=last_commitment.resource_type, 
                demand=last_commitment.independent_demand,
                order_item=last_commitment.order_item,
                quantity=last_commitment.quantity, 
                event_type=et,
                unit=last_commitment.unit_of_quantity, 
                user=user,
                stage=stage,
            )
            
    def insert_first_stream_commitments(self, next_commitment, user): #for inserting as first process in order
        ets = self.process_pattern.change_event_types()
        for et in ets:
            if et.relationship == "out":
                stage = self.process_type
            else:
                stage = None
            ct = self.add_commitment(
                resource_type=next_commitment.resource_type, 
                demand=next_commitment.independent_demand,
                order_item=next_commitment.order_item,
                quantity=next_commitment.quantity, 
                event_type=et,
                unit=next_commitment.unit_of_quantity, 
                user=user,
                stage=stage,
            )

    def explode_demands(self, demand, user, visited):
        """This method assumes the output commitment from this process 

            has already been created.

        """
        #import pdb; pdb.set_trace()
        pt = self.process_type
        output = self.main_outgoing_commitment()
        order_item = output.order_item
        #if not output:
            #import pdb; pdb.set_trace()
        visited_id = output.cycle_id()
        if visited_id not in visited:
            visited.append(visited_id)
        for ptrt in pt.all_input_resource_type_relationships():
            #import pdb; pdb.set_trace()
            if output.stage:
                #if output.resource_type == ptrt.resource_type:
                qty = output.quantity
            else:
                qty = output.quantity * ptrt.quantity
            commitment = self.add_commitment(
                resource_type=ptrt.resource_type,
                demand=demand,
                order_item=order_item,
                stage=ptrt.stage,
                state=ptrt.state,
                quantity=qty,
                event_type=ptrt.event_type,
                unit=ptrt.resource_type.directional_unit(ptrt.event_type.relationship),
                user=user,
            )
            #cycles broken here
            #flow todo: consider order_item for non-substitutables?
            # seemed to work without doing that...?
            #import pdb; pdb.set_trace()
            visited_id = ptrt.cycle_id()
            if visited_id not in visited:
                visited.append(visited_id)
                qty_to_explode = commitment.net()
                if qty_to_explode:
                    #todo: shd commitment.generate_producing_process?
                    #no, this an input commitment
                    #shd pt create process?
                    #shd pptr create next_commitment, and then 
                    #shd next_commitment.generate_producing_process?
                    #import pdb; pdb.set_trace()
                    pptr = ptrt.resource_type.main_producing_process_type_relationship(
                        stage=commitment.stage,
                        state=commitment.state)
                    if pptr:
                        next_pt = pptr.process_type
                        start_date = self.start_date - datetime.timedelta(minutes=next_pt.estimated_duration)
                        next_process = Process(          
                            name=next_pt.name,
                            process_type=next_pt,
                            process_pattern=next_pt.process_pattern,
                            #project=next_pt.project,
                            context_agent=next_pt.context_agent,
                            url=next_pt.url,
                            end_date=self.start_date,
                            start_date=start_date,
                        )
                        next_process.save()
                        #this is the output commitment
                        #import pdb; pdb.set_trace()
                        if output.stage:
                            qty = output.quantity
                        else:
                            qty = qty_to_explode * pptr.quantity
                        #print "is this an output commitment?", pptr.resource_type, pptr.event_type.relationship
                        next_commitment = next_process.add_commitment(
                            resource_type=pptr.resource_type,
                            stage=pptr.stage,
                            state=pptr.state,
                            demand=demand,
                            order_item=order_item,
                            quantity=qty,
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
        
    def plan_form_prefix(self):
        return "-".join(["PCF", str(self.id)])

    def schedule_form(self):
        from valuenetwork.valueaccounting.forms import ScheduleProcessForm
        init = {"start_date": self.start_date, "end_date": self.end_date, "notes": self.notes}
        return ScheduleProcessForm(prefix=str(self.id),initial=init)
        
    def plan_change_form(self):
        from valuenetwork.valueaccounting.forms import PlanProcessForm
        init = {"start_date": self.start_date, "end_date": self.end_date, "name": self.name}
        return PlanProcessForm(prefix=self.plan_form_prefix(),initial=init)      
        
    def insert_process_form(self):
        #import pdb; pdb.set_trace()
        from valuenetwork.valueaccounting.forms import WorkflowProcessForm
        init = {"start_date": self.start_date, "end_date": self.start_date}
        return WorkflowProcessForm(prefix=str(self.id),initial=init, order=self.independent_demand())      
        

class ExchangeManager(models.Manager):

    def financial_contributions(self):
        return Exchange.objects.filter(
            Q(use_case__identifier="cash_contr")|
            Q(use_case__identifier="purch_contr")|
            Q(use_case__identifier="exp_contr"))
        
    def sales_and_distributions(self):
        return Exchange.objects.filter(
            Q(use_case__identifier="sale")|
            Q(use_case__identifier="distribution"))

class Exchange(models.Model):
    name = models.CharField(_('name'), blank=True, max_length=128)
    process_pattern = models.ForeignKey(ProcessPattern,
        blank=True, null=True,
        verbose_name=_('pattern'), related_name='exchanges')
    use_case = models.ForeignKey(UseCase,
        blank=True, null=True,
        verbose_name=_('use case'), related_name='exchanges')
    context_agent = models.ForeignKey(EconomicAgent,
        blank=True, null=True,
        verbose_name=_('context agent'), related_name='exchanges')
    url = models.CharField(_('url'), max_length=255, blank=True, null=True)
    start_date = models.DateField(_('start date'))
    notes = models.TextField(_('notes'), blank=True)
    supplier = models.ForeignKey(EconomicAgent,
        blank=True, null=True,
        related_name="exchanges_as_supplier", verbose_name=_('supplier'))
    customer = models.ForeignKey(EconomicAgent,
        blank=True, null=True,
        related_name="exchanges_as_customer", verbose_name=_('customer'))
    order = models.ForeignKey(Order,
        blank=True, null=True,
        related_name="cash_receipts", verbose_name=_('order'))
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
    
    def cash_receipt_events(self):
        return self.events.filter(
            event_type__relationship='receivecash')
            
    def shipment_events(self):
        return self.events.filter(
            event_type__relationship='shipment')

    def distribution_events(self):
        return self.events.filter(
            event_type__relationship='distribute')
            
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
        related_name="dependent_commitments", verbose_name=_('independent demand'))
    order_item = models.ForeignKey("self",
        blank=True, null=True,
        related_name="stream_commitments", verbose_name=_('order item'))
    event_type = models.ForeignKey(EventType, 
        related_name="commitments", verbose_name=_('event type'))
    stage = models.ForeignKey(ProcessType, related_name="commitments_at_stage",
        verbose_name=_('stage'), blank=True, null=True)
    state = models.ForeignKey(ResourceState, related_name="commitments_at_state",
        verbose_name=_('state'), blank=True, null=True)
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
    context_agent = models.ForeignKey(EconomicAgent,
        blank=True, null=True,
        verbose_name=_('context agent'), related_name='commitments')
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
        
    def class_label(self):
        return " ".join(["Commitment for", self.label()])
        
    def cycle_id(self):
        stage_id = ""
        if self.stage:
            stage_id = str(self.stage.id)
        state_id = ""
        if self.state:
            state_id = str(self.state.id)
        return "-".join([str(self.resource_type.id), stage_id, state_id])
        
    def resource_type_node_id(self):
        answer = "-".join(["ProcessResource", self.cycle_id()])
        return answer

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
    
    def can_add_to_resource(self):
        if self.resource_type.substitutable:
            if not self.stage:
                return True
        return False

    def addable_resources(self):
        if self.can_add_to_resource():
            if self.onhand():
                return True
        return False
        
    def resource_create_form(self, data=None):
        from valuenetwork.valueaccounting.forms import EconomicResourceForm
        init = {
            "quantity": self.quantity,
            "unit_of_quantity": self.resource_type.unit,
        }
        return EconomicResourceForm(prefix=self.form_prefix(), initial=init, data=data)
        
    def select_resource_form(self, data=None):
        from valuenetwork.valueaccounting.forms import SelectResourceForm
        init = {
            "quantity": self.quantity,
            #"unit_of_quantity": self.resource_type.unit,
        }
        return SelectResourceForm(prefix=self.form_prefix(), resource_type=self.resource_type, initial=init, data=data)

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

    #obsolete
    def work_event_form(self, data=None):   
        from valuenetwork.valueaccounting.forms import TimeEventForm, InputEventForm
        prefix=self.form_prefix()
        unit = self.resource_type.unit
        if unit.unit_type == "time":
            return TimeEventForm(prefix=prefix, data=data)
        else:
            qty_help = " ".join(["unit:", unit.abbrev, ", up to 2 decimal places"])
            return InputEventForm(qty_help=qty_help, prefix=prefix, data=data)
            
    def input_event_form(self, data=None):
        from valuenetwork.valueaccounting.forms import InputEventForm
        prefix=self.form_prefix()
        qty_help = " ".join(["unit:", self.unit_of_quantity.abbrev, ", up to 2 decimal places"])
        return InputEventForm(qty_help=qty_help, prefix=prefix, data=data)

    def consumption_event_form(self):        
        from valuenetwork.valueaccounting.forms import InputEventForm
        prefix=self.form_prefix()
        qty_help = " ".join(["unit:", self.unit_of_quantity.abbrev, ", up to 2 decimal places"])
        return InputEventForm(qty_help=qty_help, prefix=prefix)

    def old_use_event_form(self):        
        from valuenetwork.valueaccounting.forms import TimeEventForm, InputEventForm
        prefix=self.form_prefix()
        unit = self.resource_type.directional_unit("use")
        if unit.unit_type == "time":
            return TimeEventForm(prefix=prefix)
        else:
            qty_help = " ".join(["unit:", unit.abbrev, ", up to 2 decimal places"])
            return InputEventForm(qty_help=qty_help, prefix=prefix)
            
    def use_event_form(self, data=None):        
        from valuenetwork.valueaccounting.forms import InputEventForm
        prefix=self.form_prefix()
        unit = self.resource_type.directional_unit("use")
        qty_help = " ".join(["unit:", unit.abbrev, ", up to 2 decimal places"])
        return InputEventForm(qty_help=qty_help, prefix=prefix, data=data)
            
    def resource_ready_to_be_changed(self):
        resource = None
        if self.event_type.stage_to_be_changed():
            if not self.resource_type.substitutable:
                resource = EconomicResource.objects.filter(
                    resource_type=self.resource_type,
                    stage=self.stage,
                    order_item=self.order_item)
                if resource:
                    resource = resource[0]
        return resource
        
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

    def delete_dependants(self):
        trash = []
        if self.event_type.relationship == "out":
            collect_trash(self, trash)
        else:
            collect_lower_trash(self, trash)
        for proc in trash:
            if proc.outgoing_commitments().count() <= 1:
                proc.delete()
            
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
        rt = self.resource_type
        resources = EconomicResource.goods.filter(resource_type=self.resource_type)
        if not rt.substitutable:
            resources = resources.filter(order_item=self.order_item)
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
        #if rt.id == 68:
        #    import pdb; pdb.set_trace()
        if not rt.substitutable:
            #todo: or, get resources where r.order_item == self.order_item
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
            ptrt = rt.main_producing_process_type_relationship(stage=self.stage, state=self.state)
            if ptrt:
                pt = ptrt.process_type
                start_date = self.due_date - datetime.timedelta(minutes=pt.estimated_duration)
                process = Process(
                    name=pt.name,
                    process_type=pt,
                    process_pattern=pt.process_pattern,
                    #project=pt.project,
                    context_agent=pt.context_agent,
                    url=pt.url,
                    end_date=self.due_date,
                    start_date=start_date,
                    created_by=user,
                )
                process.save()
                self.process=process
                self.save()
                if explode:
                    demand = self.independent_demand
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
        if self.stage:
            wanters = wanters.filter(stage=self.stage)
        return [ct for ct in wanters if ct.order_item == self.order_item]

    def associated_producing_commitments(self):
        producers = self.resource_type.producing_commitments().exclude(id=self.id)
        return [ct for ct in producers if ct.order_item == self.order_item]

    def scheduled_receipts(self):
        rt = self.resource_type
        if rt.substitutable:
            return rt.active_producing_commitments()
        else:
            return self.associated_producing_commitments()
            
    def is_change_related(self):
        return self.event_type.is_change_related()
        
    def is_work(self):
        return self.event_type.is_work()
        
    def remove_order(self):
        self.order = None
        self.save()
        
    def update_stage(self, process_type):
        self.stage = process_type
        self.save()
        
    def process_chain(self):
        #import pdb; pdb.set_trace()
        processes = []
        self.process.all_previous_processes(processes, [], 0)
        return processes
        
    def find_order_item(self):
        #this is a temporary method for data migration after the flows branch is deployed
        answer = None
        if self.independent_demand:
            ois = self.independent_demand.order_items()
            if ois:
                if ois.count() == 1:
                    return ois[0]
                else:
                    return ois
    
    
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
    context_agent = models.ForeignKey(EconomicAgent,
        blank=True, null=True,
        related_name="events", verbose_name=_('context agent'),
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
        if self.recipient():
            to_agt = self.recipient().name
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
        #project = self.project
        context_agent = self.context_agent
        resource_type = self.resource_type
        event_type = self.event_type
        delta = self.quantity
        agent_change = False
        project_change = False
        resource_type_change = False
        context_agent_change = False
        event_type_change = False
        if self.pk:
            prev_agent = self.from_agent
            #prev_project = self.project
            prev_context_agent = self.context_agent
            prev_resource_type = self.resource_type
            prev_event_type = self.event_type
            prev = EconomicEvent.objects.get(pk=self.pk)
            if prev.quantity != self.quantity:
                delta = self.quantity - prev.quantity
            if prev.from_agent != self.from_agent:
                agent_change = True
                prev_agent = prev.from_agent
            #if prev.project != self.project:
            #    project_change = True
            #    prev_project = prev.project 
            if prev.context_agent != self.context_agent:
                context_agent_change = True
                prev_context_agent = prev.context_agent 
            if prev.resource_type != self.resource_type:
                resource_type_change = True
                prev_resource_type = prev.resource_type
            if prev.event_type != self.event_type:
                event_type_change = True
                prev_event_type = prev.event_type
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
        update_summary(agent, context_agent, resource_type, event_type)
        if agent_change or resource_type_change or context_agent_change or event_type_change:
            update_summary(prev_agent, prev_context_agent, prev_resource_type, prev_event_type)

    def delete(self, *args, **kwargs):
        if self.event_type.relationship == "work":
            if self.is_contribution:
                agent = self.from_agent
                #project = self.project
                context_agent = self.context_agent
                resource_type = self.resource_type
                event_type = self.event_type
                if agent and context_agent and resource_type:
                    try:
                        summary = CachedEventSummary.objects.get(
                            agent=agent,
                            context_agent=context_agent,
                            resource_type=resource_type,
                            event_type=event_type)
                        summary.quantity -= self.quantity
                        if summary.quantity:
                            summary.save() 
                        else:
                            summary.delete()
                    except CachedEventSummary.DoesNotExist:
                        pass
        super(EconomicEvent, self).delete(*args, **kwargs)
        
    def default_agent(self):
        if self.context_agent:
            return self.context_agent.exchange_firm() or self.context_agent
        return None 
        
    def cycle_id(self):
        stage_id = ""
        if self.resource.stage:
            stage_id = str(self.resource.stage.id)
        state_id = ""
        if self.resource.state:
            state_id = str(self.resource.state.id)
        return "-".join([str(self.resource_type.id), stage_id, state_id])
        
    def class_label(self):
        return "Economic Event"
        
    def recipient(self):
        return self.to_agent or self.default_agent()

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
            return self.resource_type.unit.abbrev

    def quantity_formatted(self):
        return " ".join([
            str(self.quantity.quantize(Decimal('.01'), rounding=ROUND_UP)),
            self.unit(),
            ])
            
    def form_prefix(self):
        return "-".join(["EVT", str(self.id)])

    def work_event_change_form(self):
        from valuenetwork.valueaccounting.forms import WorkEventChangeForm
        return WorkEventChangeForm(instance=self)
        
    def change_form(self, data=None):
        #import pdb; pdb.set_trace()
        from valuenetwork.valueaccounting.forms import TimeEventForm, InputEventForm
        unit = self.resource_type.unit
        prefix = self.form_prefix()
        if unit.unit_type == "time":
            return TimeEventForm(instance=self, prefix=prefix, data=data)
        else:
            qty_help = " ".join(["unit:", unit.abbrev, ", up to 2 decimal places"])
            return InputEventForm(qty_help=qty_help, instance=self, prefix=prefix, data=data)

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
    def __init__(self, agent, context_agent, resource_type, event_type, quantity, value=Decimal('0.0')):
        self.agent = agent
        self.context_agent = context_agent
        self.resource_type = resource_type
        self.event_type = event_type
        self.quantity = quantity
        self.value=value

    def key(self):
        return "-".join([
            str(self.agent.id), 
            str(self.resource_type.id),
            str(self.project.id),
            str(self.event_type.id),
            ])

    def quantity_formatted(self):
        return self.quantity.quantize(Decimal('.01'), rounding=ROUND_UP)



class CachedEventSummary(models.Model):
    agent = models.ForeignKey(EconomicAgent,
        blank=True, null=True,
        related_name="cached_events", verbose_name=_('agent'))
    #project = models.ForeignKey(Project,
    #    blank=True, null=True,
    #    verbose_name=_('project'), related_name='cached_events')
    context_agent = models.ForeignKey(EconomicAgent,
        blank=True, null=True,
        verbose_name=_('context agent'), related_name='context_cached_events')
    resource_type = models.ForeignKey(EconomicResourceType,
        blank=True, null=True,
        verbose_name=_('resource type'), related_name='cached_events')
    event_type = models.ForeignKey(EventType,
        verbose_name=_('event type'), related_name='cached_events')
    resource_type_rate = models.DecimalField(_('resource type rate'), max_digits=8, decimal_places=2, default=Decimal("1.0"))
    importance = models.DecimalField(_('importance'), max_digits=3, decimal_places=0, default=Decimal("1"))
    reputation = models.DecimalField(_('reputation'), max_digits=8, decimal_places=2, 
        default=Decimal("1.00"))
    quantity = models.DecimalField(_('quantity'), max_digits=8, decimal_places=2, 
        default=Decimal("0.0"))
    value = models.DecimalField(_('value'), max_digits=8, decimal_places=2, 
        default=Decimal("0.0"))

    class Meta:
        ordering = ('agent', 'context_agent', 'resource_type')

    def __unicode__(self):
        agent_name = "Unknown"
        if self.agent:
            agent_name = self.agent.name
        #project_name = "Unknown"
        #if self.project:
        #    project_name = self.project.name
        context_agent_name = "Unknown"
        if self.context_agent:
            context_agent_name = self.context_agent.name
        resource_type_name = "Unknown"
        if self.resource_type:
            resource_type_name = self.resource_type.name
        return ' '.join([
            'Agent:',
            agent_name,
            'Context:',
            context_agent_name,
            'Resource Type:',
            resource_type_name,
        ])

    @classmethod
    def summarize_events(cls, context_agent):
        #import pdb; pdb.set_trace()
        #todo: this code is obsolete, we don't want to roll up sub-projects anymore
        all_subs = context_agent.with_all_sub_agents()
        event_list = EconomicEvent.objects.filter(context_agent__in=all_subs)
        summaries = {}
        for event in event_list:
            key = "-".join([str(event.from_agent.id), str(event.context_agent.id), str(event.resource_type.id)])
            if not key in summaries:
                summaries[key] = EventSummary(event.from_agent, event.context_agent, event.resource_type, Decimal('0.0'))
            summaries[key].quantity += event.quantity
        summaries = summaries.values()
        for summary in summaries:
            ces = cls(
                agent=summary.agent,
                context_agent=summary.context_agent,
                resource_type=summary.resource_type,
                resource_type_rate=summary.resource_type.rate,
                #importance=summary.project.importance, todo: need this in agent?
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
        context_agent = EconomicAgent.objects.get(name="Not defined")
        for event in event_list:
            #todo: very temporary hack
            if not event.context_agent:
                event.context_agent=context_agent
                event.save()
            try:
                key = "-".join([str(event.from_agent.id), str(event.context_agent.id), str(event.resource_type.id), str(event.event_type.id)])
                if not key in summaries:
                    summaries[key] = EventSummary(event.from_agent, event.context_agent, event.resource_type, event.event_type, Decimal('0.0'))
                key = "-".join([
                    str(event.from_agent.id), 
                    str(event.project.id), 
                    str(event.resource_type.id), 
                    str(event.event_type.id)])
                if not key in summaries:
                    summaries[key] = EventSummary(
                        agent=event.from_agent, 
                        #project=event.project, 
                        resource_type=event.resource_type, 
                        event_type=event.event_type,
                        quantity=Decimal('0.0'))
                summaries[key].quantity += event.quantity
            except AttributeError:
                #todo: the event errors shd be fixed
                import pdb; pdb.set_trace()
        summaries = summaries.values()
        for summary in summaries:
            ces = cls(
                agent=summary.agent,
                context_agent=summary.context_agent,
                resource_type=summary.resource_type,
                event_type=summary.event_type,
                resource_type_rate=summary.resource_type.rate,
                #importance=summary.project.importance,
                quantity=summary.quantity,
            )
            ces.save()
        return cls.objects.all()


    def quantity_formatted(self):
        return self.quantity.quantize(Decimal('.01'), rounding=ROUND_UP)

    def value_formatted(self):
        return self.value.quantize(Decimal('.01'), rounding=ROUND_UP)
        
    def quantity_label(self):
        #return " ".join([self.resource_type.name, self.resource_type.unit.abbrev])
        return self.resource_type.name


