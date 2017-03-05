from __future__ import print_function
from decimal import *
import datetime
import time

from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q
from django.conf import settings
from django.utils import six
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import python_2_unicode_compatible

from easy_thumbnails.fields import ThumbnailerImageField

from django_rea.annotations import push_down
from django_rea.spi import ModelProviderMeta
from ._utils import unique_slugify


class AgentAccount(object):
    def __init__(self, agent, event_type, count, quantity, events):
        self.agent = agent
        self.event_type = event_type
        self.count = count
        self.quantity = quantity
        self.events = events

    def example(self):
        return self.events[0]


class AgentManager(models.Manager):
    def without_user(self):
        # import pdb; pdb.set_trace()
        all_agents = EconomicAgent.objects.all()
        ua_ids = []
        for agent in all_agents:
            if agent.users.all():
                ua_ids.append(agent.id)
        return EconomicAgent.objects.exclude(id__in=ua_ids)

    def individuals_without_user(self):
        # import pdb; pdb.set_trace()
        all_agents = self.individuals()
        ua_ids = []
        for agent in all_agents:
            if agent.users.all():
                ua_ids.append(agent.id)
        return all_agents.exclude(id__in=ua_ids)

    def with_user(self):
        # better version from django-users
        # needs testing
        # return EconomicAgent.objects.filter(users__isnull=False).distinct()
        all_agents = EconomicAgent.objects.all()
        ua_ids = []
        for agent in all_agents:
            if agent.users.all():
                ua_ids.append(agent.id)
        return EconomicAgent.objects.filter(id__in=ua_ids)

    @push_down(layer="OCP")
    def without_membership_request(self):
        from ocp.work.models import MembershipRequest
        reqs = MembershipRequest.objects.all()
        req_agts = [req.agent for req in reqs if req.agent]
        rids = [agt.id for agt in req_agts]
        return EconomicAgent.objects.exclude(id__in=rids).order_by("name")

    @push_down(layer="OCP")
    def without_join_request(self):
        from ocp.work.models import JoinRequest
        reqs = JoinRequest.objects.all()
        req_agts = [req.agent for req in reqs if req.agent]
        rids = [agt.id for agt in req_agts]
        return EconomicAgent.objects.exclude(id__in=rids).order_by("name")

    def projects(self):
        return EconomicAgent.objects.filter(agent_type__party_type="team")

    def individuals(self):
        return EconomicAgent.objects.filter(agent_type__party_type="individual")

    def organizations(self):
        return EconomicAgent.objects.filter(agent_type__party_type="org")

    def networks(self):
        return EconomicAgent.objects.filter(agent_type__party_type="network")

    # def projects_and_networks(self):
    #    return EconomicAgent.objects.filter(Q(agent_type__party_type="network") | Q(agent_type__party_type="team"))

    def context_agents(self):
        return EconomicAgent.objects.filter(is_context=True)

    def non_context_agents(self):
        return EconomicAgent.objects.filter(is_context=False)

    def resource_role_agents(self):
        # return EconomicAgent.objects.filter(Q(is_context=True)|Q(agent_type__party_type="individual"))
        # todo: should there be some limits?  Ran into condition where we needed an organization, therefore change to below.
        return EconomicAgent.objects.all()

    @push_down(layer="OCP")
    def freedom_coop(self):
        if not settings.USE_FAIRCOINS:
            return None
        try:
            fc = EconomicAgent.objects.get(name="Freedom Coop")
        except EconomicAgent.DoesNotExist:
            return None
            # raise ValidationError("Freedom Coop does not exist by that name")
        return fc

    def open_projects(self):
        return EconomicAgent.objects.filter(project__visibility="public")  # is_public="True")


@python_2_unicode_compatible
class EconomicAgent(six.with_metaclass(ModelProviderMeta, models.Model)):
    name = models.CharField(_('name'), max_length=255)
    nick = models.CharField(_('ID'), max_length=32, unique=True,
                            help_text=_("Must be unique, and no more than 32 characters"))
    url = models.CharField(_('url'), max_length=255, blank=True)
    agent_type = models.ForeignKey("AgentType",
                                   verbose_name=_('agent type'), related_name='agents')
    description = models.TextField(_('description'), blank=True, null=True)
    address = models.CharField(_('address'), max_length=255, blank=True)
    email = models.EmailField(_('email address'), max_length=96, blank=True, null=True)
    phone_primary = models.CharField(_('primary phone'), max_length=32, blank=True, null=True)
    phone_secondary = models.CharField(_('secondary phone'), max_length=32, blank=True, null=True)
    latitude = models.FloatField(_('latitude'), default=0.0, blank=True, null=True)
    longitude = models.FloatField(_('longitude'), default=0.0, blank=True, null=True)
    primary_location = models.ForeignKey("Location",
                                         verbose_name=_('current location'), related_name='agents_at_location',
                                         blank=True, null=True,
                                         on_delete=models.SET_NULL)
    reputation = models.DecimalField(_('reputation'), max_digits=8, decimal_places=2,
                                     default=Decimal("0.00"))
    photo = ThumbnailerImageField(_("photo"),
                                  upload_to='photos', blank=True, null=True)
    photo_url = models.CharField(_('photo url'), max_length=255, blank=True)
    unit_of_claim_value = models.ForeignKey("Unit", blank=True, null=True,
                                            verbose_name=_('unit used in claims'), related_name="agents",
                                            help_text=_('For a context agent, the unit of all claims'))
    is_context = models.BooleanField(_('is context'), default=False)
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

    def __str__(self):
        return self.nick

    def save(self, *args, **kwargs):
        unique_slugify(self, self.nick)
        super(EconomicAgent, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        aus = self.users.all()
        if aus:
            for au in aus:
                user = au.user
                user.delete()
                au.delete()
        super(EconomicAgent, self).delete(*args, **kwargs)

    @models.permalink
    def get_absolute_url(self):
        return ('agent', (),
                {'agent_id': str(self.id), })

    @push_down(layer="OCP")
    def membership_request(self):
        reqs = self.membership_requests.all()
        if reqs:
            return reqs[0]
        else:
            return None

    @push_down(layer="OCP")
    def membership_request_id(self):
        req = self.membership_request()
        if req:
            return req.id
        else:
            return None

    """def joinaproject_request(self): # TODO deprecate this function around (only first request!)
        reqs = self.project_join_requests.all()
        if reqs:
            return reqs[0]
        else:
            return None

    def joinaproject_request_id(self): # TODO deprecate this function around (only first request!)
        reqs = self.project_join_requests.all()
        if reqs:
            return reqs[0].id
        else:
            return None
    """

    @push_down(layer="OCP")
    def joinaproject_requests(self):
        reqs = self.project_join_requests.all()
        if reqs:
            return reqs
        else:
            return None

    @push_down(layer="OCP")
    def joinaproject_requests_projects(self):
        reqs = self.project_join_requests.all()
        projects = []
        if reqs:
            for req in reqs:
                projects.append(req.project)
            return projects
        else:
            return None

    @push_down(layer="OCP")
    def request_faircoin_address(self):
        # import pdb; pdb.set_trace()
        address = self.faircoin_address()
        if not address:
            address = "address_requested"
            resource = self.create_faircoin_resource(address)
        return address

    @push_down(layer="OCP")
    def create_fake_faircoin_address(self):
        # import pdb; pdb.set_trace()
        address = self.faircoin_address()
        if not address:
            address = str(time.time())
            resource = self.create_faircoin_resource(address)
            print("created fake faircoin address")
        return address

    @push_down(layer="OCP")
    def create_faircoin_resource(self, address):
        from django_rea.valueaccounting.models.resource import EconomicResource, AgentResourceRole, AgentResourceRoleType
        from django_rea.valueaccounting.models.recipe import EconomicResourceType
        if not settings.USE_FAIRCOINS:
            return None
        role_types = AgentResourceRoleType.objects.filter(is_owner=True)
        owner_role_type = None
        if role_types:
            owner_role_type = role_types[0]
        # import pdb; pdb.set_trace()
        resource_types = EconomicResourceType.objects.filter(
            behavior="dig_acct")
        if resource_types.count() == 0:
            raise ValidationError(
                "Cannot create digital currency resource for " + self.nick + " because no digital currency account ResourceTypes.")
        if resource_types.count() > 1:
            raise ValidationError(
                "Cannot create digital currency resource for " + self.nick + ", more than one digital currency account ResourceTypes.")
        resource_type = resource_types[0]
        if owner_role_type:
            # resource type has unit
            va = EconomicResource(
                resource_type=resource_type,
                identifier="Faircoin address for " + self.nick,
                digital_currency_address=address,
            )
            va.save()
            arr = AgentResourceRole(
                agent=self,
                role=owner_role_type,
                resource=va,
            )
            arr.save()
            return va
        else:
            raise ValidationError(
                "Cannot create digital currency resource for " + self.nick + " because no owner AgentResourceRoleTypes.")

    @push_down(layer="OCP")
    def faircoin_address(self):
        if not settings.USE_FAIRCOINS:
            return None
        fcr = self.faircoin_resource()
        if fcr:
            return fcr.digital_currency_address
        else:
            return None

    @push_down(layer="OCP")
    def faircoin_resource(self):
        if not settings.USE_FAIRCOINS:
            return None
        candidates = self.agent_resource_roles.filter(
            role__is_owner=True,
            resource__resource_type__behavior="dig_acct",
            resource__digital_currency_address__isnull=False)
        if candidates:
            return candidates[0].resource
        else:
            return None

    @push_down(layer="OCP")
    def candidate_membership(self):
        aa = self.candidate_association()
        if aa:
            if aa.state == "potential":
                return aa.has_associate
        return None

    @push_down(layer="OCP")
    def candidate_association(self):
        aas = self.is_associate_of.all()
        if aas:
            aa = aas[0]
            if aa.state == "potential":
                return aa

    @push_down(layer="OCP")
    def number_of_shares(self):
        if self.agent_type.party_type == "individual":
            shares = 1
        else:
            shares = 2
        req = self.membership_request()
        if req:
            req_shares = req.number_of_shares
            shares = req_shares if req_shares > shares else shares
        return shares

    def owns(self, resource):
        if self in resource.owners():
            return True
        else:
            return False

    def owns_resource_of_type(self, resource_type):
        answer = False
        arrs = self.agent_resource_roles.filter(
            role__is_owner=True,
            resource__resource_type=resource_type)
        if arrs:
            answer = True
        return answer

    def my_user(self):
        # import pdb; pdb.set_trace()
        users = self.users.all()
        if users:
            return users[0].user
        return None

    def is_superuser(self):
        if self.my_user():
            return self.my_user().is_superuser
        return False

    def is_staff(self):
        if self.my_user():
            return self.my_user().is_staff
        return False

    def is_coop_worker(self):
        if not self.is_superuser() and not self.is_staff():
            return True
        return False

    @push_down(layer="OCP")
    def is_active_freedom_coop_member(self):
        if not settings.USE_FAIRCOINS:
            return False
        fc = EconomicAgent.objects.freedom_coop()
        fcaas = self.is_associate_of.filter(
            association_type__association_behavior="member",
            has_associate=fc,
            state="active")
        if fcaas:
            return True
        else:
            return False

    @push_down(layer="OCP")
    def is_participant(self):
        fcaas = None
        if not self.is_active_freedom_coop_member() and self.joinaproject_requests():
            reqs = self.joinaproject_requests()
            if reqs:
                for req in reqs:
                    fcaas = self.is_associate_of.filter(
                        association_type__association_behavior="member",
                        has_associate=req.project.agent,
                        state="active")
                    if fcaas:
                        break
                        return True
        if fcaas:
            return True
        else:
            return False

    @push_down(layer="OCP")
    def is_participant_candidate(self):
        fcaas = None
        if not self.is_active_freedom_coop_member() and self.joinaproject_requests():
            reqs = self.joinaproject_requests()
            if reqs:
                for req in reqs:
                    fcaas = self.is_associate_of.filter(
                        association_type__association_behavior="member",
                        has_associate=req.project.agent,
                        state="potential")
        if fcaas and not self.is_participant():
            return True
        else:
            return False

    def seniority(self):
        return (datetime.date.today() - self.created_date).days

    def node_id(self):
        if self.agent_type.party_type == "team":
            return "-".join(["Project", str(self.id)])
        else:
            return "-".join(["Agent", str(self.id)])

    def color(self):  # todo: not tested
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
            Q(event_type__relationship='consume') | Q(event_type__relationship='use'))

    def consumed_and_used_resource_types(self):
        return [ptrt.resource_type for ptrt in self.consumed_and_used_resource_type_relationships()]

    def orders(self):
        # import pdb; pdb.set_trace()
        ps = self.processes.all()
        oset = {p.independent_demand() for p in ps if p.independent_demand()}
        return list(oset)

    def active_orders(self):
        return [o for o in self.orders() if o.has_open_processes()]

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
        users = self.users.filter(user__is_active=True)
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
        aps = [p for p in self.worked_processes() if p.finished == False]
        return aps

    def finished_worked_processes(self):
        aps = [p for p in self.worked_processes() if p.finished == True]
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

    # from here these were copied from project - todo: fix these to work correctly using context agent relationships (these are in various stages of fix and test)
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

    def total_financial_contributions(self):
        # this is wrong
        events = self.events.filter(
            Q(event_type__name='Cash Contribution') |
            Q(event_type__name='Purchase Contribution') |
            Q(event_type__name='Expense Contribution')
        )
        return sum(event.quantity for event in events)

    def total_financial_income(self):
        # this is really wrong
        events = self.events.filter(
            Q(event_type__name='Cash Contribution') |
            Q(event_type__name='Purchase Contribution') |
            Q(event_type__name='Expense Contribution')
        )
        return sum(event.quantity for event in events)

    def events_by_event_type(self):
        from django_rea.valueaccounting.models.event import EconomicEvent
        from django_rea.valueaccounting.models.recipe import EventType
        agent_events = EconomicEvent.objects.filter(
            Q(from_agent=self) | Q(to_agent=self))
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

    def distributions_count(self):
        from django_rea.valueaccounting.models.distribution import Distribution
        return Distribution.objects.filter(context_agent=self).count()

    def demand_exchange_count(self):
        from .trade import Exchange
        return Exchange.objects.demand_exchanges().filter(context_agent=self).count()

    def supply_exchange_count(self):
        from .trade import Exchange
        return Exchange.objects.supply_exchanges().filter(context_agent=self).count()

    def internal_exchange_count(self):
        from .trade import Exchange
        return Exchange.objects.internal_exchanges().filter(context_agent=self).count()

    def with_all_sub_agents(self):
        from django_rea.valueaccounting.utils import flattened_children_by_association
        aas = AgentAssociation.objects.filter(association_type__association_behavior="child").order_by(
            "is_associate__name")
        return flattened_children_by_association(self, aas, [])

    def with_all_associations(self):
        from django_rea.valueaccounting.utils import group_dfs_by_has_associate, group_dfs_by_is_associate
        if self.is_individual():
            agents = [self, ]
            agents.extend([ag.has_associate for ag in self.is_associate_of.all()])
            agents.extend([ag.is_associate for ag in self.has_associates.all()])
        else:
            associations = AgentAssociation.objects.all().order_by("-association_type")
            # associations = associations.exclude(is_associate__agent_type__party_type="individual")
            # associations = associations.exclude(association_type__identifier="supplier")
            gas = group_dfs_by_has_associate(self, self, associations, [], 1)
            gas.extend(group_dfs_by_is_associate(self, self, associations, [], 1))
            agents = [self, ]
            for ga in gas:
                if ga not in agents:
                    agents.append(ga)
        return agents

    def related_contexts(self):
        agents = [ag.has_associate for ag in self.is_associate_of.all()]
        agents.extend([ag.is_associate for ag in self.has_associates.all()])
        return [a for a in agents if a.is_context]

    def related_context_queryset(self):
        ctx_ids = [ctx.id for ctx in self.related_contexts()]
        return EconomicAgent.objects.filter(id__in=ctx_ids)

    def invoicing_candidates(self):
        ctx = self.related_contexts()
        ids = [c.id for c in ctx if c.is_active_freedom_coop_member()]
        if self.is_active_freedom_coop_member():
            ids.insert(0, self.id)
        return EconomicAgent.objects.filter(id__in=ids)

    #  bum2
    def managed_projects(self):  # returns a list or None
        agents = [ag.has_associate for ag in
                  self.is_associate_of.filter(association_type__association_behavior="manager")]
        return [a for a in agents if a.is_context]  # EconomicAgent.objects.filter(pk__in=agent_ids)

    def is_public(self):
        project = self.project
        if project and project.is_public():
            return True
        else:
            return False

    #

    def task_assignment_candidates(self):
        answer = []
        if self.is_context:
            answer = [a.is_associate for a in self.all_has_associates() if a.is_associate.is_individual()]
        return answer

    def child_tree(self):
        from django_rea.valueaccounting.utils import agent_dfs_by_association
        # todo: figure out why this failed when AAs were ordered by from_agent
        aas = AgentAssociation.objects.filter(association_type__association_behavior="child").order_by(
            "is_associate__name")
        return agent_dfs_by_association(self, aas, 1)

    def wip(self):
        return self.active_processes()

    def process_types_queryset(self):
        from django_rea.valueaccounting.models.recipe import ProcessType
        pts = list(ProcessType.objects.filter(context_agent=self))
        parent = self.parent()
        while parent:
            pts.extend(ProcessType.objects.filter(context_agent=parent))
            parent = parent.parent()
        pt_ids = [pt.id for pt in pts]
        return ProcessType.objects.filter(id__in=pt_ids)

    def get_resource_types_with_recipe(self):
        from django_rea.valueaccounting.models.recipe import ProcessType
        rts = [pt.main_produced_resource_type() for pt in ProcessType.objects.filter(context_agent=self) if
               pt.main_produced_resource_type()]
        # import pdb; pdb.set_trace()
        parents = []
        parent = self.parent()
        while parent:
            parents.append(parent)
            parent = parent.parent()
        for p in parents:
            rts.extend([pt.main_produced_resource_type() for pt in ProcessType.objects.filter(context_agent=p) if
                        pt.main_produced_resource_type()])
        parent_rts = rts
        for rt in parent_rts:
            rts.extend(rt.all_children())

        return list(set(rts))

    def get_resource_type_lists(self):
        rt_lists = list(self.lists.all())
        # import pdb; pdb.set_trace()
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

    # from here are new methods for context agent code
    def parent(self):
        # assumes only one parent
        # import pdb; pdb.set_trace()
        associations = self.is_associate_of.filter(association_type__association_behavior="child").filter(
            state="active")
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

    def children(self):  # returns a list or None
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
        # import pdb; pdb.set_trace()
        agent_ids = self.has_associates.filter(association_type__association_behavior="supplier").filter(
            state="active").values_list('is_associate')
        return EconomicAgent.objects.filter(pk__in=agent_ids)

    def exchange_firms(self):
        # import pdb; pdb.set_trace()
        agent_ids = self.has_associates.filter(association_type__association_behavior="exchange").filter(
            state="active").values_list('is_associate')
        return EconomicAgent.objects.filter(pk__in=agent_ids)

    def members(self):
        # import pdb; pdb.set_trace()
        agent_ids = self.has_associates.filter(
            Q(association_type__association_behavior="member") | Q(association_type__association_behavior="manager")
        ).filter(state="active").values_list('is_associate')
        return EconomicAgent.objects.filter(pk__in=agent_ids)

    def individual_members(self):
        return self.members().filter(agent_type__party_type="individual")

    #  bum2
    def managers(self):  # returns a list or None
        agent_ids = self.has_associates.filter(association_type__association_behavior="manager").filter(
            state="active").values_list('is_associate')
        return EconomicAgent.objects.filter(pk__in=agent_ids)

    # def affiliates(self):
    #    #import pdb; pdb.set_trace()
    #    agent_ids = self.has_associates.filter(association_type__identifier="affiliate").filter(state="active").values_list('is_associate')
    #    return EconomicAgent.objects.filter(pk__in=agent_ids)

    def customers(self):
        # import pdb; pdb.set_trace()
        agent_ids = self.has_associates.filter(association_type__association_behavior="customer").filter(
            state="active").values_list('is_associate')
        return EconomicAgent.objects.filter(pk__in=agent_ids)

    def potential_customers(self):
        # import pdb; pdb.set_trace()
        agent_ids = self.has_associates.filter(association_type__association_behavior="customer").filter(
            state="potential").values_list('is_associate')
        return EconomicAgent.objects.filter(pk__in=agent_ids)

    def all_has_associates_by_type(self, assoc_type_identifier):
        # import pdb; pdb.set_trace()
        agent_ids = self.has_associates.filter(association_type__identifier=assoc_type_identifier).exclude(
            state="inactive").values_list('is_associate')
        return EconomicAgent.objects.filter(pk__in=agent_ids)

    def has_associates_of_type(self, assoc_type_identifier):  # returns boolean
        # import pdb; pdb.set_trace()
        if self.all_has_associates_by_type(
                assoc_type_identifier).count() > 0:  # todo: can this be made more efficient, return count from sql?
            return True
        else:
            return False

    def has_associates_self_or_inherited(self, assoc_type_identifier):
        # import pdb; pdb.set_trace()
        assocs = self.all_has_associates_by_type(assoc_type_identifier)
        if assocs:
            return assocs
        parent = self.parent()
        while parent:
            assocs = parent.all_has_associates_by_type(assoc_type_identifier)
            if assocs:
                return assocs
            parent = parent.parent()
        return EconomicAgent.objects.none()

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

    def association_with(self, context):
        associations = self.is_associate_of.filter(has_associate=context)
        if associations:
            return associations[0]
        else:
            return []

    def is_manager_of(self, context):
        if self is context:
            return True
        association = self.association_with(context)
        if association:
            if association.association_type.association_behavior == "manager":
                return True
        return False

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

    def virtual_accounts(self):
        vars = self.agent_resource_roles.filter(
            role__is_owner=True,
            resource__resource_type__behavior="account")
        return [var.resource for var in vars]

    def create_virtual_account(self, resource_type):
        # import pdb; pdb.set_trace()
        from django_rea.valueaccounting.models.resource import (
            EconomicResource,
            AgentResourceRole,
            AgentResourceRoleType
        )
        role_types = AgentResourceRoleType.objects.filter(is_owner=True)
        owner_role_type = None
        if role_types:
            owner_role_type = role_types[0]
        if owner_role_type:
            va = EconomicResource(
                resource_type=resource_type,
                identifier="Virtual account for " + self.nick,
            )
            va.save()
            arr = AgentResourceRole(
                agent=self,
                role=owner_role_type,
                resource=va,
            )
            arr.save()
            return va
        else:
            raise ValidationError(
                "Cannot create virtual account for " + self.nick + " because no owner AgentResourceRoleTypes."
            )

    def own_or_parent_value_equations(self):
        ves = self.value_equations.all()
        if ves:
            return ves
        parent = self.parent()
        while parent:
            ves = parent.value_equations.all()
            if ves:
                return ves
            parent = parent.parent()
        return []

    def live_value_equations(self):
        # shd this use own_or_parent_value_equations?
        return self.value_equations.filter(live=True)

    def compatible_value_equation(self, value_equation):
        if value_equation.context_agent == self:
            return True
        if value_equation.live:
            if value_equation in self.live_value_equations():
                return True
        else:
            if value_equation in self.own_or_parent_value_equations():
                return True
        return False

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
        # import pdb; pdb.set_trace()
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
        # import pdb; pdb.set_trace()
        agent_list = list(self.all_ancestors())
        agent_list.extend(self.all_members_list())
        agent_ids = [agent.id for agent in agent_list]
        return EconomicAgent.objects.filter(pk__in=agent_ids)

    def context_equipment_users(self):
        agent_list = self.all_members_list()
        agent_list.extend([agent for agent in self.exchange_firms()])
        return agent_list

    def all_has_associates(self):
        return self.has_associates.all().order_by('association_type__name', 'is_associate__nick')

    def all_is_associates(self):
        return self.is_associate_of.all().order_by('association_type__name', 'has_associate__nick')

    def all_associations(self):
        return AgentAssociation.objects.filter(
            Q(has_associate=self) | Q(is_associate=self))

    def is_context_agent(self):
        return self.is_context

    def orders_queryset(self):
        # import pdb; pdb.set_trace()
        from django_rea.valueaccounting.models.schedule import Order
        orders = []
        exf = self.exchange_firm()
        cr_orders = []
        if exf:
            crs = self.undistributed_events()
            cr_orders = [cr.exchange.order for cr in crs if cr.exchange]
        for order in Order.objects.all():
            cas = order.context_agents()
            if self in cas:
                orders.append(order)
            if exf:
                if exf in cas:
                    if order in cr_orders:
                        orders.append(order)
        orders = list(set(orders))
        order_ids = [order.id for order in orders]
        return Order.objects.filter(id__in=order_ids)

    def shipments_queryset(self):
        from django_rea.valueaccounting.models.recipe import EventType
        from django_rea.valueaccounting.models.facetconfig import UseCase
        from django_rea.valueaccounting.models.event import EconomicEvent
        # import pdb; pdb.set_trace()
        shipments = []
        exf = self.exchange_firm()
        # ship = EventType.objects.get(label="ships")
        # transfer = EventType.objects.get(name="Reciprocal Transfer")
        # qs = EconomicEvent.objects.filter(Q(event_type=ship)|Q(event_type=transfer))
        et_give = EventType.objects.get(name="Give")
        uc_demand = UseCase.objects.get(identifier="demand_xfer")
        qs = EconomicEvent.objects.filter(event_type=et_give).filter(
            transfer__transfer_type__exchange_type__use_case=uc_demand)
        # todo: retest, may need production events for shipments to tell
        # if a shipment shd be excluded or not
        if exf:
            cas = [self, exf]
            qs = qs.filter(context_agent__in=cas)
            ids_to_delete = []
            for ship in qs:
                if ship.context_agent != self:
                    if ship.commitment:
                        if ship.commitment.context_agent != self:
                            pc_cas = [pc.context_agent for pc in
                                      ship.commitment.get_production_commitments_for_shipment()]
                            pc_cas = list(set(pc_cas))
                            if self not in pc_cas:
                                ids_to_delete.append(ship.id)
                                # else:
                                #    ids_to_delete.append(ship.id)
                if ids_to_delete:
                    qs = qs.exclude(id__in=ids_to_delete)
        else:
            qs = qs.filter(context_agent=self)
        return qs

    def undistributed_events(self):
        from django_rea.valueaccounting.models.event import EconomicEvent
        # import pdb; pdb.set_trace()
        event_ids = []
        # et = EventType.objects.get(name="Cash Receipt")
        events = EconomicEvent.objects.filter(to_agent=self).filter(is_to_distribute=True)
        for event in events:
            if event.is_undistributed():
                event_ids.append(event.id)
        exf = self.exchange_firm()
        # todo: maybe use shipments in addition or instead of virtual accounts?
        # exchange firm might put cash receipt into a more general virtual account
        if exf:
            events = exf.undistributed_events()
            event_ids.extend(event.id for event in events)
            # todo: analyze this. (note change from cash receipts to events marked is_to_distribute
            # is_undistributed is unnecessary: crs only includes undistributed
            # is_virtual_account_of is the restriction that needs analysis
            # for cr in crs:
            #    if cr.is_undistributed():
            #        if cr.resource.is_virtual_account_of(self):
            #            cr_ids.append(cr.id)
        return EconomicEvent.objects.filter(id__in=event_ids)

    def undistributed_distributions(self):
        from django_rea.valueaccounting.models.recipe import EventType
        from django_rea.valueaccounting.models.event import EconomicEvent
        # import pdb; pdb.set_trace()
        id_ids = []
        et = EventType.objects.get(name="Distribution")
        ids = EconomicEvent.objects.filter(to_agent=self).filter(event_type=et)
        for id in ids:
            if id.is_undistributed():
                id_ids.append(id.id)
        return EconomicEvent.objects.filter(id__in=id_ids)

    def is_deletable(self):
        # import pdb; pdb.set_trace()
        if self.given_events.filter(quantity__gt=0):
            return False
        if self.taken_events.filter(quantity__gt=0):
            return False
        if self.given_commitments.filter(quantity__gt=0):
            return False
        if self.taken_commitments.filter(quantity__gt=0):
            return False
        if self.exchanges_as_customer.all():
            return False
        if self.exchanges_as_supplier.all():
            return False
        if self.virtual_accounts():
            return False
        if self.faircoin_resource():
            return False
        return True

    def contexts_participated_in(self):
        answer = []
        if self.agent_type.party_type == "individual":
            events = self.given_events.exclude(context_agent__isnull=True)
            cids = events.values_list('context_agent', flat=True)
            cids = list(set(cids))
            answer = EconomicAgent.objects.filter(id__in=cids)
        return answer


class AgentUser(models.Model):
    agent = models.ForeignKey("EconomicAgent",
                              verbose_name=_('agent'), related_name='users')
    user = models.OneToOneField(User,
                                verbose_name=_('user'), related_name='agent')


RELATIONSHIP_STATE_CHOICES = (
    ('active', _('active')),
    ('inactive', _('inactive')),
    ('potential', _('candidate')),
)


@python_2_unicode_compatible
class AgentAssociation(models.Model):
    is_associate = models.ForeignKey("EconomicAgent",
                                     verbose_name=_('is associate of'), related_name='is_associate_of')
    has_associate = models.ForeignKey("EconomicAgent",
                                      verbose_name=_('has associate'), related_name='has_associates')
    association_type = models.ForeignKey("AgentAssociationType",
                                         verbose_name=_('association type'), related_name='associations')
    description = models.TextField(_('description'), blank=True, null=True)
    state = models.CharField(_('state'),
                             max_length=12, choices=RELATIONSHIP_STATE_CHOICES,
                             default='active')

    class Meta:
        ordering = ('is_associate',)

    def __str__(self):
        return self.is_associate.nick + " " + self.association_type.label + " " + self.has_associate.nick

    def representation(self):
        state = ""
        if self.state == "potential":
            state = "".join(["(", self.get_state_display(), ")"])
        return " ".join([
            self.is_associate.nick,
            self.association_type.label,
            self.has_associate.nick,
            state,
        ])


ASSOCIATION_BEHAVIOR_CHOICES = (
    ('supplier', _('supplier')),
    ('customer', _('customer')),
    ('member', _('member')),
    ('child', _('child')),
    ('custodian', _('custodian')),
    ('manager', _('manager')),
    ('peer', _('peer'))
)


@python_2_unicode_compatible
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

    def __str__(self):
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
                    print("Updated %s AgentAssociationType" % name)
        except cls.DoesNotExist:
            cls(identifier=identifier, name=name, plural_name=plural_name, association_behavior=association_behavior,
                label=label, inverse_label=inverse_label).save()
            if verbosity > 1:
                print("Created %s AgentAssociationType" % name)


class AgentTypeManager(models.Manager):
    def context_agent_types(self):
        return AgentType.objects.filter(is_context=True)

    def context_types_string(self):
        return " or ".join([at.name for at in self.context_agent_types()])

    def non_context_agent_types(self):
        return AgentType.objects.filter(is_context=False)

    def individual_type(self):
        at = AgentType.objects.filter(party_type="individual")
        if at:
            return at[0]
        else:
            return None


SIZE_CHOICES = (
    ('individual', _('individual')),
    ('org', _('organization')),
    ('network', _('network')),
    ('team', _('project')),
    ('community', _('community')),
)


@python_2_unicode_compatible
class AgentType(models.Model):
    name = models.CharField(_('name'), max_length=128)
    parent = models.ForeignKey('self', blank=True, null=True,
                               verbose_name=_('parent'), related_name='sub_agents', editable=False)
    party_type = models.CharField(_('party type'),
                                  max_length=12, choices=SIZE_CHOICES,
                                  default='individual')
    description = models.TextField(_('description'), blank=True, null=True)
    is_context = models.BooleanField(_('is context'), default=False)
    objects = AgentTypeManager()

    class Meta:
        ordering = ('name',)

    def __str__(self):
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
                    print("Updated %s AgentType" % name)
        except cls.DoesNotExist:
            cls(name=name, party_type=party_type, is_context=is_context).save()
            if verbosity > 1:
                print("Created %s AgentType" % name)
