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
    ('percent', _('percent')),
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
    phone_primary = models.CharField(_('primary phone'), max_length=32, blank=True, null=True)
    phone_secondary = models.CharField(_('secondary phone'), max_length=32, blank=True, null=True)
    latitude = models.FloatField(_('latitude'), default=0.0, blank=True, null=True)
    longitude = models.FloatField(_('longitude'), default=0.0, blank=True, null=True)
    reputation = models.DecimalField(_('reputation'), max_digits=8, decimal_places=2, 
        default=Decimal("0.00"))
    photo = ThumbnailerImageField(_("photo"),
        upload_to='photos', blank=True, null=True)
    photo_url = models.CharField(_('photo url'), max_length=255, blank=True)
    unit_of_claim_value = models.ForeignKey(Unit, blank=True, null=True,
        verbose_name=_('unit used in claims'), related_name="agents",
        help_text=_('For a context agent, the unit of all claims'))    
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
            
    def username(self):
        agent_user = self.user()
        if agent_user:
            return agent_user.user.username
        else:
            return ""

    def worked_processes(self):
        cts = self.given_commitments.all()
        events = self.given_events.all()
        processes = [x.process for x in cts if x.process]
        processes.extend([x.process for x in events if x.process])
        return list(set(processes))
        
    def active_worked_processes(self):
        aps = [p for p in self.worked_processes() if p.finished==False]
        return aps
        
    def finished_worked_processes(self):
        aps = [p for p in self.worked_processes() if p.finished==True]
        return aps
        
    def context_processes(self):
        return self.processes.all()
        
    def active_context_processes(self):
        return self.context_processes().filter(finished=False)
        
    def finished_context_processes(self):
        return self.context_processes().filter(finished=True)
        
    def is_individual(self):
        return self.agent_type.party_type == "individual"
        
    def active_processes(self):
        if self.is_individual():
            return self.active_worked_processes()
        else:
            return self.active_context_processes()
            
    def finished_processes(self):
        if self.is_individual():
            return self.finished_worked_processes()
        else:
            return self.finished_context_processes()
            
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
        aas = AgentAssociation.objects.filter(association_type__association_behavior="child").order_by("is_associate__name")
        return flattened_children_by_association(self, aas, [])
        
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
        aas = AgentAssociation.objects.filter(association_type__association_behavior="child").order_by("is_associate__name")
        return agent_dfs_by_association(self, aas, 1)
        
    def wip(self):
        return self.active_processes()
        
    def process_types_queryset(self):
        pts = list(ProcessType.objects.filter(context_agent=self))
        parent = self.parent()
        while parent:
            pts.extend(ProcessType.objects.filter(context_agent=parent))
            parent = parent.parent()
        pt_ids = [pt.id for pt in pts]
        return ProcessType.objects.filter(id__in=pt_ids)
        
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
        parent_rts = rts
        for rt in parent_rts:
            rts.extend(rt.all_children())
            
        return list(set(rts))
        
    def get_resource_type_lists(self):
        rt_lists = list(self.lists.all())
        #import pdb; pdb.set_trace()
        parents = []
        parent = self.parent()
        while parent:
            parents.append(parent)
            parent = parent.parent()
        for p in parents:
            rt_lists.extend(list(p.lists.all()))
        rt_lists = list(set(rt_lists))
        rt_lists.sort(lambda x, y: cmp(x.name, y.name))
        return rt_lists
                
    #from here are new methods for context agent code
    def parent(self):
        #assumes only one parent
        #import pdb; pdb.set_trace()
        associations = self.is_associate_of.filter(association_type__association_behavior="child").filter(state="active")
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
        associations = self.has_associates.filter(association_type__association_behavior="child").filter(state="active")
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
        agent_ids = self.has_associates.filter(association_type__association_behavior="supplier").filter(state="active").values_list('is_associate')
        return EconomicAgent.objects.filter(pk__in=agent_ids)
        
    def exchange_firms(self): #todo: 'legal' is not a behavior, will there ever be a need for this?
        #import pdb; pdb.set_trace()
        agent_ids = self.has_associates.filter(association_type__association_behavior="legal").filter(state="active").values_list('is_associate')
        return EconomicAgent.objects.filter(pk__in=agent_ids)
        
    def members(self): 
        #import pdb; pdb.set_trace()
        agent_ids = self.has_associates.filter(association_type__association_behavior="member").filter(state="active").values_list('is_associate')
        return EconomicAgent.objects.filter(pk__in=agent_ids)
        
    #def affiliates(self):
    #    #import pdb; pdb.set_trace()
    #    agent_ids = self.has_associates.filter(association_type__identifier="affiliate").filter(state="active").values_list('is_associate')
    #    return EconomicAgent.objects.filter(pk__in=agent_ids)
        
    def customers(self):
        #import pdb; pdb.set_trace()
        agent_ids = self.has_associates.filter(association_type__association_behavior="customer").filter(state="active").values_list('is_associate')
        return EconomicAgent.objects.filter(pk__in=agent_ids)
        
    def potential_customers(self):
        #import pdb; pdb.set_trace()
        agent_ids = self.has_associates.filter(association_type__association_behavior="customer").filter(state="potential").values_list('is_associate')
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
        return self
        
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
            
    def is_context_agent(self):
        return self.agent_type.is_context
        
    def orders_queryset(self):
        orders = []
        for order in Order.objects.all():
            if self in order.context_agents():
                orders.append(order)
        order_ids = [order.id for order in orders]
        return Order.objects.filter(id__in=order_ids)
            
        
class AgentUser(models.Model):
    agent = models.ForeignKey(EconomicAgent,
        verbose_name=_('agent'), related_name='users')
    user = models.OneToOneField(User, 
        verbose_name=_('user'), related_name='agent')


ASSOCIATION_BEHAVIOR_CHOICES = (
    ('supplier', _('supplier')),
    ('customer', _('customer')),
    ('member', _('member')),
    ('child', _('child')),
)

class AgentAssociationType(models.Model):
    identifier = models.CharField(_('identifier'), max_length=12, unique=True)
    name = models.CharField(_('name'), max_length=128)
    plural_name = models.CharField(_('plural name'), default="", max_length=128)
    association_behavior = models.CharField(_('association behavior'), 
        max_length=12, choices=ASSOCIATION_BEHAVIOR_CHOICES,
        blank=True, null=True)
    description = models.TextField(_('description'), blank=True, null=True)
    label = models.CharField(_('label'), max_length=32, null=True)
    inverse_label = models.CharField(_('inverse label'), max_length=40, null=True)
    
    def __unicode__(self):
        return self.name
        
    @classmethod
    def create(cls, identifier, name, plural_name, association_behavior, label, inverse_label, verbosity=2):
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
            if association_behavior != agent_association_type.association_behavior:
                agent_association_type.association_behavior = association_behavior
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
            cls(identifier=identifier, name=name, plural_name=plural_name, association_behavior=association_behavior, label=label, inverse_label=inverse_label).save()
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
    AgentAssociationType.create('child', 'Child', 'Children', 'child', 'is child of', 'has child') 
    AgentAssociationType.create('member', 'Member', 'Members', 'member', 'is member of', 'has member')  
    AgentAssociationType.create('supplier', 'Supplier', 'Suppliers', 'supplier', 'is supplier of', 'has supplier') 
    AgentAssociationType.create('customer', 'Customer', 'Customers', 'customer', 'is customer of', 'has customer') 
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
    ('adjust', _('adjust')),
    ('payexpense', _('expense payment')),
)

RELATED_CHOICES = (
    ('process', _('process')),
    ('agent', _('agent')), #not used logically as an event type, rather for agent - resource type relationships
    ('exchange', _('exchange')),
)

RESOURCE_EFFECT_CHOICES = (
    ('+', _('increase')),
    ('-', _('decrease')),
    ('+-', _('adjust')),
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
        
    def used_for_value_equations(self):
        ets = EventType.objects.all()
        used_ids = [et.id for et in ets if et.used_for_value_equations()]
        return EventType.objects.filter(id__in=used_ids)     


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
        return self.name

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

    def default_event_value_equation(self):
        if self.used_for_value_equations():
            if self.relationship == "use":
                return "quantity * valuePerUnitOfUse"
            elif self.relationship == "cite" or self.relationship == "pay":
                return "quantity"
            elif self.relationship == "resource" or self.relationship == "receive":
                return "value"
            elif self.relationship == "expense" or self.relationship == "cash":
                return "value"
            else:
                return "quantity * valuePerUnit"
        return ""
            
    def used_for_value_equations(self):
        bad_relationships = [
            "consume",
            "in",
            #"pay",
            "receivecash",
            "shipment",
            "adjust",
            "distribute",
        ]
        bad_names = [
            "Work Provision",
            "Failed quantity",
            "Damage",
            "Receipt",
            "Sale",
            "Supply",
        ]
        if self.relationship in bad_relationships:
            return False
        elif self.name in bad_names:
            return False 
        return True
            
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

    
class RecipeInheritance(object):
    def __init__(self, parent, heir):
        self.parent = parent
        self.heir = heir

    def substitute(self, candidate):
        if candidate == self.parent:
            return self.heir
        else:
            return candidate

            
class ResourceClass(models.Model):
    name = models.CharField(_('name'), max_length=128, unique=True)
    description = models.TextField(_('description'), blank=True, null=True)
    
    def __unicode__(self):
        return self.name

INVENTORY_RULE_CHOICES = (
    ('yes', _('Keep inventory')),
    ('no', _('Not worth it')),
    ('never', _('Does not apply')),
)

class EconomicResourceType(models.Model):
    name = models.CharField(_('name'), max_length=128, unique=True)
    #version = models.CharField(_('version'), max_length=32, blank=True)    
    parent = models.ForeignKey('self', blank=True, null=True, 
        verbose_name=_('parent'), related_name='children')    
    resource_class = models.ForeignKey(ResourceClass, blank=True, null=True, 
        verbose_name=_('resource class'), related_name='resource_types')
    unit = models.ForeignKey(Unit, blank=True, null=True,
        verbose_name=_('unit'), related_name="resource_units",
        help_text=_('if this resource has different units of use and inventory, this is the unit of inventory'))
    unit_of_use = models.ForeignKey(Unit, blank=True, null=True,
        verbose_name=_('unit of use'), related_name="units_of_use",
        help_text=_('if this resource has different units of use and inventory, this is the unit of use'))
    unit_of_value = models.ForeignKey(Unit, blank=True, null=True,
        limit_choices_to={'unit_type': 'value'},
        verbose_name=_('unit of value'), related_name="resource_type_value_units")
    value_per_unit = models.DecimalField(_('value per unit'), max_digits=8, decimal_places=2, 
        default=Decimal("0.00"))
    value_per_unit_of_use = models.DecimalField(_('value per unit of use'), max_digits=8, decimal_places=2, 
        default=Decimal("0.00"))
    price_per_unit = models.DecimalField(_('price per unit'), max_digits=8, decimal_places=2, 
        default=Decimal("0.00"))
    unit_of_price = models.ForeignKey(Unit, blank=True, null=True,
        limit_choices_to={'unit_type': 'value'},
        verbose_name=_('unit of price'), related_name="resource_type_price_units")
    substitutable = models.BooleanField(_('substitutable'), default=True,
        help_text=_('Can any resource of this type be substituted for any other resource of this type?'))
    inventory_rule = models.CharField(_('inventory rule'), max_length=5,
        choices=INVENTORY_RULE_CHOICES, default='yes')
    photo = ThumbnailerImageField(_("photo"),
        upload_to='photos', blank=True, null=True)
    photo_url = models.CharField(_('photo url'), max_length=255, blank=True)
    url = models.CharField(_('url'), max_length=255, blank=True)
    description = models.TextField(_('description'), blank=True, null=True)
    #rate = models.DecimalField(_('rate'), max_digits=6, decimal_places=2, default=Decimal("0.00"), editable=False)
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

    def direct_children(self):
        return self.children.all()
        
    def with_all_children(self):
        answer = [self,]
        kids = self.direct_children()
        for kid in kids:
            answer.extend(kid.with_all_children())
        return answer
        
    def all_children(self):
        kids = self.direct_children()
        answer = list(kids)
        for kid in kids:
            answer.extend(kid.all_children())
        return answer
        
    def child_of_class(self, resource_class):
        kids = self.all_children()
        for kid in kids:
            if kid.resource_class == resource_class:
                return kid
        return None

    def node_id(self):
        return "-".join(["ResourceType", str(self.id)])

    def color(self):
        return "red"

    def onhand(self):
        return EconomicResource.goods.filter(
            resource_type=self,
            quantity__gt=0)
            
    def onhand_for_stage(self, stage):
        return EconomicResource.goods.filter(
            resource_type=self,
            stage=stage,
            quantity__gt=0)
    
    def onhand_for_resource_driven_recipe(self):
        return EconomicResource.goods.filter(
            resource_type=self,
            independent_demand__isnull=True,
            stage__isnull=True,
            quantity__gt=0)

    def all_resources(self):
        return self.resources.all()

    def onhand_qty(self):
        return sum(oh.quantity for oh in self.onhand())
        
    def onhand_qty_for_stage(self, stage):
        return sum(oh.quantity for oh in self.onhand_for_stage(stage))

    def onhand_qty_for_commitment(self, commitment):
        #pr changed
        #does not need order_item because net already skipped non-subs
        due_date = commitment.due_date
        stage = commitment.stage
        if stage:
            oh_qty = self.onhand_qty_for_stage(stage)
            priors = self.consuming_commitments_for_stage(stage).filter(due_date__lt=due_date)
        else:
            oh_qty = self.onhand_qty()
            priors = self.consuming_commitments().filter(due_date__lt=due_date)
        remainder = oh_qty - sum(p.quantity for p in priors)
        if remainder > 0:
            return remainder
        else:
            return Decimal("0")

    def scheduled_qty_for_commitment(self, commitment):
        #pr changed
        #does not need order_item because net already skipped non-subs
        #import pdb; pdb.set_trace()
        due_date = commitment.due_date
        stage = commitment.stage
        sked_rcts = self.producing_commitments().filter(due_date__lte=due_date).exclude(id=commitment.id)
        if stage:
            sked_rcts = sked_rcts.filter(stage=stage)
        unfilled_rcts = []
        for sr in sked_rcts:
            if not sr.is_fulfilled():
                unfilled_rcts.append(sr)
        sked_qty = sum(pc.quantity for pc in unfilled_rcts)
        if not sked_qty:
            return Decimal("0")
        if stage:
            priors = self.consuming_commitments_for_stage(stage).filter(due_date__lt=due_date)
        else:
            priors = self.consuming_commitments().filter(due_date__lt=due_date)
        remainder = sked_qty - sum(p.quantity for p in priors)
        if remainder > 0:
            return remainder
        else:
            return Decimal("0")

    def producing_process_type_relationships(self):
        #todo pr: this shd be replaced by own_recipes
        return self.process_types.filter(event_type__relationship='out')
        
    def manufacturing_producing_process_type_relationships(self):
        return self.process_types.filter(
            stage__isnull=True,
            event_type__relationship='out')
        
    def own_recipes(self):
        #todo pr: or shd that be own_producing_commitment_types?
        return self.process_types.filter(event_type__relationship='out')
        
    def own_or_parent_recipes(self):
        ptrs =  self.own_recipes()
        parent = None
        inheritance = None
        if not ptrs:
            parent = self.parent
            while parent:
                ptrs = parent.own_recipes()
                if ptrs:
                    break
                else:
                    parent = parent.parent
        if ptrs:
            if parent:
                inheritance = RecipeInheritance(parent, self)
        return ptrs, inheritance

    def main_producing_process_type_relationship(self, stage=None, state=None):
        #import pdb; pdb.set_trace()
        #pr changed
        ptrts, inheritance = self.own_or_parent_recipes()
        if stage or state:
            ptrts = ptrts.filter(stage=stage, state=state)
        if ptrts:
            one_ptrt = ptrts[0]
            if stage or state:
                return one_ptrt, inheritance
            else:
                if one_ptrt.stage:
                    stages, inheritance = self.staged_commitment_type_sequence()
                    if stages:
                        one_ptrt = stages[-1]
                    else:
                        return None, None
                return one_ptrt, inheritance
        else:
            return None, None
            
    def recipe_is_staged(self):
        #todo pr: shd this use own_or_parent_recipes?
        #staged_commitments = self.process_types.filter(stage__isnull=False)
        #pr changed
        ptrts, inheritance = self.own_or_parent_recipes()
        stages = [ct for ct in ptrts if ct.stage]
        if stages:
            return True
        else:
            return False

    def producing_process_types(self):
        #todo pr: shd this be own or own_or_parent_recipes?
        return [pt.process_type for pt in self.producing_process_type_relationships()]

    def main_producing_process_type(self, stage=None, state=None):
        #todo pr: shd this return inheritance, too?
        ptrt, inheritance = self.main_producing_process_type_relationship(stage, state)
        if ptrt:
            return ptrt.process_type
        else:
            return None
            
    def all_staged_commitment_types(self):
        #todo pr: shd this be own or own_or_parent_recipes?
        return self.process_types.filter(stage__isnull=False)
        
    def all_staged_process_types(self):
        cts = self.all_staged_commitment_types()
        pts = [ct.process_type for ct in cts]
        return list(set(pts))
        
    def all_stages(self):
        ids = [pt.id for pt in self.all_staged_process_types()]
        return ProcessType.objects.filter(id__in=ids)
        
    def staged_commitment_type_sequence(self):
        #import pdb; pdb.set_trace()
        #pr changed
        staged_commitments = self.process_types.filter(stage__isnull=False)
        parent = None
        inheritance = None
        if not staged_commitments:
            parent = self.parent
            while parent:
                staged_commitments = parent.process_types.filter(stage__isnull=False)
                if staged_commitments:
                    break
                else:
                    parent = parent.parent
        if not staged_commitments:
            return [], None
        creation_et = EventType.objects.get(name='Create Changeable') 
        chain = []
        creation = None
        try:
            if parent:
                inheritance = RecipeInheritance(parent, self)
                creation = parent.process_types.get(
                    stage__isnull=False,
                    event_type=creation_et)
            else:
                creation = self.process_types.get(
                    stage__isnull=False,
                    event_type=creation_et)
        except ProcessTypeResourceType.DoesNotExist:
            try:
                if parent:
                    creation = parent.process_types.get(
                        stage__isnull=True)
                else:
                    creation = self.process_types.get(
                        stage__isnull=True)
            except ProcessTypeResourceType.DoesNotExist:
                pass
        if creation:
            creation.follow_stage_chain(chain)
        return chain, inheritance
              
    def staged_commitment_type_sequence_beyond_workflow(self):
        #import pdb; pdb.set_trace()
        #pr changed
        staged_commitments = self.process_types.filter(stage__isnull=False)
        parent = None
        inheritance = None
        if not staged_commitments:
            parent = self.parent
            while parent:
                staged_commitments = parent.process_types.filter(stage__isnull=False)
                if staged_commitments:
                    break
                else:
                    parent = parent.parent
        if not staged_commitments:
            return [], None
        creation_et = EventType.objects.get(name='Create Changeable') 
        chain = []
        creation = None
        try:
            if parent:
                inheritance = RecipeInheritance(parent, self)
                creation = parent.process_types.get(
                    stage__isnull=False,
                    event_type=creation_et)
            else:
                creation = self.process_types.get(
                    stage__isnull=False,
                    event_type=creation_et)
        except ProcessTypeResourceType.DoesNotExist:
            try:
                if parent:
                    creation = parent.process_types.get(
                        stage__isnull=True)
                else:
                    creation = self.process_types.get(
                        stage__isnull=True)
            except ProcessTypeResourceType.DoesNotExist:
                pass
        if creation:
            creation.follow_stage_chain_beyond_workflow(chain)
        return chain, inheritance
        
    def staged_process_type_sequence(self):
        #pr changed
        pts = []
        stages, inheritance = self.staged_commitment_type_sequence()
        for stage in stages:
            if stage.process_type not in pts:
                pts.append(stage.process_type)
        return pts, inheritance
        
    def all_stages(self):
        pts, inheritance = self.staged_process_type_sequence()
        ids = [pt.id for pt in pts]
        return ProcessType.objects.filter(id__in=ids)
        
    def staged_process_type_sequence_beyond_workflow(self):
        #pr changed
        pts = []
        stages, inheritance = self.staged_commitment_type_sequence_beyond_workflow()
        for stage in stages:
            if stage.process_type not in pts:
                pts.append(stage.process_type)
        return pts, inheritance
        
    def recipe_needs_starting_resource(self):
        #todo pr: shd this pass inheritance on?
        #shd recipe_is_staged consider own_or_parent_recipes?
        if not self.recipe_is_staged():
            return False
        seq, inheritance = self.staged_commitment_type_sequence()
        ct0 = seq[0]
        if ct0.event_type.name == 'To Be Changed':
            return True
        else:
            return False
            
    def has_listable_recipe(self):
        #todo pr: shd this be own or own_or_parent_recipes?
        answer = False
        ctype, inheritance = self.own_or_parent_recipes()
        if ctype:
            answer = True
            if self.recipe_needs_starting_resource():
                answer = False
        return answer
        
    def can_be_parent(self):
        if self.own_recipes():
            #if self.recipe_is_staged():
            return True
        return False

    def generate_staged_work_order(self, order_name, start_date, user):
        #pr changed
        #import pdb; pdb.set_trace()
        pts, inheritance = self.staged_process_type_sequence()
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
            p = pt.create_process(new_start_date, user, inheritance)
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
        #Todo: apply selected_context_agent here
        for process in processes:
            for ct in process.commitments.all():
                ct.independent_demand = order
                ct.order_item = order_item
                ct.save()
        return order
        
    def generate_staged_order_item(self, order, start_date, user):
        #pr changed
        pts, inheritance = self.staged_process_type_sequence()
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
                ct.save()
            #import pdb; pdb.set_trace()
            assert octs.count() == 1, 'generate_staged_order_item assumes one and only one output'
            order_item = octs[0]
            if order.due_date < last_process.end_date:
                order.due_date = last_process.end_date
                order.save()
        #Todo: apply selected_context_agent here
        for process in processes:
            for ct in process.commitments.all():
                ct.independent_demand = order
                ct.order_item = order_item
                ct.save()
        return order
    
    def generate_staged_work_order_from_resource(self, resource, order_name, start_date, user):
        #pr changed
        #import pdb; pdb.set_trace()
        pts, inheritance = self.staged_process_type_sequence()
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
            p = pt.create_process(new_start_date, user, inheritance)
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
            #pr changed
            if not resource.resource_type.substitutable:
                resource.independent_demand = order
                resource.order_item = order_item
                resource.save()
        #Todo: apply selected_context_agent here
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
        #todo pr: cd this be shortcut but looking at recipes first?
        #todo pr: shd this be own or own_or_parent_recipes?
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
        #todo pr: shd this be own or own_or_parent_recipes?
        return self.process_types.filter(event_type__resource_effect='-')

    def citing_process_type_relationships(self):
        #todo pr: shd this be own or own_or_parent_recipes?
        return self.process_types.filter(event_type__relationship='cite')

    def wanting_process_type_relationships(self):
        #todo pr: shd this be own or own_or_parent_recipes?
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
            
    def consuming_commitments_for_stage(self, stage):
        return self.commitments.filter(
            finished=False, 
            stage=stage,
            event_type__resource_effect='>~')

    def wanting_process_type_relationships(self):
        #todo pr: shd this be own or own_or_parent_recipes?
        return self.process_types.exclude(event_type__relationship='out')
        
    def wanting_process_type_relationships_for_stage(self, stage):
        #todo pr: shd this be own or own_or_parent_recipes?
        return self.process_types.exclude(event_type__relationship='out').filter(stage=stage)

    def wanting_process_types(self):
        #todo pr: shd this be own or own_or_parent_recipes?
        return [pt.process_type for pt in self.wanting_process_type_relationships()]

    def consuming_process_types(self):
        #todo pr: shd this be own or own_or_parent_recipes?
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
        if self.stage:
            return self.commitments.filter(
                event_type__relationship='out',
                stage=self.stage,
                process__finished=False)
        else:
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
        #todo pr: this shd be own_recipes
        answer.extend(self.manufacturing_producing_process_type_relationships())
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
        #todo pr: self shd be excluded from parents
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
        #return XbillProcessTypeForm(prefix=self.process_create_prefix())
        
    def process_stream_create_form(self):
        from valuenetwork.valueaccounting.forms import RecipeProcessTypeForm
        #init = {"name": " ".join(["Make", self.name])}
        #return RecipeProcessTypeForm(initial=init, prefix=self.process_create_prefix())
        return RecipeProcessTypeForm(prefix=self.process_create_prefix())
            
    def source_create_prefix(self):
        return "".join(["SRC", str(self.id)])

    def source_create_form(self):
        from valuenetwork.valueaccounting.forms import AgentResourceTypeForm
        return AgentResourceTypeForm(prefix=self.source_create_prefix())

    def directional_unit(self, direction):
        answer = self.unit
        if self.unit_of_use:
            if direction == "use" or direction == "cite":
                answer = self.unit_of_use
        return answer

    def unit_for_use(self):
        return self.directional_unit("use")

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

    def work_without_value(self):
        work = self.events.filter(event_type__relationship="work")
        if work:
            if not self.value_per_unit:
                return True
        return False
    
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


class ResourceTypeList(models.Model):
    name = models.CharField(_('name'), max_length=128)
    description = models.TextField(_('description'), blank=True, null=True)
    context_agent = models.ForeignKey(EconomicAgent,
        blank=True, null=True,
        limit_choices_to={"agent_type__is_context": True,},
        verbose_name=_('context agent'), related_name='lists')
        
    class Meta:
        ordering = ('name',)

    def __unicode__(self):
        return self.name
        
    def resource_types_string(self):
        return ", ".join([elem.resource_type.name for elem in self.list_elements.all()])
        
    def form_prefix(self):
        return "-".join(["RTL", str(self.id)])
   
    def change_form(self):
        from valuenetwork.valueaccounting.forms import ResourceTypeListForm
        prefix=self.form_prefix()
        rt_ids = [elem.resource_type.id for elem in self.resource_types.all()]
        init = {"resource_types": rt_ids,}
        return ResourceTypeListForm(instance=self, prefix=prefix, initial=init)
        
    def recipe_class(self):
        answer = "workflow"
        for elem in self.list_elements.all():
            if not elem.resource_type.recipe_is_staged():
                answer = "manufacturing"
        return answer

        
class ResourceTypeListElement(models.Model):
    resource_type_list = models.ForeignKey(ResourceTypeList, 
        verbose_name=_('resource type list'), related_name='list_elements')
    resource_type = models.ForeignKey(EconomicResourceType, 
        verbose_name=_('resource type'), related_name='lists')
    default_quantity = models.DecimalField(_('default quantity'), max_digits=8, decimal_places=2, 
        default=Decimal("1.0"))
        
    class Meta:
        unique_together = ('resource_type_list', 'resource_type')
        ordering = ('resource_type_list', 'resource_type')
        
    def __unicode__(self):
        return ": ".join([self.resource_type_list.name, self.resource_type.name])
   

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
        
    def all_production_resource_types(self):
        patterns = self.production_patterns()
        rt_ids = []
        for pat in patterns:
            #todo pr: shd this be own or own_or_parent_recipes?
            rt_ids.extend([rt.id for rt in pat.output_resource_types() if rt.producing_process_type_relationships()])
        return EconomicResourceType.objects.filter(id__in=rt_ids)
        

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
        
        #import pdb; pdb.set_trace()
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
        rts = []
        ets = self.event_types()
        for et in ets:
            rts.extend(self.get_resource_types(et))
        rt_ids = [rt.id for rt in rts]
        return EconomicResourceType.objects.filter(id__in=rt_ids)
        
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
        
    def matl_contr_resource_types_with_resources(self):
        #import pdb; pdb.set_trace()
        rts = [rt for rt in self.resource_types_for_relationship("resource") if rt.onhand()]
        rt_ids = [rt.id for rt in rts]
        return EconomicResourceType.objects.filter(id__in=rt_ids)
        
    def expense_resource_types(self):
        #import pdb; pdb.set_trace()
        return self.resource_types_for_relationship("expense")

    def process_expense_resource_types(self):
        return self.resource_types_for_relationship("payexpense")
        
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
    
    def use_case_identifier_list(self):
        ucl = [uc.use_case.identifier for uc in self.use_cases.all()]
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
    UseCase.create('non_prod', _('Non-production Logging'), True)
    UseCase.create('rand', _('Manufacturing Recipes/Logging'))
    UseCase.create('recipe', _('Workflow Recipes/Logging'))
    UseCase.create('todo', _('Todos'), True)
    UseCase.create('cust_orders', _('Customer Orders'))
    UseCase.create('purchasing', _('Purchasing')) 
    UseCase.create('res_contr', _('Material Contribution'))
    UseCase.create('purch_contr', _('Purchase Contribution'))
    UseCase.create('exp_contr', _('Expense Contribution'), True)
    UseCase.create('sale', _('Sale'))
    UseCase.create('distribution', _('Distribution'), True)
    UseCase.create('val_equation', _('Value Equation'), True)
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
    EventType.create('Adjust Quantity', _('adjusts'), 'adjusted', 'adjust', 'agent', '+-', 'quantity')
    EventType.create('Cash Receipt', _('receives cash'), _('cash received by'), 'receivecash', 'exchange', '+', 'value')
    EventType.create('Distribution', _('distributes'), _('distributed by'), 'distribute', 'exchange', '-', 'value')
    EventType.create('Process Expense', _('pays expense'), _('paid by'), 'payexpense', 'process', '=', 'value')    

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
    UseCaseEventType.create('rand', 'Process Expense')
    #todo: 'rand' now = mfg/assembly, 'recipe' now = workflow.  Need to rename these use cases.
    UseCaseEventType.create('recipe','Citation')
    UseCaseEventType.create('recipe', 'Resource Consumption')
    UseCaseEventType.create('recipe', 'Resource Production')
    UseCaseEventType.create('recipe', 'Resource use')
    UseCaseEventType.create('recipe', 'Time Contribution')
    UseCaseEventType.create('recipe', 'To Be Changed')
    UseCaseEventType.create('recipe', 'Change')
    UseCaseEventType.create('recipe', 'Create Changeable')
    UseCaseEventType.create('recipe', 'Process Expense')
    UseCaseEventType.create('todo', 'Todo')
    #UseCaseEventType.create('cust_orders', 'Damage')
    #UseCaseEventType.create('cust_orders', 'Payment')
    #UseCaseEventType.create('cust_orders', 'Receipt')
    UseCaseEventType.create('cust_orders', 'Sale')
    #UseCaseEventType.create('cust_orders', 'Shipment')
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
    UseCaseEventType.create('val_equation', 'Time Contribution')
    UseCaseEventType.create('val_equation', 'Resource Production')
    UseCaseEventType.create('val_equation', 'Process Expense')

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
        
    def rand_orders(self):
        return Order.objects.filter(order_type="rand")
                
    def open_rand_orders(self):
        orders = self.rand_orders()
        open_orders = []
        for order in orders:
            if order.has_open_processes():
                open_orders.append(order)
            if not order.unordered_processes():
                open_orders.append(order)
        return open_orders
        
    def closed_work_orders(self):
        orders = self.rand_orders()
        closed_orders = []
        for order in orders:
            if not order.has_open_processes():
                closed_orders.append(order)
        return closed_orders        
        
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
            
    def shorter_label_customer_order(self):
        receiver_label = ", buyer:"
        receiver_name = ""
        if self.receiver:
            receiver_name = self.receiver.name
        due_label = " on:"
        return " ".join(
            [self.get_order_type_display(), 
            str(self.id),
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

    def process(self): #todo: should this be on order_item?
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
            context_agent,
            quantity,
            event_type,
            unit,
            description,
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
            context_agent=context_agent,
            description=description,
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

    def create_order_item(self,
            resource_type,
            quantity,
            user):
        #todo pr: may need return inheritance?
        #import pdb; pdb.set_trace()
        ptrt, inheritance = resource_type.main_producing_process_type_relationship()
        description = ""
        context_agent = None
        stage=None
        state=None
        if ptrt:
            event_type=ptrt.event_type
            stage=ptrt.stage
            state=ptrt.state
            description=ptrt.description
            context_agent=ptrt.process_type.context_agent
        else:
            if self.order_type == "customer":
                event_type = EventType.objects.get(relationship="shipment")
                ois = self.order_items()
                if ois:
                    context_agent = ois[0].context_agent
            else:
                assert ptrt, 'create_order_item for a work order assumes items with a producing process type'
        commitment = self.add_commitment(
            resource_type=resource_type,
            context_agent=context_agent,
            quantity=quantity,
            event_type=event_type,
            unit=resource_type.unit,
            description=description,
            stage=stage,
            state=state)
        if ptrt:
            commitment.generate_producing_process(user, [], inheritance, explode=True)
        return commitment
        
    def add_customer_order_item(self,
            resource_type,
            quantity,
            description,
            user,
            stage=None,
            state=None,
            due=None):
        #import pdb; pdb.set_trace()
        if not due:
            due=self.due_date
        event_type = EventType.objects.get(relationship="shipment")
        ct = Commitment(
            order=self,
            independent_demand=self,
            event_type=event_type,
            resource_type=resource_type,
            from_agent=self.provider,
            to_agent=self.receiver,
            context_agent=self.provider,
            description=description,
            stage=stage,
            state=state,
            quantity=quantity,
            unit_of_quantity=resource_type.unit,
            due_date=due,
            created_by=user)
        ct.save()
        ct.order_item = ct
        ct.save()
        ct.generate_producing_process(user, [], inheritance=None, explode=True)
        return ct
    
    def all_processes(self):
        # this method includes only processes for this order
        #import pdb; pdb.set_trace()
        deliverables = self.commitments.filter(event_type__relationship="out")
        if deliverables:
            processes = [d.process for d in deliverables if d.process]
        else:
            processes = []
            commitments = Commitment.objects.filter(independent_demand=self)
            for c in commitments:
                if c.process:
                    processes.append(c.process)
            processes = list(set(processes))
        roots = []
        for p in processes:
            if not p.next_processes_for_order(self):
                roots.append(p)
        ordered_processes = []
        for root in roots:
            visited = []
            root.all_previous_processes_for_order(self, ordered_processes, visited, 0)
        ordered_processes = list(set(ordered_processes))
        ordered_processes = sorted(ordered_processes, key=attrgetter('end_date'))
        ordered_processes = sorted(ordered_processes, key=attrgetter('start_date'))
        return ordered_processes 
        
    def unordered_processes(self):
        cts = Commitment.objects.filter(independent_demand=self)
        processes = set()
        for ct in cts:
            processes.add(ct.process)
        return processes
        
    def all_dependent_commitments(self):
        return Commitment.objects.filter(independent_demand=self)

    def has_open_processes(self):
        answer = False
        processes = self.unordered_processes()
        for process in processes:
            if process.finished == False:
                answer = True
                break
        return answer

    def last_process_in_order(self):
        processes = self.all_processes()
        if processes:
            return processes[-1]
        else:
            return None
                
    def process_types(self):
        pts = []
        for process in self.all_processes():
            if process.process_type:
                pts.append(process.process_type)
        return pts
        
    def all_events(self):
        processes = self.unordered_processes()
        events = []
        for process in processes:
            events.extend(process.events.all())
        return events
        
    def all_input_events(self):
        processes = self.unordered_processes()
        events = []
        for process in processes:
            events.extend(process.events.exclude(event_type__relationship="out"))
        return events
        
    def context_agents(self):
        items = self.order_items()
        return [item.context_agent for item in items]
        
    def sale(self):
        if self.order_type == "customer":
            return Exchange.objects.get(order=self)
        else:
            return None

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
        limit_choices_to={"agent_type__is_context": True,},
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
        
    def create_process(self, start_date, user, inheritance=None):
        #pr changed
        end_date = start_date + datetime.timedelta(minutes=self.estimated_duration)
        process = Process(          
            name=self.name,
            notes=self.description or "",
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
            ic.create_commitment_for_process(process, user, inheritance)
        output_ctypes = self.produced_resource_type_relationships()
        for oc in output_ctypes:
            oc.create_commitment_for_process(process, user, inheritance)
        #todo: delete next lines, makes awkward process.names?
        #process.name = " ".join([process.name, oc.resource_type.name])
        #process.save()
        return process
                            
    def produced_resource_type_relationships(self):
        #todo pr: needs own_or_parent_recipes
        return self.resource_types.filter(event_type__relationship='out')
        
    def main_produced_resource_type_relationship(self):
        ptrs = self.produced_resource_type_relationships()
        if ptrs:
            return ptrs[0]
        else:
            return None
            
    def is_stage(self):
        ct = self.main_produced_resource_type_relationship()
        if ct.stage:
            return True
        return False
                                
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
        qty = Decimal("0.0")
        prtr = self.main_produced_resource_type_relationship()
        if prtr:
            qty = prtr.quantity
        init = {"quantity": qty,}
        return XbillProcessTypeForm(instance=self, initial=init, prefix=self.xbill_change_prefix())
    
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
        #init = {"name": " ".join(["Make", rt.name])}
        #return RecipeProcessTypeForm(initial=init, prefix=self.stream_process_type_create_prefix())
        return RecipeProcessTypeForm(prefix=self.stream_process_type_create_prefix())
        
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
        default=Decimal("1.00"), editable=False)
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
    value_per_unit = models.DecimalField(_('value per unit'), max_digits=8, decimal_places=2, 
        default=Decimal("0.00"))
    value_per_unit_of_use = models.DecimalField(_('value per unit of use'), max_digits=8, decimal_places=2, 
        default=Decimal("0.00"))
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
        #rollup stage change
        id_str = self.identifier or str(self.id)
        rt_name = self.resource_type.name
        return ": ".join([
                rt_name,
                id_str,
            ])
        
    def value_explanation(self):
        return "Value per unit is composed of the value of the inputs on the next level:"
        
    def unit_of_quantity(self):
        return self.resource_type.unit

    def change_form(self):
        from valuenetwork.valueaccounting.forms import EconomicResourceForm
        #import pdb; pdb.set_trace()
        unit = self.resource_type.unit_of_use
        vpu_help = None
        if unit:
            vpu_help = "Value added when this resource is used for one " + unit.abbrev
        return EconomicResourceForm(instance=self, vpu_help=vpu_help)

    #def change_role_formset(self):
    #    from valuenetwork.valueaccounting.forms import ResourceRoleAgentForm
    #    return EconomicResourceForm(instance=self)
    
    def test_rollup(self):
        import pdb; pdb.set_trace()
        visited = set()
        path = []
        depth = 0
        value_per_unit = self.roll_up_value(path, depth, visited)
        return path
    
    def roll_up_value(self, path, depth, visited):
        #import pdb; pdb.set_trace()
        #Value_per_unit will be the result of this method.
        depth += 1
        self.depth = depth
        #self.explanation = "Value per unit consists of all the input values on the next level"
        path.append(self)
        value_per_unit = Decimal("0.0")
        #Values of all of the inputs will be added to this list.
        values = []
        #Resource contributions use event.value.
        contributions = self.resource_contribution_events()
        for evt in contributions:
            #if evt.id == 3960:
            #    import pdb; pdb.set_trace()
            evt_vpu = evt.value / evt.quantity
            if evt_vpu:
                values.append([evt_vpu, evt.quantity])
            depth += 1
            evt.depth = depth
            path.append(evt)
            depth -= 1
        #Purchase contributions use event.value.
        buys = self.purchase_events()
        for evt in buys:
            #import pdb; pdb.set_trace()
            evt_vpu = evt.value / evt.quantity
            if evt_vpu:
                values.append([evt_vpu, evt.quantity])
            depth += 1
            evt.depth = depth
            path.append(evt)
            depth -= 1
        citations = []
        production_value = Decimal("0.0")
        #rollup stage change
        processes = self.producing_processes_for_historical_stage()
        for process in processes:
            pe_value = Decimal("0.0")
            if process not in visited:
                visited.add(process)
                depth += 1
                process.depth = depth
                production_qty = process.production_quantity()
                path.append(process)
                #depth += 1
                if production_qty:
                    inputs = process.incoming_events()
                    for ip in inputs:
                        #Work contributions use resource_type.value_per_unit
                        if ip.event_type.relationship == "work":
                            ip.value = ip.quantity * ip.value_per_unit()
                            ip.save()
                            pe_value += ip.value
                            ip.depth = depth
                            path.append(ip)
                        #Use contributions use resource value_per_unit_of_use.
                        elif ip.event_type.relationship == "use":
                            if ip.resource:
                                ip.value = ip.quantity * ip.resource.value_per_unit_of_use
                                ip.save()
                                pe_value += ip.value
                                ip.resource.roll_up_value(path, depth, visited)
                                ip.depth = depth
                                path.append(ip)
                        #Consume contributions use resource rolled up value_per_unit
                        elif ip.event_type.relationship == "consume" or ip.event_type.name == "To Be Changed":
                            ip.depth = depth
                            path.append(ip)
                            #rollup stage change
                            value_per_unit = ip.roll_up_value(path, depth, visited)
                            ip.value = ip.quantity * value_per_unit
                            ip.save()
                            pe_value += ip.value
                        #Citations valued later, after all other inputs added up
                        elif ip.event_type.relationship == "cite":
                            ip.depth = depth
                            path.append(ip)
                            if ip.resource_type.unit_of_use:
                                if ip.resource_type.unit_of_use.unit_type == "percent":
                                    citations.append(ip)
                            else:
                                ip.value = ip.quantity
                            if ip.resource:
                                ip.resource.roll_up_value(path, depth, visited)
            production_value += pe_value
        if production_value:
            #Citations use percentage of the sum of other input values.
            for c in citations:
                percentage = c.quantity / 100
                c.value = production_value * percentage
                c.save()
            for c in citations:
                production_value += c.value
        if production_value and production_qty:
            #print "production value:", production_value, "production qty", production_qty
            production_value_per_unit = production_value / production_qty
            values.append([production_value_per_unit, production_qty])
        #If many sources of value, compute a weighted average.
        #Multiple sources cd be:
        #    resource contributions, purchases, and multiple production processes.
        if values:
            if len(values) == 1:
                value_per_unit = values[0][0]
            else:
                #compute weighted average
                weighted_values = sum(v[0] * v[1] for v in values)
                weights = sum(v[1] for v in values)
                if weighted_values and weights:
                    value_per_unit = weighted_values / weights
        self.value_per_unit = value_per_unit.quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
        self.save()
        return self.value_per_unit
        
    def rollup_explanation(self):
        depth = -1
        visited = set()
        path = []
        queue = []
        #import pdb; pdb.set_trace()
        self.rollup_explanation_traversal(path, visited, depth)
        return path
        
    def direct_value_tree(self):
        depth = -1
        visited = set()
        path = []
        queue = []
        self.direct_value_components(path, visited, depth)
        return path
        
    def rollup_explanation_traversal(self, path, visited, depth):
        depth += 1
        self.depth = depth
        path.append(self)
        depth += 1
        contributions = self.resource_contribution_events()
        for evt in contributions:
            evt.depth = depth
            path.append(evt)
        buys = self.purchase_events()
        for evt in buys:
            evt.depth = depth
            path.append(evt)
        processes = self.producing_processes()
        for process in processes:
            if process not in visited:
                visited.add(process)
                production_qty = sum(pe.quantity for pe in process.production_events())
                if production_qty:
                    inputs = process.incoming_events()
                    for ip in inputs:
                        if ip.event_type.relationship == "work":
                            ip.depth = depth
                            path.append(ip)
                        elif ip.event_type.relationship == "use":
                            ip.depth = depth
                            path.append(ip)
                        elif ip.event_type.relationship == "consume" or ip.event_type.name == "To Be Changed":
                            ip.depth = depth
                            path.append(ip)
                            ip.resource.rollup_explanation_traversal(path, visited, depth)
                        elif ip.event_type.relationship == "cite":
                            ip.depth = depth
                            path.append(ip)
                            
    def direct_value_components(self, components, visited, depth):
        depth += 1
        self.depth = depth
        components.append(self)
        depth += 1
        contributions = self.resource_contribution_events()
        for evt in contributions:
            evt.depth = depth
            components.append(evt)
        buys = self.purchase_events()
        for evt in buys:
            evt.depth = depth
            components.append(evt)
        processes = self.producing_processes()
        for process in processes:
            #todo: make sure this works for >1 process producing the same resource
            if process not in visited:
                visited.add(process)
                production_qty = sum(pe.quantity for pe in process.production_events())
                if production_qty:
                    inputs = process.incoming_events()
                    for ip in inputs:
                        if ip.event_type.relationship == "work":
                            ip.depth = depth
                            components.append(ip)
                        elif ip.event_type.relationship == "use":
                            ip.depth = depth
                            components.append(ip)
                        elif ip.event_type.relationship == "consume" or ip.event_type.name == "To Be Changed":
                            ip.depth = depth
                            components.append(ip)
                            #depth += 1
                            ip.resource.direct_value_components(components, visited, depth)
                            #depth += 1
                        elif ip.event_type.relationship == "cite":
                            ip.depth = depth
                            components.append(ip)       
        
    def test_compute_income_shares(self):
        visited = set()
        path = []
        depth = 0
        value_per_unit = self.roll_up_value(path, depth, visited)
        #print "value_per_unit:", value_per_unit
        value = self.quantity * value_per_unit
        visited = set()
        shares = []
        #import pdb; pdb.set_trace()
        quantity = self.quantity or Decimal("1.0")
        self.compute_income_shares(quantity, value, shares, visited)
        total = sum(s.share for s in shares)
        for s in shares:
            s.fraction = s.share / total
        #import pdb; pdb.set_trace()
        #print "total shares:", total
        return shares
         
    def compute_shipment_income_shares(self, quantity):
        visited = set()
        path = []
        depth = 0
        value_per_unit = self.roll_up_value(path, depth, visited)
        #print "value_per_unit:", value_per_unit
        value = quantity * value_per_unit
        visited = set()
        shares = []
        #import pdb; pdb.set_trace()
        self.compute_income_shares(quantity, value, shares, visited)
        total = sum(s.share for s in shares)
        for s in shares:
            s.fraction = s.share / total
        #import pdb; pdb.set_trace()
        #print "total shares:", total
        return shares
        
    def compute_income_shares(self, quantity, value, events, visited):
        #This method assumes that self.roll_up_value has been run,
        #and all contribution events have been valued.
        #print "Resource:", self.id, self
        #print "running quantity:", quantity, "running value:", value
        #import pdb; pdb.set_trace()
        contributions = self.resource_contribution_events()
        for evt in contributions:
            #if evt.id == 3960:
            #    import pdb; pdb.set_trace()
            if evt.value:
                vpu = evt.value / evt.quantity
                evt.share = quantity * vpu
                events.append(evt)
                #print evt.id, evt, evt.share
                #print "----Event.share:", evt.share, "= evt.value:", evt.value
        #purchases of resources in value flow are contributions
        buys = self.purchase_events()
        for evt in buys:
            #import pdb; pdb.set_trace()
            #if evt.value:
            #    vpu = evt.value / evt.quantity
            #    evt.share = quantity * vpu
            #    events.append(evt)
            if evt.exchange:
                evt.exchange.compute_income_shares(evt, quantity, value, events, visited)
        processes = self.producing_processes()
        for process in processes:
            if process not in visited:
                visited.add(process)
                if quantity:
                    #todo: how will this work for >1 processes producing the same resource?
                    #what will happen to the shares of the inputs of the later processes?
                    production_events = process.production_events()
                    produced_qty = sum(pe.quantity for pe in production_events)
                    distro_fraction = 1
                    distro_qty = quantity
                    if produced_qty > quantity:
                        distro_fraction = quantity / produced_qty
                        quantity = Decimal("0.0")
                    elif produced_qty <= quantity:
                        distro_qty = produced_qty
                        quantity -= produced_qty
                    for pe in production_events:
                        pe.share = pe.quantity * distro_fraction
                        events.append(pe)
                    inputs = process.incoming_events()
                    for ip in inputs:
                        #we assume here that work events are contributions
                        if ip.event_type.relationship == "work":
                            ip.share = ip.value * distro_fraction
                            events.append(ip)
                            #print ip.id, ip, ip.share
                            #print "----Event.share:", ip.share, "= Event.value:", ip.value, "* distro_fraction:", distro_fraction
                        elif ip.event_type.relationship == "use":
                            #use events are not contributions, but their resources may have contributions
                            if ip.resource:
                                ip_value = ip.value * distro_fraction
                                d_qty = distro_qty
                                if ip_value:
                                    d_qty = ip_value / value
                                ip.resource.compute_income_shares(d_qty, ip_value, events, visited) 
                        elif ip.event_type.relationship == "consume" or ip.event_type.name == "To Be Changed":
                            #consume events are not contributions, but their resources may have contributions
                            ip_value = ip.value * distro_fraction
                            #if ip.resource.id == 98:
                            #    import pdb; pdb.set_trace()
                            d_qty = ip.quantity * distro_fraction
                            #if ip_value:
                                #print "consumption:", ip.id, ip, "ip.value:", ip.value
                                #print "----value:", ip_value, "d_qty:", d_qty, "distro_fraction:", distro_fraction
                            ip.resource.compute_income_shares(d_qty, ip_value, events, visited)
                        elif ip.event_type.relationship == "cite":
                            #import pdb; pdb.set_trace()   
                            #citation events are not contributions, but their resources may have contributions
                            ip_value = ip.value * distro_fraction
                            d_qty = distro_qty
                            if ip_value:
                                d_qty = ip_value / value
                                #print "citation:", ip.id, ip, "ip.value:", ip.value
                                #print "----value:", ip_value, "d_qty:", d_qty, "distro_fraction:", distro_fraction
                            ip.resource.compute_income_shares(d_qty, ip_value, events, visited)

    def direct_share_components(self, components, visited, depth):
        depth += 1
        self.depth = depth
        components.append(self)
        depth += 1
        contributions = self.resource_contribution_events()
        for evt in contributions:
            evt.depth = depth
            components.append(evt)
        buys = self.purchase_events()
        for evt in buys:
            evt.depth = depth
            components.append(evt)
        processes = self.producing_processes()
        for process in processes:
            if process not in visited:
                visited.add(process)
                production_qty = sum(pe.quantity for pe in process.production_events())
                if production_qty:
                    inputs = process.incoming_events()
                    for ip in inputs:
                        if ip.event_type.relationship == "work":
                            ip.depth = depth
                            components.append(ip)
                        elif ip.event_type.relationship == "use":
                            ip.depth = depth
                            components.append(ip)
                        elif ip.event_type.relationship == "consume" or ip.event_type.name == "To Be Changed":
                            ip.depth = depth
                            components.append(ip)
                            #depth += 1
                            ip.resource.direct_value_components(components, visited, depth)
                            #depth += 1
                        elif ip.event_type.relationship == "cite":
                            ip.depth = depth
                            components.append(ip)
                            
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
        
    def producing_processes(self):
        pes = self.producing_events()
        processes = [pe.process for pe in pes if pe.process]
        processes = list(set(processes))
        return processes
        
    def producing_processes_for_historical_stage(self):
        #rollup stage change
        pes = self.producing_events()
        processes = [pe.process for pe in pes if pe.process]
        try:
            processes = [p for p in processes if p.process_type==self.historical_stage]
        except AttributeError:
            pass
        processes = list(set(processes))
        return processes
        
    def where_from_events(self):
        return self.events.filter(
            Q(event_type__relationship='out')|Q(event_type__relationship='receive')|Q(event_type__relationship='receivecash')
            |Q(event_type__relationship='cash')|Q(event_type__relationship='resource'))

    def consuming_events(self):
        return self.events.filter(event_type__relationship='consume')

    def using_events(self):
        return self.events.filter(event_type__relationship="use")
        
    def resource_contribution_events(self):
        ret_et = EventType.objects.get(relationship="resource")
        return self.events.filter(event_type=ret_et)
        
    def purchase_events(self):
        rct_et = EventType.objects.get(relationship="receive")
        return self.events.filter(event_type=rct_et)

    def all_usage_events(self):
        return self.events.exclude(event_type__relationship="out").exclude(event_type__relationship="receive").exclude(event_type__relationship="resource").exclude(event_type__relationship="cash")

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
        
    def unsourced_consumption(self):
        if self.consuming_events():
            if not self.where_from_events():
                return True
        return False
        
    def used_without_value(self):
        if self.using_events():
            if not self.value_per_unit_of_use:
                return True
        return False

    def is_deletable(self):
        if self.events.all():
            return False
        if self.quantity != 0:
            return False
        return True
        
    def track_lot_forward(self):
        pass
        
        
    def bill_of_lots(self):
        flows = self.inputs_to_output()
        lots = []
        for flow in flows:
            if type(flow) is EconomicEvent:
                resource = flow.resource
                if not resource == self:
                    lots.append(resource)
        lots = list(set(lots))
        lots.append(self)
        return lots

    def inputs_to_output(self):
        flows = self.incoming_value_flows()
        flows.reverse()
        return flows

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
            #this needs to include purchases and contributions
            for event in self.producing_events():
                event.depth = depth
                flows.append(event)
                p = event.process
                if p:
                    if p not in visited:
                        visited.append(p)
                        depth += 1
                        p.depth = depth
                        flows.append(p)
                        depth += 1
                        #process.incoming_events shd include p&c
                        for evt in p.incoming_events():
                            evt.depth = depth
                            flows.append(evt)
                            if evt.resource:
                                if evt.resource not in resources:
                                    resources.append(evt.resource)
            for event in self.resource_contribution_events():
                event.depth = depth
                flows.append(event)
            for event in self.purchase_events():
                event.depth = depth
                flows.append(event)
                if event.exchange:
                    for pmt in event.exchange.payment_events():
                        pmt.depth = depth + 1
                        flows.append(pmt)
            for resource in resources:
                resource.incoming_value_flows_dfs(flows, visited, depth)
                
    def incoming_events(self):
        flows = self.incoming_value_flows()
        events = []
        for flow in flows:
            if type(flow) is EconomicEvent:
                if flow not in events:
                    events.append(flow)
        return events
         
    def value_flow_going_forward(self):
        #todo: needs rework, see next method
        #import pdb; pdb.set_trace()
        flows = []
        visited = []
        depth = 0
        self.depth = depth
        flows.append(self)
        self.value_flow_going_forward_dfs(flows, visited, depth)
        creation_et = EventType.objects.get(name='Create Changeable')
        production_et = EventType.objects.get(name='Resource Production')
        receipt_et = EventType.objects.get(name='Receipt')
        all_events = self.events.all()
        events = all_events.filter(
            Q(event_type=creation_et)|
            Q(event_type=production_et)|
            Q(event_type=receipt_et))
        if events:
            processes = []
            for event in events:
                flows.insert(0, event)
                if event.process:
                    if event.process not in processes:
                        processes.append(event.process)
            for process in processes:
                flows.insert(0, process)
        return flows
                
    def value_flow_going_forward_dfs(self, flows, visited, depth):
        #import pdb; pdb.set_trace()
        if not self in visited:
            visited.append(self)
            depth += 1
            #todo: this will break, depends on event creation order
            for event in self.all_usage_events().order_by("id"):
                event.depth = depth
                flows.append(event)
                p = event.process
                if p:
                    if not p in visited:
                        depth += 1
                        p.depth = depth
                        flows.append(p)
                        depth += 1
                        for evt in p.production_events():
                            evt.depth = depth
                            flows.append(evt)
                            
    def staged_process_sequence_beyond_workflow(self):
        #todo: this was created for a DHen report 
        # but does not work yet because the converted data
        # has no commitments
        # Plus, it can't be tested and so probably won't work.
        processes = []
        if not self.stage:
            return processes
        creation_event = None
        #import pdb; pdb.set_trace()
        creation_et = EventType.objects.get(name='Create Changeable')
        production_et = EventType.objects.get(name='Resource Production')
        receipt_et = EventType.objects.get(name='Receipt')
        all_events = self.events.all()
        events = all_events.filter(
            Q(event_type=creation_et)|
            Q(event_type=production_et)|
            Q(event_type=receipt_et))
        if events:
            creation_event = events[0]
        if not creation_event:
            return processes
        if creation_event.process:
            #all_processes = [event.process for event in events if event.process]
            #all_processes = list(set(all_processes))
            #processes.append(creation_event.process)
            creation_event.follow_process_chain_beyond_workflow(processes, all_events)

    def value_flow_going_forward_reorganized(self):
        #import pdb; pdb.set_trace()
        in_out = self.value_flow_going_forward()
        processes = []
        save_process = None
        new_process = None
        for index, io in enumerate(in_out):
            item_process = save_process
            if io.__class__.__name__ == "EconomicEvent":
                item_process = io.process
            elif io.__class__.__name__ == "Process":
                item_process = io
            if item_process:
                if item_process != save_process:
                    if new_process:
                        processes.append(new_process)
                    new_process = item_process
                    new_process.input_events = []
                    new_process.output_events = []
                    save_process = new_process
            if io.__class__.__name__ == "EconomicEvent":
                if io.event_type.relationship == "out":
                    new_process.output_events.append(io)
                else:
                    new_process.input_events.append(io)
        if new_process:
            processes.append(new_process)
        return processes

    def form_prefix(self):
        return "-".join(["RES", str(self.id)])

    def consumption_event_form(self):        
        from valuenetwork.valueaccounting.forms import InputEventForm
        prefix=self.form_prefix()
        qty_help = " ".join(["unit:", self.unit_of_quantity().abbrev, ", up to 2 decimal places"])
        return InputEventForm(qty_help=qty_help, prefix=prefix)

    def use_event_form(self, data=None):        
        from valuenetwork.valueaccounting.forms import InputEventForm
        prefix=self.form_prefix()
        unit = self.resource_type.directional_unit("use")
        qty_help = " ".join(["unit:", unit.abbrev, ", up to 2 decimal places"])
        return InputEventForm(qty_help=qty_help, prefix=prefix, data=data)
        
    def cite_event_form(self, data=None):        
        from valuenetwork.valueaccounting.forms import InputEventForm
        prefix=self.form_prefix()
        unit = self.resource_type.directional_unit("cite")
        qty_help = " ".join(["unit:", unit.abbrev, ", up to 2 decimal places"])
        return InputEventForm(qty_help=qty_help, prefix=prefix, data=data)
            
    def input_event_form(self, data=None):
        from valuenetwork.valueaccounting.forms import InputEventForm
        prefix=self.form_prefix()
        qty_help = " ".join(["unit:", self.unit_of_quantity().abbrev, ", up to 2 decimal places"])
        return InputEventForm(qty_help=qty_help, prefix=prefix, data=data)
            
    def owner(self): #returns first owner
        owner_roles = self.agent_resource_roles.filter(role__is_owner=True)
        if owner_roles:
            return owner_roles[0].agent
        return None
             
    def all_owners(self):
        owner_assns = self.agent_resource_roles.filter(role__is_owner=True)
        owners = []
        for own in owner_assns:
            owners.append(own.agent.nick)
        return owners
           
    def revert_to_previous_stage(self):
        #import pdb; pdb.set_trace()
        current_stage = self.stage
        cts, inheritance = self.resource_type.staged_commitment_type_sequence()
        for ct in cts:
            if ct.stage == current_stage:
                break
            prev_stage = ct.stage
        self.stage = prev_stage
        self.save()
        return prev_stage


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
    value_per_unit = models.DecimalField(_('value per unit'), max_digits=8, decimal_places=2, 
        default=Decimal("0.0"))
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
        average = str((sum(scores) / len(scores)).quantize(Decimal('.01'), rounding=ROUND_HALF_UP))
        return "".join([
            "Min: ", str(min(scores).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)), 
            ", Average: ", average, 
            ", Max: ", str(max(scores).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)),
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
    is_account = models.BooleanField(_('is account'), default=False)
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
                
    def follow_stage_chain_beyond_workflow(self, chain):
        #import pdb; pdb.set_trace()
        chain.append(self)
        if self.event_type.is_change_related():
            if self.event_type.relationship == "out":
                next_in_chain = self.resource_type.wanting_process_type_relationships_for_stage(self.stage)
            if self.event_type.relationship == "in":
                next_in_chain = ProcessTypeResourceType.objects.filter(
                    resource_type=self.resource_type,
                    stage=self.process_type,
                    event_type__resource_effect="~>")
            if next_in_chain:
                next_in_chain[0].follow_stage_chain_beyond_workflow(chain)
                    
    def create_commitment_for_process(self, process, user, inheritance):
        #pr changed
        if self.event_type.relationship == "out":
            due_date = process.end_date
        else:
            due_date = process.start_date
        resource_type = self.resource_type
        #todo dhen: this is where species would be used
        if inheritance:
            if resource_type == inheritance.parent:
                resource_type = inheritance.substitute(resource_type)
        unit = self.resource_type.directional_unit(self.event_type.relationship)
        commitment = Commitment(
            process=process,
            stage=self.stage,
            state=self.state,
            description=self.description,
            context_agent=process.context_agent,
            event_type=self.event_type,
            resource_type=resource_type,
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
            description=self.description,
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

    def processes_with_expenses(self, start=None, end=None):
        #import pdb; pdb.set_trace()
        et_exp = EventType.objects.get(name="Process Expense")
        if start and end:
            procs = [exp.process for exp in EconomicEvent.objects.filter(event_type=et_exp).filter(process__isnull=False).filter(event_date__range=[start, end])]
        else:
            procs = [exp.process for exp in EconomicEvent.objects.filter(event_type=et_exp).filter(process__isnull=False)]
        return list(set(procs))

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
        limit_choices_to={"agent_type__is_context": True,},
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

    def shorter_label(self):
        return " ".join([
            self.name,
            self.start_date.strftime('%Y-%m-%d'),
            "to",
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
            return self.context_agent.default_agent()
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
            
    def production_quantity(self):
        return sum(pe.quantity for pe in self.production_events())

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
            
    def uncommitted_process_expense_events(self):
        return self.events.filter(
            event_type__relationship='payexpense',
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
        for ct in cts:
            if ct.order_item:
                return ct
        if cts:
            return cts[0]
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
        for ie in self.incoming_events():
            if ie.resource:
                for evt in ie.resource.producing_events():
                    if evt.process:
                        if evt.process != self:
                            if evt.process not in answer:
                                answer.append(evt.process)
        return answer
        
    def previous_processes_for_order(self, order):
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
                
    def all_previous_processes_for_order(self, order, ordered_processes, visited, depth):
        #import pdb; pdb.set_trace()
        self.depth = depth * 2
        ordered_processes.append(self)
        output = self.main_outgoing_commitment()
        if not output:
            return []
        depth = depth + 1
        if output.cycle_id() not in visited:
            visited.append(output.cycle_id())
            for process in self.previous_processes_for_order(order):
                process.all_previous_processes_for_order(order, ordered_processes, visited, depth)

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
        for oe in self.production_events():
            rt = oe.resource_type
            if oe.cycle_id() not in input_ids:
                if oe.resource:
                    for evt in oe.resource.all_usage_events():
                        if evt.process:
                            if evt.process != self:
                                if evt.process not in answer:
                                    answer.append(evt.process)
        return answer
        
    def next_processes_for_order(self, order):
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
            description,
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
            description=description,
            #Todo: apply selected_context_agent here? Dnly if inheritance?
            #or has that already been set on the process in explode_demands?
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
                description="",
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
                description="",
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
                description="",
                unit=next_commitment.unit_of_quantity, 
                user=user,
                stage=stage,
            )
            
    def change_context_agent(self, context_agent):
        #import pdb; pdb.set_trace()
        self.context_agent = context_agent
        self.save()
        for commit in self.commitments.all():
            commit.context_agent = context_agent
            commit.save()
        for event in self.events.all():
            event.context_agent = context_agent
            event.save()

    def explode_demands(self, demand, user, visited, inheritance):
        """This method assumes the output commitment from this process 

            has already been created.

        """
        #import pdb; pdb.set_trace()
        #todo pr: may need get and use RecipeInheritance object
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
                multiplier = output.quantity 
                if output.process:
                    if output.process.process_type:
                        main_ptr = output.process.process_type.main_produced_resource_type_relationship()
                        if main_ptr:
                            if main_ptr.quantity:
                                multiplier = output.quantity / main_ptr.quantity
                qty = (multiplier * ptrt.quantity).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
                #todo: must consider ratio of PT output qty to PT input qty
            #pr changed
            resource_type = ptrt.resource_type
            #todo dhen: this is where species would be used
            if inheritance:
                if resource_type == inheritance.parent:
                    resource_type = inheritance.substitute(resource_type)
                else:
                    resource_class = output.resource_type.resource_class
                    candidate = resource_type.child_of_class(resource_class)
                    if candidate:
                        resource_type = candidate
            #Todo: apply selected_context_agent here? Dnly if inheritance?
            commitment = self.add_commitment(
                resource_type=resource_type,
                demand=demand,
                description=ptrt.description or "",
                order_item=order_item,
                stage=ptrt.stage,
                state=ptrt.state,
                quantity=qty,
                event_type=ptrt.event_type,
                unit=resource_type.directional_unit(ptrt.event_type.relationship),
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
                    #pr changed
                    stage = commitment.stage
                    state = commitment.state
                    pptr, inheritance = resource_type.main_producing_process_type_relationship(stage=stage, state=state)
                    if pptr:
                        resource_type = pptr.resource_type
                        #todo dhen: this is where species would be used? Or not?
                        if inheritance:
                            if resource_type == inheritance.parent:
                                resource_type = inheritance.substitute(resource_type)
                        next_pt = pptr.process_type
                        start_date = self.start_date - datetime.timedelta(minutes=next_pt.estimated_duration)
                        next_process = Process(          
                            name=next_pt.name,
                            notes=next_pt.description or "",
                            process_type=next_pt,
                            process_pattern=next_pt.process_pattern,
                            #Todo: apply selected_context_agent here? Dnly if inheritance?
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
                            #todo: this makes no sense, why did I do that?
                            #temporary insanity or some reason that escapes me now?
                            #ps. prior to this commented-out code, it was
                            #qty = qty_to_explode * pptr.quantity
                            #I did this when making that salsa recipe work.
                            #2014-11-05
                            #if not multiplier:
                            #    multiplier = pptr.quantity
                            #qty = (qty_to_explode * multiplier).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
                            qty = qty_to_explode
                        #todo: must consider ratio of PT output qty to PT input qty
                        #Todo: apply selected_context_agent here? Dnly if inheritance?
                        next_commitment = next_process.add_commitment(
                            resource_type=resource_type,
                            stage=pptr.stage,
                            state=pptr.state,
                            demand=demand,
                            order_item=order_item,
                            quantity=qty,
                            event_type=pptr.event_type,
                            unit=resource_type.unit,
                            description=pptr.description or "",
                            user=user,
                        )
                        #todo pr: may need pass RecipeInheritance object
                        next_process.explode_demands(demand, user, visited, inheritance)

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
        return WorkflowProcessForm(prefix=str(self.id),initial=init, order_item=self.order_item())
        
    def roll_up_value(self, path, depth, visited):
        #import pdb; pdb.set_trace()
        #Value_per_unit will be the result of this method.
        depth += 1
        self.depth = depth
        #self.explanation = "Value per unit consists of all the input values on the next level"
        path.append(self)
        process_value = Decimal("0.0")
        #Values of all of the inputs will be added to this list.
        values = []
        citations = []
        production_value = Decimal("0.0")

        production_qty = self.production_quantity()
        if production_qty:
            inputs = self.incoming_events()
            for ip in inputs:
                #Work contributions use resource_type.value_per_unit
                if ip.event_type.relationship == "work":
                    ip.value = ip.quantity * ip.value_per_unit()
                    ip.save()
                    process_value += ip.value
                    ip.depth = depth
                    path.append(ip)
                #Use contributions use resource value_per_unit_of_use.
                elif ip.event_type.relationship == "use":
                    if ip.resource:
                        ip.value = ip.quantity * ip.resource.value_per_unit_of_use
                        ip.save()
                        process_value += ip.value
                        ip.resource.roll_up_value(path, depth, visited)
                        ip.depth = depth
                        path.append(ip)
                #Consume contributions use resource rolled up value_per_unit
                elif ip.event_type.relationship == "consume" or ip.event_type.name == "To Be Changed":
                    ip.depth = depth
                    path.append(ip)
                    value_per_unit = ip.resource.roll_up_value(path, depth, visited)
                    ip.value = ip.quantity * value_per_unit
                    ip.save()
                    process_value += ip.value
                #Citations valued later, after all other inputs added up
                elif ip.event_type.relationship == "cite":
                    ip.depth = depth
                    path.append(ip)
                    if ip.resource_type.unit_of_use:
                        if ip.resource_type.unit_of_use.unit_type == "percent":
                            citations.append(ip)
                    else:
                        ip.value = ip.quantity
                    if ip.resource:
                        ip.resource.roll_up_value(path, depth, visited)
        if process_value:
            #These citations use percentage of the sum of other input values.
            for c in citations:
                percentage = c.quantity / 100
                c.value = process_value * percentage
                c.save()
            for c in citations:
                process_value += c.value
        return process_value


    def compute_income_shares(self, order_item, quantity, value, events, visited):
        #This method assumes that self.roll_up_value has been run,
        #and all contribution events have been valued.
        #print "running quantity:", quantity, "running value:", value
        #import pdb; pdb.set_trace()
        if self not in visited:
            visited.add(self)
            if quantity:
                #todo: how will this work for >1 processes producing the same resource?
                #what will happen to the shares of the inputs of the later processes?
                production_events = self.production_events()
                produced_qty = sum(pe.quantity for pe in production_events)
                distro_fraction = 1
                distro_qty = quantity
                if produced_qty > quantity:
                    distro_fraction = quantity / produced_qty
                    quantity = Decimal("0.0")
                elif produced_qty <= quantity:
                    distro_qty = produced_qty
                    quantity -= produced_qty
                for pe in production_events:
                    pe.share = pe.quantity * distro_fraction
                    events.append(pe)
                inputs = self.incoming_events()
                for ip in inputs:
                    #we assume here that work events are contributions
                    if ip.event_type.relationship == "work":
                        ip.share = ip.value * distro_fraction
                        events.append(ip)
                        #print ip.id, ip, ip.share
                        #print "----Event.share:", ip.share, "= Event.value:", ip.value, "* distro_fraction:", distro_fraction
                    elif ip.event_type.relationship == "use":
                        #use events are not contributions, but their resources may have contributions
                        if ip.resource:
                            ip_value = ip.value * distro_fraction
                            if ip_value:
                                d_qty = ip_value / value
                                ip.resource.compute_income_shares(d_qty, ip_value, events, visited) 
                    elif ip.event_type.relationship == "consume" or ip.event_type.name == "To Be Changed":
                        #consume events are not contributions, but their resources may have contributions
                        ip_value = ip.value * distro_fraction
                        #if ip.resource.id == 98:
                        #    import pdb; pdb.set_trace()
                        if ip_value:
                            d_qty = ip.quantity * distro_fraction
                            #print "consumption:", ip.id, ip, "ip.value:", ip.value
                            #print "----value:", ip_value, "d_qty:", d_qty, "distro_fraction:", distro_fraction
                            ip.resource.compute_income_shares(d_qty, ip_value, events, visited)
                    elif ip.event_type.relationship == "cite":
                        #import pdb; pdb.set_trace()   
                        #citation events are not contributions, but their resources may have contributions
                        ip_value = ip.value * distro_fraction
                        if ip_value:
                            d_qty = ip_value / value
                            #print "citation:", ip.id, ip, "ip.value:", ip.value
                            #print "----value:", ip_value, "d_qty:", d_qty, "distro_fraction:", distro_fraction
                            ip.resource.compute_income_shares(d_qty, ip_value, events, visited)
    

class ExchangeManager(models.Manager):

    def financial_contributions(self, start=None, end=None):
        #import pdb; pdb.set_trace()
        if start and end:
             exchanges = Exchange.objects.filter(
                Q(use_case__identifier="cash_contr")|
                Q(use_case__identifier="purch_contr")|
                Q(use_case__identifier="exp_contr")).filter(start_date__range=[start, end])
        else:
            exchanges = Exchange.objects.filter(
                Q(use_case__identifier="cash_contr")|
                Q(use_case__identifier="purch_contr")|
                Q(use_case__identifier="exp_contr"))
        processes_with_expenses = Process.objects.processes_with_expenses(start, end)
        both = list(exchanges)
        both.extend(processes_with_expenses)
        both.sort(lambda x, y: cmp(y.start_date, x.start_date))
        return both
        
    def sales_and_distributions(self):
        return Exchange.objects.filter(
            Q(use_case__identifier="sale")|
            Q(use_case__identifier="distribution"))
            
    def material_contributions(self):
        return Exchange.objects.filter(use_case__identifier="res_contr")

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
        limit_choices_to={"agent_type__is_context": True,},
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
        related_name="exchanges", verbose_name=_('order'))
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
            
    def class_label(self):
        return "Exchange"

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

    def shipment_commitments(self):
        return self.commitments.filter(
            event_type__relationship='shipment')
            
    def cash_receipt_commitments(self):
        return self.commitments.filter(
            event_type__name='Cash Receipt')
            
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
            
    def shipment_events_no_commitment(self):
        return self.events.filter(event_type__relationship='shipment').filter(commitment=None)
            
    def distribution_events(self):
        return self.events.filter(
            event_type__relationship='distribute')
            
    def sorted_events(self):
        events = self.events.all().order_by("event_type__name")
        return events
        
    def compute_income_shares(self, trigger_event, quantity, value, events, visited):
        #import pdb; pdb.set_trace()
        if self not in visited:
            visited.add(self)
            receipts = self.receipt_events()
            trigger_fraction = 1
            if receipts.count() > 1:
                rsum = sum(r.value for r in receipts)
                trigger_fraction = trigger_event.value / rsum
            payments = self.payment_events()
            share =  quantity / trigger_event.quantity
            if payments.count() == 1:
                evt = payments[0]
                evt.share = evt.quantity * share
                events.append(evt)
            elif payments.count() > 1:
                total = sum(p.quantity for p in payments)
                for evt in payments:
                    fraction = evt.quantity / total
                    evt.share = evt.quantity * share * fraction * trigger_fraction
                    events.append(evt)
            for evt in self.work_events():
                evt.share = evt.quantity * share * trigger_fraction
                events.append(evt)


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
        limit_choices_to={"agent_type__is_context": True,},
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
        abbrev = ""
        if self.event_type.relationship == "cite":
            quantity_string = ""
        else:
            quantity_string = str(self.quantity)
            if self.unit_of_quantity:
                abbrev = self.unit_of_quantity.abbrev
        resource_name = ""
        process_name = ""
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

    def shorter_label(self):
        quantity_string = str(self.quantity)
        resource_name = ""
        abbrev = ""
        if self.unit_of_quantity:
           abbrev = self.unit_of_quantity.abbrev
        if self.resource_type:
            resource_name = self.resource_type.name
        return ' '.join([
            quantity_string,
            abbrev,
            resource_name,         
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
        #todo: figure out how to allow for workflow stream resources
        #easy way: edit previous change event
        #hard way: a new change event (or is that really a change event?)
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
        if self.resource_type.inventory_rule == "yes":
            from valuenetwork.valueaccounting.forms import CreateEconomicResourceForm
            init = {
                "quantity": self.quantity,
                "unit_of_quantity": self.resource_type.unit,
            }
            return CreateEconomicResourceForm(prefix=self.form_prefix(), initial=init, data=data)
        else:
            from valuenetwork.valueaccounting.forms import UninventoriedProductionEventForm
            init = {
                #"from_agent": self.from_agent,
                "quantity": self.quantity,
            }
            unit = self.resource_type.unit
            qty_help = ""
            if unit:
                unit_string = unit.abbrev
                qty_help = " ".join(["unit:", unit.abbrev, ", up to 2 decimal places"])
            return UninventoriedProductionEventForm(qty_help=qty_help, prefix=self.form_prefix(), initial=init, data=data)
        
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
            
    def resources_ready_to_be_changed(self):
        #import pdb; pdb.set_trace()
        resources = []
        if self.event_type.stage_to_be_changed():
            if self.resource_type.substitutable:
                resources = EconomicResource.objects.filter(
                    resource_type=self.resource_type,
                    stage=self.stage)
            else:
                resources = EconomicResource.objects.filter(
                    resource_type=self.resource_type,
                    stage=self.stage,
                    order_item=self.order_item)
        return resources
        
    def fulfilling_events(self):
        return self.fulfillment_events.all()    
        
    #def fulfilling_shipment_events(self):
    #    return self.fulfillment_events.filter(event_type__name="Shipment")
     
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
        
    def is_fulfilled(self):
        if self.unfilled_quantity():
            return False
        return True

    def onhand(self):
        answer = []
        rt = self.resource_type
        if self.stage:
            resources = EconomicResource.goods.filter(
                stage=self.stage,
                resource_type=rt)
        else:
            resources = EconomicResource.goods.filter(resource_type=rt)
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
        if not rt.substitutable:
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
        
    def is_change_related(self):
        return self.event_type.is_change_related()
            
    def applies_stage(self):
        return self.event_type.applies_stage()
        
    def changes_stage(self):
        return self.event_type.changes_stage()

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

    def generate_producing_process(self, user, visited, inheritance=None, explode=False):
        
        """ This method is usually used in recipe explosions.
        
            inheritance is optional, can be positional or keyword arg. It means 
            the recipe in use was inherited from a parent.
            explode is also optional. If used by a caller, and inheritance is not used,
            explode must be a keyword arg.
        """
        #import pdb; pdb.set_trace()
        qty_required = self.quantity
        rt = self.resource_type
        should_net = False
        if self.order:
            if self.order.order_type == "customer":
                should_net = True
        else:
            should_net = True
        if should_net:
            qty_required = self.net()
        process=None
        if qty_required:
            #pr changed
            #import pdb; pdb.set_trace()
            ptrt, inheritance = rt.main_producing_process_type_relationship(stage=self.stage, state=self.state)
            if ptrt:
                resource_type = self.resource_type
                if self.event_type.relationship == "shipment":
                    producing_commitment = Commitment(
                        resource_type=resource_type,
                        independent_demand=self.independent_demand,
                        order_item=self,
                        event_type=ptrt.event_type,
                        context_agent=self.context_agent,
                        stage=ptrt.stage,
                        state=ptrt.state,
                        quantity=self.quantity,
                        unit_of_quantity=resource_type.unit,
                        due_date=self.due_date,
                        created_by=user)
                    producing_commitment.save()
                else:
                    producing_commitment = self
                pt = ptrt.process_type
                start_date = self.due_date - datetime.timedelta(minutes=pt.estimated_duration)
                process = Process(
                    name=pt.name,
                    notes=pt.description or "",
                    process_type=pt,
                    process_pattern=pt.process_pattern,
                    #Todo: apply selected_context_agent here?
                    #only if inheritance?
                    context_agent=pt.context_agent,
                    url=pt.url,
                    end_date=self.due_date,
                    start_date=start_date,
                    created_by=user,
                )
                process.save()
                producing_commitment.process=process
                producing_commitment.save()
                if explode:
                    demand = self.independent_demand
                    process.explode_demands(demand, user, visited, inheritance)
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
        if self.stage:
            producers = self.resource_type.producing_commitments().filter(stage=self.stage).exclude(id=self.id)
        else:
            producers = self.resource_type.producing_commitments().exclude(id=self.id)
        #todo: this shd just be a filter, but need to test the change, so do later
        return [ct for ct in producers if ct.order_item == self.order_item]
        
    def active_producing_commitments(self):
        if self.stage:
            return self.resource_type.commitments.filter(
                event_type__relationship='out',
                stage=self.stage,
                process__finished=False)
        else:
            return self.resource_type.commitments.filter(
                event_type__relationship='out',
                process__finished=False)

    def scheduled_receipts(self):
        #import pdb; pdb.set_trace()
        rt = self.resource_type
        if rt.substitutable:
            return self.active_producing_commitments()
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

    def all_processes_in_my_order_item(self):
        ordered_processes = []
        if self.order_item:
            commitments = Commitment.objects.filter(order_item=self.order_item)
            for c in commitments:
                if c.process:
                    ordered_processes.append(c.process)
            #import pdb; pdb.set_trace()
            if ordered_processes:
                ordered_processes = list(set(ordered_processes))
                ordered_processes = sorted(ordered_processes, key=attrgetter('end_date'))
                ordered_processes = sorted(ordered_processes, key=attrgetter('start_date'))
        return ordered_processes
        
    def last_process_in_my_order_item(self):
        processes = self.all_processes_in_my_order_item()
        if processes:
            return processes[-1]
        else:
            return None
         
    def is_order_item(self):
        if self.order:
            return True
        else:
            return False
            
    def is_workflow_order_item(self):
        if self.process and self.order:
            return self.process.is_staged()
        else:
            return False
            
    def process_types(self):
        pts = []
        for process in self.all_processes_in_my_order_item():
            if process.process_type:
                pts.append(process.process_type)
        return list(set(pts))
        
    def available_workflow_process_types(self):
        all_pts = ProcessType.objects.workflow_process_types()
        my_pts = self.process_types()
        available_pt_ids = []
        for pt in all_pts:
            if pt not in my_pts:
                available_pt_ids.append(pt.id)
        return ProcessType.objects.filter(id__in=available_pt_ids)
        
    def workflow_quantity(self):
        if self.is_workflow_order_item():
            return self.quantity
        else:
            return None
        
    def workflow_unit(self):
        if self.is_workflow_order_item():
            return self.unit_of_quantity
        else:
            return None  
    
    def change_commitment_quantities(self, qty):
        #import pdb; pdb.set_trace()
        if self.is_workflow_order_item():
            processes = self.process_chain()
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
            
    def change_workflow_project(self, project):
        #import pdb; pdb.set_trace()
        if self.is_workflow_order_item():
            processes = self.process_chain()
            for process in processes:
                #process.context_agent = project
                #process.save()
                process.change_context_agent(context_agent=project)
        return self
        
    def adjust_workflow_commitments_process_added(self, process, user): #process added to the end of the order item
        #import pdb; pdb.set_trace()
        last_process = self.last_process_in_my_order_item() 
        process.add_stream_commitments(last_process=last_process, user=user)
        last_commitment = last_process.main_outgoing_commitment()
        last_commitment.remove_order()
        return self
        
    def adjust_workflow_commitments_process_inserted(self, process, next_process, user):
        #import pdb; pdb.set_trace()
        all_procs = self.all_processes_in_my_order_item()
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
        all_procs = self.all_processes_in_my_order_item()
        process_index = all_procs.index(process)
        last_process = None
        next_commitment = None
        if process_index > 0:
            last_process = all_procs[process_index - 1]
        if process == self.last_process_in_my_order_item():
            if last_process:
                last_commitment = last_process.main_outgoing_commitment()
                last_commitment.order = self.order
                last_commitment.save()
        else:
            next_process = all_procs[process_index + 1]
            next_commitment = next_process.to_be_changed_requirements()[0]
        if last_process and next_commitment:    
            next_commitment.update_stage(last_process.process_type)
        return None
        
    def compute_income_fractions(self):
        """Returns a list of contribution events for an order_item, 
        
        where each event has event.share and event.fraction.
        event.share is that event's share based on its 
        proportional contribution to the order_item's resource value.
        event.fraction is that event's fraction of the total shares.
        
        """
        events = self.fulfilling_events()
        resources = []
        resource = None
        shares = []
        total = 0
        for event in events:
            if event.resource:
                if event.resource not in resources:
                    resources.append(event.resource)
        if resources:
            if len(resources) == 1:
                resource = resources[0]
            else:
                #does not handle different resources per order_item yet.
                msg = " ".join([self.__unicode__(), "has different resources, not handled yet."])
                assert False, msg
        if resource:
            shares = self.compute_income_fractions_for_resource(resource)
        else:
            shares = self.compute_income_fractions_for_process()
        if shares:
            total = sum(s.share for s in shares)
        if total:
            for s in shares:
                s.fraction = s.share / total
        #import pdb; pdb.set_trace()
        #print "total shares:", total
        return shares
        
    def compute_income_fractions_for_resource(self, resource):
        #print "*** rollup up resource value"
        visited = set()
        path = []
        depth = 0
        value_per_unit = resource.roll_up_value(path, depth, visited)
        #print "resource value_per_unit:", value_per_unit
        value = self.quantity * value_per_unit
        visited = set()
        #print "*** computing income shares"
        shares = []
        #import pdb; pdb.set_trace()
        resource.compute_income_shares(self.quantity, value, shares, visited)
        return shares
        
    def compute_income_fractions_for_process(self):
        shares = []
        visited = set()
        path = []
        depth = 0
        p = self.process
        if p:
            #print "*** rollup up process value"
            value = p.roll_up_value(path, depth, visited)
            #print "processvalue:", value
            visited = set()
            #print "*** computing income shares"
            #import pdb; pdb.set_trace()
            p.compute_income_shares(self, self.quantity, value, shares, visited)
        return shares


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
        limit_choices_to={"agent_type__is_context": True,},
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
            prev_context_agent = self.context_agent
            prev_resource_type = self.resource_type
            prev_event_type = self.event_type
            prev = EconomicEvent.objects.get(pk=self.pk)
            if prev.quantity != self.quantity:
                delta = self.quantity - prev.quantity
            if prev.from_agent != self.from_agent:
                agent_change = True
                prev_agent = prev.from_agent
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
                #todo ART: bugs in this code cause dup records
                if self.event_type.relationship == "work" or self.event_type.related_to == "agent":
                    try:
                        art, created = AgentResourceType.objects.get_or_create(
                            agent=agent,
                            resource_type=resource_type,
                            event_type=event_type)
                    except:
                        #todo: this shd not happen, but it does...
                        arts = AgentResourceType.objects.filter(
                            agent=agent,
                            resource_type=resource_type,
                            event_type=event_type)
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
        if self.is_contribution:
            agent = self.from_agent
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
        
    def seniority(self):
        return (datetime.date.today() - self.event_date).days
        
    def value_per_unit(self):
        if self.resource:
            return self.resource.value_per_unit
        if self.from_agent:
            arts = AgentResourceType.objects.filter(
                agent=self.from_agent,
                resource_type=self.resource_type,
                event_type=self.event_type)
            if arts:
                art = arts[0]
                if art.value_per_unit:
                    return art.value_per_unit
        return self.resource_type.value_per_unit
       
    def value_explanation(self):
        if self.process:
            p_qty = self.process.production_quantity()
        if self.event_type.relationship == "work":
            vpu = self.resource_type.value_per_unit
            value = vpu * self.quantity
            if p_qty:
                value = value / p_qty
                return " ".join([
                    "Value per parent unit:", str(value),
                    "= Resource Type value per unit:", str(vpu),
                    "* Event quantity:", str(self.quantity),
                    "/ Process production qty:", str(p_qty),
                    ])
            else:
                return " ".join([
                    "Value:", str(value),
                    "= Resource Type value per unit:", str(vpu),
                    "* Event quantity:", str(self.quantity)
                    ])
        elif self.event_type.relationship == "use":
            vpu = self.resource.value_per_unit_of_use
            value = vpu * self.quantity
            if p_qty:
                value = value / p_qty
                return " ".join([
                    "Value per parent unit:", str(value),
                    "= Resource value per unit of use:", str(vpu),
                    "* Event quantity:", str(self.quantity),
                    "/ Process production qty:", str(p_qty),
                    ])
            else:
                return " ".join([
                    "Value:", str(value),
                    "= Resource value per unit of use:", str(vpu),
                    "* Event quantity:", str(self.quantity)
                    ])
        elif self.event_type.relationship == "consume":
            vpu = self.resource.value_per_unit
            value = vpu * self.quantity
            if p_qty:
                value = value / p_qty
                return " ".join([
                    "Value per parent unit:", str(value),
                    "= Resource value per unit:", str(vpu),
                    "* Event quantity:", str(self.quantity),
                    "/ Process production qty:", str(p_qty),
                    ])
            else:
                return " ".join([
                    "Value:", str(value),
                    "= Resource value per unit:", str(vpu),
                    "* Event quantity:", str(self.quantity)
                    ])
        elif self.event_type.relationship == "cite":
            percent = False
            if self.resource_type.unit_of_use:
                if self.resource_type.unit_of_use.unit_type == "percent":
                    percent = True
            if percent:
                return "".join([
                    "Value per parent unit: ", str(self.value),
                    " = ", str(self.quantity),
                    "% of sum of the values of the other inputs to the process",
                    ])
            else:
                return " ".join([
                    "Value:", str(self.value),
                    "= Event quantity:", str(self.quantity),
                    ])
        elif self.event_type.relationship == "resource":
            vpu = self.resource.value_per_unit
            value = vpu * self.quantity
            return " ".join([
                "Value:", str(value),
                "= Resource value per unit:", str(vpu),
                "* Event quantity:", str(self.quantity)
                ])
        elif self.event_type.relationship == "receive":
            vpu = self.resource.value_per_unit
            value = vpu * self.quantity
            return " ".join([
                "Value:", str(value),
                "= Resource value per unit:", str(vpu),
                "* Event quantity:", str(self.quantity)
                ])
        elif self.event_type.relationship == "out":
            return "Value per unit is composed of the value of the inputs on the next level:"
        return ""
        
    def roll_up_value(self, path, depth, visited):
        #rollup stage change
        if self.commitment:
            stage = self.commitment.stage
            if stage:
                self.resource.historical_stage = stage
        return self.resource.roll_up_value(path, depth, visited)
        
    def claims(self):
        claim_events = self.claim_events.all()
        claims = [ce.claim for ce in claim_events]
        return list(set(claims))    
         
    def outstanding_claims(self):
        claim_events = self.claim_events.all()
        claims = [ce.claim for ce in claim_events if ce.claim.value > Decimal("0.0")]
        return list(set(claims))
        
    def created_claim(self):
        cc = None
        claim_events = self.claim_events.all()
        for ce in claim_events:
            if ce.event_effect == "+":
                cc = ce.claim
                cc.claim_event = ce
                break
        return cc
        
    def outstanding_claims_for_bucket_rule(self, bucket_rule):
        claims = self.outstanding_claims()
        return [claim for claim in claims if claim.value_equation_bucket_rule==bucket_rule]
               
    def create_claim(self, bucket_rule):
        #import pdb; pdb.set_trace()
        #claims = self.outstanding_claims_for_bucket_rule(bucket_rule)
        #if claims:
        if self.created_claim():
            return self.created_claim()
        else:
            order = None
            if self.commitment:
                order = self.commitment.independent_demand
            else:
                if self.process:
                    order = self.process.independent_demand()
            claim = Claim(
                order=order,
                value_equation_bucket_rule=bucket_rule,
                claim_date=datetime.date.today(),
                has_agent=self.from_agent,
                against_agent=self.to_agent,
                context_agent=self.context_agent,
                unit_of_value=self.unit_of_value,
                claim_creation_equation=bucket_rule.claim_creation_equation,
            )
            claim.save()
            claim_event = ClaimEvent(
                event=self,
                claim=claim,
                claim_event_date=datetime.date.today(),
                value=bucket_rule.compute_claim_value(self),
                unit_of_value=self.unit_of_value,
                event_effect="+",
            )
            claim_event.save()
            claim_event.update_claim()
            return claim
               
    def get_unsaved_contribution_claim(self, bucket_rule):
        #import pdb; pdb.set_trace()
        claim = self.created_claim()
        if claim:
            return claim
        else:
            #order = None
            #if self.commitment:
            #    order = self.commitment.independent_demand
            #else:
            #    if self.process:
            #        order = self.process.independent_demand()
            value = bucket_rule.compute_claim_value(self)
            claim = Claim(
                #order=order,
                value_equation_bucket_rule=bucket_rule,
                claim_date=datetime.date.today(),
                has_agent=self.from_agent,
                against_agent=self.to_agent,
                context_agent=self.context_agent,
                value=value,
                unit_of_value=self.unit_of_value,
                claim_creation_equation=bucket_rule.claim_creation_equation,
            )
            claim_event = ClaimEvent(
                event=self,
                claim=claim,
                claim_event_date=datetime.date.today(),
                value=value,
                unit_of_value=self.unit_of_value,
                event_effect="+",
            )
            claim.claim_event = claim_event
            return claim     
            
    def shorter_label(self):
        if self.unit_of_quantity:
            quantity_string = " ".join([str(self.quantity), self.unit_of_quantity.abbrev])
        else:
            quantity_string = str(self.quantity)
        from_agt = 'Unassigned'
        if self.from_agent:
            from_agt = self.from_agent.nick
        to_agt = 'Unassigned'
        if self.recipient():
            to_agt = self.recipient().nick
        return ' '.join([
            'from',
            from_agt,
            'to',
            to_agt,
            quantity_string,
        ])
        
    def default_agent(self):
        if self.context_agent:
            return self.context_agent.default_agent()
        return None 
        
    def cycle_id(self):
        stage_id = ""
        state_id = ""
        if self.resource:
            if self.resource.stage:
                stage_id = str(self.resource.stage.id)
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
            #rollup stage change
            #import pdb; pdb.set_trace()
            id_str = self.resource.identifier or str(self.resource.id)
            if self.commitment:
                stage = self.commitment.stage
                if stage:
                    resource_string = "@".join([resource_string, stage.name])
            resource_string = ": ".join([
                    resource_string,
                    id_str,
                ])
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
            str(self.quantity.quantize(Decimal('.01'), rounding=ROUND_HALF_UP)),
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
        
    def is_change_related(self):
        return self.event_type.is_change_related()
            
    def applies_stage(self):
        return self.event_type.applies_stage()
        
    def changes_stage(self):
        return self.event_type.changes_stage()
        
    def follow_process_chain_beyond_workflow(self, chain, all_events):
        #import pdb; pdb.set_trace()
        #todo: this was created for a DHen report 
        # but does not work yet because the converted data
        # has no commitments
        # Plus, it can't be tested and so probably won't work.
        if self.event_type.is_change_related():
            if self.process not in chain:
                chain.append(self.process)
                stage = self.process.process_type
                if stage:
                    if self.event_type.relationship == "out":
                        next_candidates = all_events.filter(
                            commitment__stage=stage,
                            event_type__relationship="in")
                        if next_candidates:
                            next_in_chain = next_candidates[0]
                    if self.event_type.relationship == "in":
                        next_candidates = self.process.events.filter(
                            resource_type=self.resource_type,
                            stage=stage,
                            event_type__relationship="out")
                    if next_in_chain:
                        next_in_chain[0].follow_stage_chain_beyond_workflow(chain)


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

        
PERCENTAGE_BEHAVIOR_CHOICES = (
    ('remaining', _('Remaining percentage')),
    ('straight', _('Straight percentage')),
)

class ValueEquation(models.Model):
    name = models.CharField(_('name'), max_length=255, blank=True)
    context_agent = models.ForeignKey(EconomicAgent,
        limit_choices_to={"agent_type__is_context": True,},
        related_name="value_equations", verbose_name=_('context agent'))  
    description = models.TextField(_('description'), null=True, blank=True)
    percentage_behavior = models.CharField(_('percentage behavior'), 
        max_length=12, choices=PERCENTAGE_BEHAVIOR_CHOICES, default='straight',
        help_text=_('Remaining percentage uses the % of the remaining amount to be distributed.  Straight percentage uses the % of the total distribution amount.'))
    live = models.BooleanField(_('live'), default=False,
        help_text=_("Make this value equation available for use in real distributions."))
    created_by = models.ForeignKey(User, verbose_name=_('created by'),
        related_name='value_equations_created', blank=True, null=True)
    created_date = models.DateField(auto_now_add=True, blank=True, null=True, editable=False)
    
    def __unicode__(self):
        return self.name
        
    @models.permalink
    def get_absolute_url(self):
        return ('edit_value_equation', (),
            { 'value_equation_id': str(self.id),})
            
    def is_deletable(self):
        if self.distributions.all():
            return False
        else:
            return True
            
    def run_value_equation_and_save(self, exchange, money_resource, amount_to_distribute, serialized_filters):
        #import pdb; pdb.set_trace()
        context_agent = exchange.context_agent
        distribution_events = self.run_value_equation(
            context_agent=context_agent, 
            amount_to_distribute=amount_to_distribute,
            serialized_filters=serialized_filters)
        #import pdb; pdb.set_trace()
        for event in distribution_events:
            event.exchange = exchange
            event.resource_type = money_resource.resource_type
            event.resource = money_resource
            event.unit_of_quantity = money_resource.unit_of_quantity
            event.save()
            #todo: will need to save new claims too
            for claim_event in event.new_claim_events:
                claim_event.claim.save()
                claim_event.event = event
                claim_event.save()
        return exchange
        
    def run_value_equation(self, amount_to_distribute, serialized_filters):
        #import pdb; pdb.set_trace()
        detail_sums = []
        claim_events = []
        contribution_events = []
        for bucket in self.buckets.all():
            #import pdb; pdb.set_trace()
            bucket_amount =  bucket.percentage * amount_to_distribute / 100
            amount = amount_to_distribute - bucket_amount
            if amount < 0:
                bucket_amount = bucket_amount - amount
            amount_distributed = 0
            if bucket_amount > 0:
                if bucket.distribution_agent:
                    sum_a = str(bucket.distribution_agent.id) + "~" + str(bucket_amount)
                    detail_sums.append(sum_a)
                    amount_distributed = bucket_amount
                else:
                    serialized_filter = serialized_filters.get(bucket.id)
                    if serialized_filter:
                        ces, contributions = bucket.run_bucket_value_equation(amount_to_distribute=bucket_amount, context_agent=self.context_agent, serialized_filter=serialized_filter)
                        for ce in ces:
                            detail_sums.append(str(ce.claim.has_agent.id) + "~" + str(ce.value))
                            amount_distributed += ce.value
                        claim_events.extend(ces)
                        contribution_events.extend(contributions)
            if self.percentage_behavior == "remaining":
                amount_to_distribute = amount_to_distribute - amount_distributed
        agent_amounts = {}
        for dtl in detail_sums:
            detail = dtl.split("~")
            if detail[0] in agent_amounts:
                amt = agent_amounts[detail[0]]
                agent_amounts[detail[0]] = amt + Decimal(detail[1])
            else:
                agent_amounts[detail[0]] = Decimal(detail[1])
        #import pdb; pdb.set_trace()
        et = EventType.objects.get(name='Distribution')
        distribution_events = []
        for agent_id in agent_amounts:   
            distribution = EconomicEvent(
                event_type = et,
                event_date = datetime.date.today(),
                from_agent = self.context_agent, 
                to_agent = EconomicAgent.objects.get(id=int(agent_id)),
                context_agent = self.context_agent,
                quantity = agent_amounts[agent_id].quantize(Decimal('.01'), rounding=ROUND_HALF_UP),
                is_contribution = False,
            )
            agent_claim_events = [ce for ce in claim_events if ce.claim.has_agent.id == int(agent_id)]
            for ce in agent_claim_events:
                ce.event = distribution
            distribution.new_claim_events = agent_claim_events
            distribution_events.append(distribution)
        #import pdb; pdb.set_trace()
        return distribution_events, contribution_events
        
class DistributionValueEquation(models.Model):
    '''
    Distribution itself is currently implemented using Exchange.  This is not totally correct from an REA point
    of view.  It groups events that apply to many earlier exchanges. If we were using subclasses, it might be that
    EconomicInteraction is the superclass of Process, Exchange, and Distribution.
    
    This class holds the remaining information for a Distribution.
    '''
    distribution_date = models.DateField(_('distribution date'))
    exchange = models.ForeignKey(Exchange,
        blank=True, null=True,
        verbose_name=_('distribution'), related_name='value equation')    
    value_equation_link = models.ForeignKey(ValueEquation,
        blank=True, null=True,
        verbose_name=_('value equation link'), related_name='distributions')
    value_equation_content = models.TextField(_('value equation formulas used'), null=True, blank=True)    

'''
class AgentValueEquation(models.Model):
    context_agent = models.ForeignKey(EconomicAgent,
        limit_choices_to={"agent_type__is_context": True,},
        related_name="value_equations", verbose_name=_('context agent'))  
    value_equation = models.ForeignKey(ValueEquation,
        verbose_name=_('value equation'), related_name='agents')
    created_by = models.ForeignKey(User, verbose_name=_('created by'),
        related_name='value_equations_assigned', blank=True, null=True)
    created_date = models.DateField(auto_now_add=True, blank=True, null=True, editable=False)     
    
    def __unicode__(self):
        return self.value_equation.name
'''

FILTER_METHOD_CHOICES = (
    ('order', _('Order')),
    ('shipment', _('Shipment or Delivery')),
    ('dates', _('Date range')),
)

class ValueEquationBucket(models.Model): 
    name = models.CharField(_('name'), max_length=32)
    sequence = models.IntegerField(_('sequence'), default=0)  
    value_equation = models.ForeignKey(ValueEquation,
        verbose_name=_('value equation'), related_name='buckets')
    filter_method =  models.CharField(_('filter method'), null=True, blank=True, 
        max_length=12, choices=FILTER_METHOD_CHOICES, default='dates')
    #filter_rule not used right now, leaving in just in case
    filter_rule = models.TextField(_('filter rule'), null=True, blank=True)
    percentage = models.IntegerField(_('bucket percentage'), null=True)    
    distribution_agent = models.ForeignKey(EconomicAgent,
        blank=True, null=True,
        related_name="value_equation_buckets", verbose_name=_('distribution agent'))     
    created_by = models.ForeignKey(User, verbose_name=_('created by'),
        related_name='buckets_created', blank=True, null=True, editable=False)
    changed_by = models.ForeignKey(User, verbose_name=_('changed by'),
        related_name='buckets_changed', blank=True, null=True, editable=False)
    created_date = models.DateField(auto_now_add=True, blank=True, null=True, editable=False)
    changed_date = models.DateField(auto_now=True, blank=True, null=True, editable=False)
    
    class Meta:
        ordering = ('sequence',)
        
    def __unicode__(self):
        return ' '.join([
            'Bucket',
            str(self.sequence),
            '-',
            str(self.percentage) + '%',
            '-',
            self.name,
        ])
        
    def run_bucket_value_equation(self, amount_to_distribute, context_agent, serialized_filter):
        #import pdb; pdb.set_trace()
        rules = self.bucket_rules.all()
        claims = []
        claim_events = []
        contribution_events = []
        for vebr in rules:
            vebr_claims, contributions = vebr.gather_claims(context_agent=context_agent, serialized_filter=serialized_filter)
            claims.extend(vebr_claims)
            vebr.calced_claims = vebr_claims
            contribution_events.extend(contributions)
        if claims:
            total_amount = 0
            for claim in claims:
                total_amount = total_amount + claim.share
            if total_amount > 0:
                portion_of_amount = amount_to_distribute / total_amount
            else:
                portion_of_amount = Decimal("0.0")
            #import pdb; pdb.set_trace()
            if self.value_equation.percentage_behavior == "remaining":
                if portion_of_amount > 1:
                    portion_of_amount = Decimal("1.0")
            #import pdb; pdb.set_trace()
            for vebr in rules:
                ces = vebr.create_distribution_claim_events(claims=vebr.calced_claims, portion_of_amount=portion_of_amount)
                claim_events.extend(ces)
        return claim_events, contribution_events
        
        
    def change_form(self):
        from valuenetwork.valueaccounting.forms import ValueEquationBucketForm
        return ValueEquationBucketForm(instance=self, prefix=str(self.id))
        
    def rule_form(self):
        from valuenetwork.valueaccounting.forms import ValueEquationBucketRuleForm
        return ValueEquationBucketRuleForm(prefix=str(self.id))
         
    def rule_filter_form(self):
        from valuenetwork.valueaccounting.forms import BucketRuleFilterSetForm
        ca = None
        pattern = None
        #import pdb; pdb.set_trace()
        if self.value_equation.context_agent:
            ca = self.value_equation.context_agent
        uc = UseCase.objects.get(identifier='val_equation')
        patterns = ProcessPattern.objects.usecase_patterns(use_case=uc)
        if patterns.count() > 0:
            pattern = patterns[0]
        return BucketRuleFilterSetForm(prefix=str(self.id), context_agent=ca, event_type=None, pattern=pattern)
        
    def filter_entry_form(self, data=None):
        #import pdb; pdb.set_trace()
        form = None
        if self.filter_method == "order":
            from valuenetwork.valueaccounting.forms import OrderMultiSelectForm
            if data == None:
                form = OrderMultiSelectForm(prefix=str(self.id), context_agent=self.value_equation.context_agent)
            else:
                form = OrderMultiSelectForm(prefix=str(self.id), context_agent=self.value_equation.context_agent, data=data)
        elif self.filter_method == "shipment":
            from valuenetwork.valueaccounting.forms import ShipmentMultiSelectForm
            if data == None:
                form = ShipmentMultiSelectForm(prefix=str(self.id), context_agent=self.value_equation.context_agent)
            else:
                form = ShipmentMultiSelectForm(prefix=str(self.id), context_agent=self.value_equation.context_agent, data=data)
        elif self.filter_method == "dates":
            from valuenetwork.valueaccounting.forms import DateRangeForm
            if data == None:
                form = DateRangeForm(prefix=str(self.id)) 
            else:
                form = DateRangeForm(prefix=str(self.id), data=data) 
        return form

        
DIVISION_RULE_CHOICES = (
    ('percentage', _('Percentage')),
    ('fifo', _('Oldest first')),
)

CLAIM_RULE_CHOICES = (
    ('debt-like', _('Until paid off')),
    ('equity-like', _('Forever')),
    ('once', _('One distribution')),
)

class ValueEquationBucketRule(models.Model): 
    value_equation_bucket = models.ForeignKey(ValueEquationBucket,
        verbose_name=_('value equation bucket'), related_name='bucket_rules')
    event_type = models.ForeignKey(EventType, 
        related_name="bucket_rules", verbose_name=_('event type')) 
    filter_rule = models.TextField(_('filter rule'), null=True, blank=True)
    #todo: thinking we can get rid of division_rule, see if we have requirement
    division_rule =  models.CharField(_('division rule'), 
        max_length=12, choices=DIVISION_RULE_CHOICES)
    claim_rule_type = models.CharField(_('claim rule type'), 
        max_length=12, choices=CLAIM_RULE_CHOICES)
    claim_creation_equation = models.TextField(_('claim creation equation'), 
        null=True, blank=True)
    created_by = models.ForeignKey(User, verbose_name=_('created by'),
        related_name='rules_created', blank=True, null=True, editable=False)
    changed_by = models.ForeignKey(User, verbose_name=_('changed by'),
        related_name='rules_changed', blank=True, null=True, editable=False)
    created_date = models.DateField(auto_now_add=True, blank=True, null=True, editable=False)
    changed_date = models.DateField(auto_now=True, blank=True, null=True, editable=False)    
    
    def __unicode__(self):
        return ' '.join([
            'rule for:',
            self.value_equation_bucket.__unicode__(),
            '-',
            self.event_type.name,
        ])

    def filter_rule_deserialized(self):
        from valuenetwork.valueaccounting.forms import BucketRuleFilterSetForm
        form = BucketRuleFilterSetForm(prefix=str(self.id), context_agent=None, event_type=None, pattern=None)
        #import pdb; pdb.set_trace()
        return form.deserialize(json=self.filter_rule)
        
    def gather_events(self, context_agent, serialized_filter):
        #import pdb; pdb.set_trace()
        json = self.filter_rule_deserialized()
        process_types = []
        resource_types = []
        if 'process_types' in json.keys():
            process_types = json['process_types']
        if 'resource_types' in json.keys():
            resource_types = json['resource_types']
        events = []
        filter = self.filter_rule_display_list()
        if self.value_equation_bucket.filter_method == 'dates':
            from valuenetwork.valueaccounting.forms import DateRangeForm
            form = DateRangeForm()
            bucket_filter = form.deserialize(serialized_filter)
            start_date = None
            end_date = None
            if "start_date" in bucket_filter:
                start_date = bucket_filter["start_date"]
                filter = "".join([
                    filter,
                    ", Start date: ",
                    start_date.strftime('%Y-%m-%d')
                    ])
            if "end_date" in bucket_filter:
                end_date = bucket_filter["end_date"]
                filter = "".join([
                    filter,
                    ", End date: ",
                    end_date.strftime('%Y-%m-%d')
                    ])
            events = EconomicEvent.objects.filter(context_agent=context_agent, event_type=self.event_type)
            if start_date and end_date:
                events = events.filter(event_date__range=(start_date, end_date))
            elif start_date:
                events = events.filter(event_date__gte=start_date)
            elif end_date:
                events = events.filter(event_date__gte=end_date)
            if process_types:
                events = events.filter(process__process_type__in=process_types)
            if resource_types:
                events = events.filter(resource_type__in=resource_types)
        elif self.value_equation_bucket.filter_method == 'order':
            from valuenetwork.valueaccounting.forms import OrderMultiSelectForm
            form = OrderMultiSelectForm(context_agent=context_agent)
            bucket_filter = form.deserialize(serialized_filter)
            orders = bucket_filter["orders"]
            if orders:
                order_string = ", ".join([str(o.id) for o in orders])
                if filter:
                    filter = "".join([
                        filter,
                        ", Orders: ",
                        order_string,
                        ])
                else:        
                    filter = "".join([
                        "Orders: ",
                        order_string,
                        ])
            events = []
            for order in orders:
                for order_item in order.order_items():
                    events.extend([e for e in order_item.compute_income_fractions() if e.event_type==self.event_type]) 
            if process_types:
                events = [e for e in events if e.process.process_type in process_types]
            if resource_types:
                events = [e for e in events if e.resource_type in resource_types]
        elif self.value_equation_bucket.filter_method == 'shipment':
            from valuenetwork.valueaccounting.forms import ShipmentMultiSelectForm
            form = ShipmentMultiSelectForm(context_agent=context_agent)
            bucket_filter = form.deserialize(serialized_filter)
            shipment_events = bucket_filter["shipments"]
            if shipment_events:
                ship_string = ", ".join([str(s.id) for s in shipment_events])
                if filter:
                    filter = "".join([
                        filter,
                        ", Shipments: ",
                        ship_string,
                        ])
                else:
                    filter = "".join([
                        "Shipments: ",
                        ship_string,
                        ])
            #lots = [e.resource for e in shipment_events]
            #import pdb; pdb.set_trace()
            events = []
            for ship in shipment_events:
                resource = ship.resource
                qty = ship.quantity
                events.extend([event for event in resource.compute_shipment_income_shares(qty) if event.event_type==self.event_type])
            if process_types:
                events_with_processes = [e for e in events if e.process]
                events = [e for e in events_with_processes if e.process.process_type in process_types]
            if resource_types:
                events = [e for e in events if e.resource_type in resource_types]
        for e in events:
            e.vebr = self
            e.vebr.filter = filter
        return events
        
    def claims_from_events(self, events):
        #import pdb; pdb.set_trace()
        claims = []
        for event in events:
            claim = event.get_unsaved_contribution_claim(self)
            #claim.creating_event = event
            fraction = 1
            if event.value:
                try:
                    fraction = event.share / event.value
                except AttributeError:
                    pass
            claim.share = claim.value * fraction
            claim.event = event
            claims.append(claim)
        return claims
        
    def gather_claims(self, context_agent, serialized_filter):
        #import pdb; pdb.set_trace()
        events = self.gather_events(context_agent=context_agent, serialized_filter=serialized_filter)
        return self.claims_from_events(events), events
        
    def create_distribution_claim_events(self, portion_of_amount, claims=None):
        #import pdb; pdb.set_trace()
        claim_events = []
        if claims == None:
            claims = self.gather_claims()
        for claim in claims:
            distr_amt = claim.share * portion_of_amount
            #if distr_amt > claim.value:
            #    distr_amt = claim.value
            if self.claim_rule_type == "debt-like":
                claim.value = claim.value - distr_amt
            elif self.claim_rule_type == "once":
                claim.value = 0
            claim.event.distr_amt = distr_amt.quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
            unit_of_value = ""
            if claim.event.unit_of_value:
                unit_of_value = claim.event.unit_of_value.abbrev
            excuse = ""
            if portion_of_amount < 1:
                percent = (portion_of_amount * 100).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
                excuse = "".join([
                    ", but the distribution amount covered only ",
                    str(percent),
                    "% of the claims for this bucket",
                    ])
            share = claim.share.quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
            sel = ""
            reason = ""
            obj = ""
            if "Orders" in claim.event.vebr.filter:
                obj = "order"
                sel = " to the selected orders"
            if "Shipments" in claim.event.vebr.filter:
                obj = "shipment"
                sel = " to the selected shipments"
            if share < claim.value:
                reason = " The reason the value added is less than the contribution value is that the contribution added value to more than one deliverable."
            claim.event.explanation = "".join([
                "This contribution added ", str(share), unit_of_value, 
                " of value",
                sel,
                excuse,
                ".",
                reason,
                ])
                
            claim_event = ClaimEvent(
                claim = claim,
                value = distr_amt,
                unit_of_value = claim.unit_of_value,
                event_effect = "-",
            )
            claim_events.append(claim_event)
        return claim_events    
        
    def normalize_equation(self):
        eq = self.claim_creation_equation.split(" ")
        for i, x in enumerate(eq):
            eq[i] = x.replace("_","")
            try:
                y = Decimal(x)
                eq[i] = "".join(["Decimal('", x, "')"])
            except InvalidOperation:
                continue
        s = " "
        return s.join(eq)
         
    def compute_claim_value(self, event):
        #import pdb; pdb.set_trace()
        equation = self.normalize_equation()
        safe_list = ['math',]
        safe_dict = dict([ (k, locals().get(k, None)) for k in safe_list ])
        safe_dict['Decimal'] = Decimal
        safe_dict['quantity'] = event.quantity
        safe_dict['valuePerUnit'] = event.value_per_unit()
        if event.resource:
            safe_dict['valuePerUnitOfUse'] = event.resource.value_per_unit_of_use
        safe_dict['value'] = event.value
        #safe_dict['importance'] = event.importance()
        #safe_dict['reputation'] = event.from_agent.reputation
        #safe_dict['seniority'] = Decimal(event.seniority())
        value = eval(equation, {"__builtins__":None}, safe_dict)
        return value
       
    def default_equation(self):
        et = self.event_type
        return et.default_event_value_equation()
            
    def filter_rule_deserialized(self):
        from valuenetwork.valueaccounting.forms import BucketRuleFilterSetForm
        form = BucketRuleFilterSetForm(prefix=str(self.id), context_agent=None, event_type=None, pattern=None)
        #import pdb; pdb.set_trace()
        return form.deserialize(json=self.filter_rule)
        
    def filter_rule_display_list(self):
        json = self.filter_rule_deserialized()
        pts = []
        rts = []
        if 'process_types' in json.keys():
            pts = json['process_types']
        if 'resource_types' in json.keys():
            rts = json['resource_types']
        filter = ""
        #for pt in pts:
        #    filter += pt.name + ", "
        #for rt in rts:
        #    filter += rt.name + ","
        if pts:
            filter = ", ".join([pt.name for pt in pts])
        if pts and rts:
            filter = ", ".join(filter, [pt.name for pt in pts])
        elif rts:
            filter = ", ".join([rt.name for rt in rts])
        return filter
        
    def test_results(self):
        #import pdb; pdb.set_trace()
        fr = self.filter_rule_deserialized()
        pts = []
        rts = []
        if 'process_types' in fr.keys():
            pts = fr['process_types']
        if 'resource_types' in fr.keys():
            rts = fr['resource_types']
        events = EconomicEvent.objects.filter(context_agent=self.value_equation_bucket.value_equation.context_agent, event_type=self.event_type)
        if pts:
            events = events.filter(process__process_type__in=pts)
        if rts:
            events = events.filter(resource_type__in=rts)
        return events
        
    def change_form(self):
        from valuenetwork.valueaccounting.forms import ValueEquationBucketRuleForm
        return ValueEquationBucketRuleForm(prefix="vebr" + str(self.id), instance=self)
         
    def change_filter_form(self):
        from valuenetwork.valueaccounting.forms import BucketRuleFilterSetForm
        ca = None
        pattern = None
        #import pdb; pdb.set_trace()
        if self.value_equation_bucket.value_equation.context_agent:
            ca = self.value_equation_bucket.value_equation.context_agent
        uc = UseCase.objects.get(identifier='val_equation')
        patterns = ProcessPattern.objects.usecase_patterns(use_case=uc)
        if patterns.count() > 0:
            pattern = patterns[0]
        json = self.filter_rule_deserialized()
        return BucketRuleFilterSetForm(prefix="vebrf" + str(self.id), initial=json, context_agent=ca, event_type=self.event_type, pattern=pattern)
        
            
class Claim(models.Model):
    value_equation_bucket_rule = models.ForeignKey(ValueEquationBucketRule,
        blank=True, null=True, 
        related_name="claims", verbose_name=_('value equation bucket rule'))
    claim_date = models.DateField(_('claim date'))
    has_agent = models.ForeignKey(EconomicAgent,
        blank=True, null=True,
        related_name="has_claims", verbose_name=_('has'))
    against_agent = models.ForeignKey(EconomicAgent,
        blank=True, null=True,
        related_name="claims against", verbose_name=_('against'))
    context_agent = models.ForeignKey(EconomicAgent,
        blank=True, null=True,
        limit_choices_to={"agent_type__is_context": True,},
        related_name="claims", verbose_name=_('context agent'),
        on_delete=models.SET_NULL)        
    value = models.DecimalField(_('value'), max_digits=8, decimal_places=2, 
        default=Decimal("0.0"))
    unit_of_value = models.ForeignKey(Unit, blank=True, null=True,
        verbose_name=_('unit of value'), related_name="claim_value_units")
    claim_creation_equation = models.TextField(_('creation equation'), null=True, blank=True)
    
    slug = models.SlugField(_("Page name"), editable=False)

    class Meta:
        ordering = ('claim_date',)

    def __unicode__(self):
        if self.unit_of_value:
            if self.unit_of_value.symbol:
                value_string = "".join([self.unit_of_value.symbol, str(self.value)])
            else:
                value_string = " ".join([str(self.value), self.unit_of_value.abbrev])
        else:
            value_string = str(self.value)
        has_agt = 'Unassigned'
        if self.has_agent:
            has_agt = self.has_agent.nick
        against_agt = 'Unassigned'
        if self.against_agent:
            against_agt = self.against_agent.nick
        return ' '.join([
            'Claim',
            has_agt,
            'has against',
            against_agt,
            'for',
            value_string,
            'from',
            self.claim_date.strftime('%Y-%m-%d'),
        ])
        
    def creating_event(self):
        event = None
        claim_events = self.claim_events.all()
        for ce in claim_events:
            if ce.event_effect == "+":
                event = ce.event
                break
        return event
        

EVENT_EFFECT_CHOICES = (
    ('+', _('increase')),
    ('-', _('decrease')),
 )
 
class ClaimEvent(models.Model):
    event = models.ForeignKey(EconomicEvent, 
        blank=True, null=True,
        related_name="claim_events", verbose_name=_('claim event'))
    claim = models.ForeignKey(Claim, 
        related_name="claim_events", verbose_name=_('claims'))
    claim_event_date = models.DateField(_('claim event date'), default=datetime.date.today)
    value = models.DecimalField(_('value'), max_digits=8, decimal_places=2)
    unit_of_value = models.ForeignKey(Unit, blank=True, null=True,
        verbose_name=_('unit of value'), related_name="claim_event_value_units")
    event_effect = models.CharField(_('event effect'), 
        max_length=12, choices=EVENT_EFFECT_CHOICES)       
    
    class Meta:
        ordering = ('claim_event_date',)

    def __unicode__(self):
        if self.unit_of_value:
            value_string = " ".join([str(self.value), self.unit_of_value.abbrev])
        else:
            value_string = str(self.value)
        if self.event:
            event_str = self.event.__unicode__()
        else:
            event_str = "none"
        return ' '.join([
            'event:',
            event_str,
            'affecting claim:',
            self.claim.__unicode__(),
            'value:',
            value_string,
        ])
       
    def update_claim(self):
        if self.event_effect == "+":
            self.claim.value += self.value
        else:
            self.claim.value -= self.value
        self.claim.save()
            

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
        return self.quantity.quantize(Decimal('.01'), rounding=ROUND_HALF_UP)


#todo: this model is obsolete and can be deleted
#as soon as we also remove the value equation demo page, view, etc.
class CachedEventSummary(models.Model):
    agent = models.ForeignKey(EconomicAgent,
        blank=True, null=True,
        related_name="cached_events", verbose_name=_('agent'))
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
                resource_type_rate=summary.resource_type.value_per_unit,
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
                key = "-".join([
                    str(event.from_agent.id), 
                    str(event.context_agent.id), 
                    str(event.resource_type.id), 
                    str(event.event_type.id)
                    ])
                if not key in summaries:
                    summaries[key] = EventSummary(
                        event.from_agent, 
                        event.context_agent, 
                        event.resource_type, 
                        event.event_type, 
                        Decimal('0.0'))
                #key = "-".join([
                #    str(event.from_agent.id), 
                #    str(event.project.id), 
                #    str(event.resource_type.id), 
                #    str(event.event_type.id)])
                #if not key in summaries:
                #    summaries[key] = EventSummary(
                #        agent=event.from_agent, 
                #        #project=event.project, 
                #        resource_type=event.resource_type, 
                #        event_type=event.event_type,
                #        quantity=Decimal('0.0'))
                summaries[key].quantity += event.quantity
            except AttributeError:
                msg = " ".join(["invalid summary key:", key])
                assert False, msg
        summaries = summaries.values()
        for summary in summaries:
            ces = cls(
                agent=summary.agent,
                context_agent=summary.context_agent,
                resource_type=summary.resource_type,
                event_type=summary.event_type,
                resource_type_rate=summary.resource_type.value_per_unit,
                #importance=summary.project.importance,
                quantity=summary.quantity,
            )
            ces.save()
        return cls.objects.all()


    def quantity_formatted(self):
        return self.quantity.quantize(Decimal('.01'), rounding=ROUND_HALF_UP)

    def value_formatted(self):
        return self.value.quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
        
    def quantity_label(self):
        #return " ".join([self.resource_type.name, self.resource_type.unit.abbrev])
        return self.resource_type.name


