from __future__ import print_function
from decimal import *
import datetime
import time

from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import python_2_unicode_compatible

from easy_thumbnails.fields import ThumbnailerImageField

from toposort import toposort, toposort_flatten

from ._utils import unique_slugify

FAIRCOIN_DIVISOR = Decimal("1000000.00")


class AgentAccount(object):
    def __init__(self, agent, event_type, count, quantity, events):
        self.agent = agent
        self.event_type = event_type
        self.count = count
        self.quantity = quantity
        self.events = events

    def example(self):
        return self.events[0]


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


@python_2_unicode_compatible
class AccountingReference(models.Model):
    code = models.CharField(_('code'), max_length=128, unique=True)
    name = models.CharField(_('name'), max_length=128)

    def __str__(self):
        return self.name


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

    def without_membership_request(self):
        from ocp.work.models import MembershipRequest
        reqs = MembershipRequest.objects.all()
        req_agts = [req.agent for req in reqs if req.agent]
        rids = [agt.id for agt in req_agts]
        return EconomicAgent.objects.exclude(id__in=rids).order_by("name")

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

    def freedom_coop(self):
        if not settings.use_faircoins:
            return None
        try:
            fc = EconomicAgent.objects.get(name="Freedom Coop")
        except EconomicAgent.DoesNotExist:
            return None
            # raise ValidationError("Freedom Coop does not exist by that name")
        return fc

    def open_projects(self):
        return EconomicAgent.objects.filter(project__visibility="public")  # is_public="True")


class GoodResourceManager(models.Manager):
    def get_queryset(self):
        return super(GoodResourceManager, self).get_queryset().exclude(quality__lt=0)


class FailedResourceManager(models.Manager):
    def get_queryset(self):
        return super(FailedResourceManager, self).get_queryset().filter(quality__lt=0)


class EconomicResourceManager(models.Manager):
    def virtual_accounts(self):
        # import pdb; pdb.set_trace()
        resources = EconomicResource.objects.all()
        vas = []
        for resource in resources:
            if resource.resource_type.is_virtual_account():
                vas.append(resource)
        return vas

    def context_agent_virtual_accounts(self):
        vas = self.virtual_accounts()
        # import pdb; pdb.set_trace()
        cavas = []
        for va in vas:
            if va.owner():
                if va.owner().is_context_agent():
                    cavas.append(va)
        return cavas

    def onhand(self):
        return EconomicResource.objects.filter(quantity__gt=0)


@python_2_unicode_compatible
class EconomicResource(models.Model):
    resource_type = models.ForeignKey("EconomicResourceType",
                                      verbose_name=_('resource type'), related_name='resources')
    identifier = models.CharField(_('identifier'), blank=True, max_length=128)
    independent_demand = models.ForeignKey("Order",
                                           blank=True, null=True,
                                           related_name="dependent_resources", verbose_name=_('independent demand'))
    order_item = models.ForeignKey("Commitment",
                                   blank=True, null=True,
                                   related_name="stream_resources", verbose_name=_('order item'))
    stage = models.ForeignKey("ProcessType", related_name="resources_at_stage",
                              verbose_name=_('stage'), blank=True, null=True)
    exchange_stage = models.ForeignKey("ExchangeType", related_name="resources_at_exchange_stage",
                                       verbose_name=_('exchange stage'), blank=True, null=True)
    state = models.ForeignKey("ResourceState", related_name="resources_at_state",
                              verbose_name=_('state'), blank=True, null=True)
    url = models.CharField(_('url'), max_length=255, blank=True)
    # todo: remove author, in the meantime, don't use it
    author = models.ForeignKey("EconomicAgent", related_name="authored_resources",
                               verbose_name=_('author'), blank=True, null=True)
    quantity = models.DecimalField(_('quantity'), max_digits=8, decimal_places=2,
                                   default=Decimal("0.00"), editable=False)
    quality = models.DecimalField(_('quality'), max_digits=3, decimal_places=0,
                                  default=Decimal("0"), blank=True, null=True)
    notes = models.TextField(_('notes'), blank=True, null=True)
    photo = ThumbnailerImageField(_("photo"),
                                  upload_to='photos', blank=True, null=True)
    photo_url = models.CharField(_('photo url'), max_length=255, blank=True)
    access_rules = models.TextField(_('access rules'), blank=True, null=True)
    current_location = models.ForeignKey("Location",
                                         verbose_name=_('current location'), related_name='resources_at_location',
                                         blank=True, null=True)
    digital_currency_address = models.CharField(_("digital currency address"), max_length=96,
                                                blank=True, null=True, editable=False)
    value_per_unit = models.DecimalField(_('value per unit'), max_digits=8, decimal_places=2,
                                         default=Decimal("0.00"))
    value_per_unit_of_use = models.DecimalField(_('value per unit of use'), max_digits=8, decimal_places=2,
                                                default=Decimal("0.00"))
    price_per_unit = models.DecimalField(_('price per unit'), max_digits=8, decimal_places=2,
                                         default=Decimal("0.00"))
    created_date = models.DateField(_('created date'), default=datetime.date.today)
    created_by = models.ForeignKey(User, verbose_name=_('created by'),
                                   related_name='resources_created', blank=True, null=True, editable=False)
    changed_by = models.ForeignKey(User, verbose_name=_('changed by'),
                                   related_name='resources_changed', blank=True, null=True, editable=False)
    changed_date = models.DateField(auto_now=True, blank=True, null=True, editable=False)

    objects = EconomicResourceManager()
    goods = GoodResourceManager()
    failures = FailedResourceManager()

    class Meta:
        ordering = ('resource_type', 'identifier',)

    def __str__(self):
        # import pdb; pdb.set_trace()
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
                {'resource_id': str(self.id), })

    def label(self):
        return self.identifier or str(self.id)

    def flow_type(self):
        return "Resource"

    def flow_class(self):
        return "resource"

    def class_label(self):
        return "Economic Resource"

    def flow_description(self):
        # rollup stage change
        id_str = self.identifier or str(self.id)
        resource_string = self.resource_type.name
        try:
            stage = self.historical_stage
        except AttributeError:
            stage = self.stage
        if stage:
            resource_string = "@".join([resource_string, stage.name])
        return ": ".join([
            resource_string,
            id_str,
        ])

    def is_digital_currency_resource(self):
        if not settings.use_faircoins:
            return False
        if self.digital_currency_address:
            return True
        else:
            return False

    def address_is_activated(self):
        if not settings.use_faircoins:
            return False
        address = self.digital_currency_address
        if address:
            if address != "address_requested":
                return True
        return False

    def digital_currency_history(self):
        history = []
        if not settings.use_faircoins:
            return history
        address = self.digital_currency_address
        if address:
            from django_rea.valueaccounting.faircoin_utils import get_address_history
            history = get_address_history(address)
        return history

    def digital_currency_balance(self):
        bal = 0
        if not settings.use_faircoins:
            return bal
        address = self.digital_currency_address
        if address:
            try:
                from django_rea.valueaccounting.faircoin_utils import get_address_balance
                balance = get_address_balance(address)
                balance = balance[0]
                if balance:
                    bal = Decimal(balance) / FAIRCOIN_DIVISOR
            except InvalidOperation:
                bal = "Not accessible now"
        return bal

    def spending_limit(self):
        limit = 0
        if not settings.use_faircoins:
            return limit
        address = self.digital_currency_address
        if address:
            from django_rea.valueaccounting.faircoin_utils import get_address_balance, network_fee
            balance = get_address_balance(address)
            if balance:
                bal = Decimal(balance[0]) / FAIRCOIN_DIVISOR
                fee = Decimal(network_fee()) / FAIRCOIN_DIVISOR
                limit = bal - fee
        return limit

    def context_agents(self):
        pes = self.where_from_events()
        cas = [pe.context_agent for pe in pes if pe.context_agent]
        if not cas:
            pts = self.resource_type.producing_process_types()
            cas = [pt.context_agent for pt in pts if pt.context_agent]
        return list(set(cas))

    def shipped_on_orders(self):
        from .types import EventType
        # todo exchange redesign fallout
        orders = []
        # this is insufficient to select shipments
        # sales below is better
        et = EventType.objects.get(name="Give")  # was shipment
        shipments = EconomicEvent.objects.filter(resource=self).filter(event_type=et)
        for ship in shipments:
            if ship.exchange.order:
                orders.append(ship.exchange.order)
        return orders

    def sales(self):
        from .types import EventType
        from .processes import UseCase
        sales = []
        use_case = UseCase.objects.get(identifier="demand_xfer")
        et = EventType.objects.get(name="Give")
        events = EconomicEvent.objects.filter(resource=self).filter(event_type=et)
        for event in events:
            if event.transfer:
                transfer = event.transfer
                if not transfer.is_reciprocal():
                    if transfer.exchange.exchange_type.use_case == use_case:
                        sales.append(event.transfer.exchange)
        return sales

    def value_equations(self):
        ves = []
        # import pdb; pdb.set_trace()
        cas = self.context_agents()
        for ca in cas:
            ca_ves = ca.own_or_parent_value_equations()
            if ca_ves:
                ves.extend(ca_ves)
        return ves

    def value_explanation(self):
        return "Value per unit is composed of the value of the inputs on the next level:"

    def unit_of_quantity(self):
        return self.resource_type.unit

    def formatted_quantity(self):
        unit = self.unit_of_quantity()
        if unit:
            if unit.symbol:
                answer = "".join([unit.symbol, str(self.quantity)])
            else:
                answer = " ".join([str(self.quantity), unit.abbrev])
        else:
            answer = str(self.quantity)
        return answer

    def allow_payout_by(self, agent, user):
        if self.quantity:
            if user.is_superuser:
                return True
        return False

    def payout_form(self, data=None):
        from django_rea.valueaccounting.forms import PayoutForm
        init = {
            "event_date": datetime.date.today(),
            "quantity": self.quantity,
            "max": self.quantity,
        }
        return PayoutForm(prefix=str(self.id), initial=init, data=data)

    def change_form(self):
        from django_rea.valueaccounting.forms import EconomicResourceForm
        # import pdb; pdb.set_trace()
        unit = self.resource_type.unit_of_use
        vpu_help = None
        if unit:
            vpu_help = "Value added when this resource is used for one " + unit.abbrev
        return EconomicResourceForm(instance=self, vpu_help=vpu_help)

    def transform_form(self, data=None):
        # import pdb; pdb.set_trace()
        from django_rea.valueaccounting.forms import TransformEconomicResourceForm
        quantity = self.quantity
        init = {
            "event_date": datetime.date.today(),
            "quantity": self.quantity,
        }
        unit = self.resource_type.unit
        qty_help = ""
        if unit:
            unit_string = unit.abbrev
            qty_help = " ".join(["unit:", unit.abbrev, ", up to 2 decimal places"])
        return TransformEconomicResourceForm(qty_help=qty_help, prefix=self.form_prefix(), initial=init, data=data)

    # def change_role_formset(self):
    #    from django_rea.valueaccounting.forms import ResourceRoleAgentForm
    #    return EconomicResourceForm(instance=self)

    def event_sequence(self):
        # import pdb; pdb.set_trace()
        events = self.events.all()
        data = {}
        visited = set()
        for e in events:
            if e not in visited:
                visited.add(e)
                candidates = e.previous_events()
                prevs = set()
                for cand in candidates:
                    # if cand not in visited:
                    #    visited.add(cand)
                    prevs.add(cand)
                data[e] = prevs
        # import pdb; pdb.set_trace()
        return toposort_flatten(data)

    def test_rollup(self, value_equation=None):
        # leave the following line uncommented
        import pdb;
        pdb.set_trace()
        visited = set()
        path = []
        depth = 0
        value_per_unit = self.roll_up_value(path, depth, visited, value_equation)
        print("value_per_unit:", value_per_unit)
        return path

    def compute_value_per_unit(self, value_equation=None):
        # import pdb; pdb.set_trace()
        visited = set()
        path = []
        depth = 0
        return self.roll_up_value(path, depth, visited, value_equation)

    def roll_up_value(self, path, depth, visited, value_equation=None):
        # EconomicResource method
        # import pdb; pdb.set_trace()
        # Value_per_unit will be the result of this method.
        depth += 1
        self.depth = depth
        # self.explanation = "Value per unit consists of all the input values on the next level"
        path.append(self)
        value_per_unit = Decimal("0.0")
        # Values of all of the inputs will be added to this list.
        values = []
        # Resource contributions use event.value.
        contributions = self.resource_contribution_events()
        for evt in contributions:
            value = evt.value
            if value_equation:
                br = evt.bucket_rule(value_equation)
                if br:
                    # import pdb; pdb.set_trace()
                    value = br.compute_claim_value(evt)
            evt_vpu = value / evt.quantity
            if evt_vpu:
                values.append([evt_vpu, evt.quantity])
                # padding = ""
                # for x in range(0,depth):
                #    padding += "."
                # print padding, depth, evt.id, evt
                # print padding, "--- evt_vpu: ", evt_vpu
                # print padding, "--- values:", values
            depth += 1
            evt.depth = depth
            path.append(evt)
            depth -= 1
            # todo br: use
            # br = evt.bucket_rule(value_equation)
        # Purchase contributions use event.value.
        # todo dhen_bug: only buys for the same exchange_stage count
        # also, need to get transfers for the same exchange_stage
        # probably also need to chase historical_stage
        buys = self.purchase_events_for_exchange_stage()
        for evt in buys:
            # import pdb; pdb.set_trace()
            depth += 1
            evt.depth = depth
            path.append(evt)
            value = evt.value
            if evt.transfer:
                if evt.transfer.exchange:
                    # print "value b4:", value
                    exchange = evt.transfer.exchange
                    value = exchange.roll_up_value(evt, path, depth, visited, value_equation)
                    # print "value after:", value
            evt_vpu = value / evt.quantity
            if evt_vpu:
                values.append([evt_vpu, evt.quantity])
                # padding = ""
                # for x in range(0,depth):
                #    padding += "."
                # print padding, depth, evt.id, evt
                # print padding, "--- evt_vpu: ", evt_vpu
                # print padding, "--- values:", values
            depth -= 1
        # todo exchange redesign fallout
        # this is obsolete
        """
        xfers = self.transfer_events_for_exchange_stage()
        for evt in xfers:
            #import pdb; pdb.set_trace()
            depth += 1
            evt.depth = depth
            path.append(evt)
            value = evt.value
            if evt.exchange:
                #print "value b4:", value
                value = evt.exchange.roll_up_value(evt, path, depth, visited, value_equation)
                #print "value after:", value
            evt_vpu = value / evt.quantity
            if evt_vpu:
                values.append([evt_vpu, evt.quantity])
                #padding = ""
                #for x in range(0,depth):
                #    padding += "."
                #print padding, depth, evt.id, evt
                #print padding, "--- evt_vpu: ", evt_vpu
                #print padding, "--- values:", values
            depth -= 1
        """
        citations = []
        production_value = Decimal("0.0")
        # rollup stage change
        processes = self.producing_processes_for_historical_stage()
        for process in processes:
            pe_value = Decimal("0.0")
            if process not in visited:
                visited.add(process)
                depth += 1
                process.depth = depth
                # todo share: credit for production events?
                # todo: eliminate production for other resources
                production_qty = process.production_quantity()
                path.append(process)
                # depth += 1
                if production_qty:
                    inputs = process.incoming_events()
                    for ip in inputs:
                        # Work contributions use resource_type.value_per_unit
                        if ip.event_type.relationship == "work":
                            # import pdb; pdb.set_trace()
                            value = ip.quantity * ip.value_per_unit()
                            if value_equation:
                                br = ip.bucket_rule(value_equation)
                                if br:
                                    # value_b4 = value
                                    value = br.compute_claim_value(ip)
                                    # print br.id, br
                                    # print ip
                                    # print "--- value b4:", value_b4, "value after:", value
                            ip.value = value
                            ip.save()
                            pe_value += value
                            # padding = ""
                            # for x in range(0,depth):
                            #    padding += "."
                            # print padding, depth, ip.id, ip
                            # print padding, "--- ip.value: ", ip.value
                            # print padding, "--- pe_value:", pe_value
                            ip.depth = depth
                            path.append(ip)
                        # Use contributions use resource value_per_unit_of_use.
                        elif ip.event_type.relationship == "use":
                            # import pdb; pdb.set_trace()
                            if ip.resource:
                                # price changes
                                if ip.price:
                                    ip.value = ip.price
                                else:
                                    ip.value = ip.quantity * ip.resource.value_per_unit_of_use
                                ip.save()
                                pe_value += ip.value
                                # padding = ""
                                # for x in range(0,depth):
                                #    padding += "."
                                # print padding, depth, ip.id, ip
                                # print padding, "--- ip.value: ", ip.value
                                # print padding, "--- pe_value:", pe_value
                                ip.depth = depth
                                path.append(ip)
                                ip.resource.roll_up_value(path, depth, visited, value_equation)
                                # br = ip.bucket_rule(value_equation)
                        # Consume contributions use resource rolled up value_per_unit
                        elif ip.event_type.relationship == "consume" or ip.event_type.name == "To Be Changed":
                            ip.depth = depth
                            path.append(ip)
                            # rollup stage change
                            # this is where it starts (I think)
                            value_per_unit = ip.roll_up_value(path, depth, visited, value_equation)
                            ip.value = ip.quantity * value_per_unit
                            ip.save()
                            pe_value += ip.value
                            # padding = ""
                            # for x in range(0,depth):
                            #    padding += "."
                            # print padding, depth, ip.id, ip
                            # print padding, "--- ip.value: ", ip.value
                            # print padding, "--- pe_value:", pe_value
                        # Citations valued later, after all other inputs added up
                        elif ip.event_type.relationship == "cite":
                            ip.depth = depth
                            path.append(ip)
                            if ip.resource_type.unit_of_use:
                                if ip.resource_type.unit_of_use.unit_type == "percent":
                                    citations.append(ip)
                            else:
                                ip.value = ip.quantity
                                pe_value += ip.value

                                # padding = ""
                                # for x in range(0,depth):
                                #    padding += "."
                                # print padding, depth, ip.id, ip
                                # print padding, "--- ip.value: ", ip.value
                                # print padding, "--- pe_value:", pe_value
                            if ip.resource:
                                ip.resource.roll_up_value(path, depth, visited, value_equation)
            production_value += pe_value
        if production_value:
            # Citations use percentage of the sum of other input values.
            for c in citations:
                percentage = c.quantity / 100
                c.value = production_value * percentage
                c.save()
            for c in citations:
                production_value += c.value
                # padding = ""
                # for x in range(0,depth):
                #    padding += "."
                # print padding, depth, c.id, c
                # print padding, "--- c.value: ", c.value
                # print padding, "--- production_value:", production_value
        if production_value and production_qty:
            # print "production value:", production_value, "production qty", production_qty
            production_value_per_unit = production_value / production_qty
            values.append([production_value_per_unit, production_qty])
        # If many sources of value, compute a weighted average.
        # Multiple sources cd be:
        #    resource contributions, purchases, and multiple production processes.
        if values:
            if len(values) == 1:
                value_per_unit = values[0][0]
            else:
                # compute weighted average
                weighted_values = sum(v[0] * v[1] for v in values)
                weights = sum(v[1] for v in values)
                if weighted_values and weights:
                    value_per_unit = weighted_values / weights
        self.value_per_unit = value_per_unit.quantize(Decimal('.01'), rounding=ROUND_UP)
        self.save()
        # padding = ""
        # for x in range(0,depth):
        #    padding += "."
        # print padding, depth, self.id, self, "value_per_unit:", self.value_per_unit
        return self.value_per_unit

    def rollup_explanation(self):
        depth = -1
        visited = set()
        path = []
        queue = []
        # import pdb; pdb.set_trace()
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
                            if ip.resource:
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
            # todo: make sure this works for >1 process producing the same resource
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
                            # depth += 1
                            if ip.resource:
                                ip.resource.direct_value_components(components, visited, depth)
                                # depth += 1
                        elif ip.event_type.relationship == "cite":
                            ip.depth = depth
                            components.append(ip)

    def test_compute_income_shares(self, value_equation):
        visited = set()
        path = []
        depth = 0
        # value_per_unit = self.roll_up_value(path, depth, visited, value_equation)
        # print "value_per_unit:", value_per_unit
        # value = self.quantity * value_per_unit
        visited = set()
        shares = []
        # import pdb; pdb.set_trace()
        quantity = self.quantity or Decimal("1.0")
        self.compute_income_shares(value_equation, quantity, shares, visited)
        total = sum(s.share for s in shares)
        for s in shares:
            s.fraction = s.share / total
        # import pdb; pdb.set_trace()
        # print "total shares:", total
        return shares

    def compute_shipment_income_shares(self, value_equation, quantity):
        # visited = set()
        # path = []
        # depth = 0
        # value_per_unit = self.roll_up_value(path, depth, visited, value_equation)
        # print "value_per_unit:", value_per_unit
        # value = quantity * value_per_unit
        visited = set()
        shares = []
        # import pdb; pdb.set_trace()
        self.compute_income_shares(value_equation, quantity, shares, visited)
        total = sum(s.share for s in shares)
        # todo: bob: total was zero, unclear if bad data; unclear what fraction should be in that case
        if total:
            for s in shares:
                s.fraction = s.share / total
        else:
            for s in shares:
                s.fraction = 1
        # import pdb; pdb.set_trace()
        # print "total shares:", total
        return shares

    def compute_income_shares(self, value_equation, quantity, events, visited):
        # Resource method
        # print "Resource:", self.id, self
        # print "running quantity:", quantity, "running value:", value
        # import pdb; pdb.set_trace()
        contributions = self.resource_contribution_events()
        for evt in contributions:
            br = evt.bucket_rule(value_equation)
            value = evt.value
            if br:
                # import pdb; pdb.set_trace()
                value = br.compute_claim_value(evt)
            if value:
                vpu = value / evt.quantity
                evt.share = quantity * vpu
                events.append(evt)
                # print evt.id, evt, evt.share
                # print "----Event.share:", evt.share, "= evt.value:", evt.value
        # import pdb; pdb.set_trace()
        # purchases of resources in value flow can be contributions
        buys = self.purchase_events()
        for evt in buys:
            # import pdb; pdb.set_trace()
            # if evt.value:
            #    vpu = evt.value / evt.quantity
            #    evt.share = quantity * vpu
            #    events.append(evt)
            if evt.exchange:
                evt.exchange.compute_income_shares(value_equation, evt, quantity, events, visited)
        # todo exchange redesign fallout
        # change transfer_events, that method is obsolete
        # import pdb; pdb.set_trace()
        # xfers = self.transfer_events()
        # for evt in xfers:
        #    if evt.exchange:
        #       evt.exchange.compute_income_shares(value_equation, evt, quantity, events, visited)
        # import pdb; pdb.set_trace()
        # income_shares stage change
        processes = self.producing_processes_for_historical_stage()
        try:
            stage = self.historical_stage
        except AttributeError:
            if self.stage:
                processes = [p for p in processes if p.process_type == self.stage]
        for process in processes:
            if process not in visited:
                visited.add(process)
                if quantity:
                    # todo: how will this work for >1 processes producing the same resource?
                    # what will happen to the shares of the inputs of the later processes?
                    production_events = [e for e in process.production_events() if e.resource == self]
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
                        # todo br
                        # import pdb; pdb.set_trace()
                        value = pe.quantity
                        br = pe.bucket_rule(value_equation)
                        if br:
                            # import pdb; pdb.set_trace()
                            value = br.compute_claim_value(pe)
                        pe.share = value * distro_fraction
                        pe.value = value
                        events.append(pe)
                    # import pdb; pdb.set_trace()
                    if process.context_agent.compatible_value_equation(value_equation):
                        inputs = process.incoming_events()
                        for ip in inputs:
                            # we assume here that work events are contributions
                            if ip.event_type.relationship == "work":
                                # import pdb; pdb.set_trace()
                                if ip.is_contribution:
                                    value = ip.value
                                    br = ip.bucket_rule(value_equation)
                                    if br:
                                        # import pdb; pdb.set_trace()
                                        value = br.compute_claim_value(ip)
                                        ip.value = value
                                    ip.share = value * distro_fraction
                                    events.append(ip)
                                    # print ip.id, ip, ip.share
                                    # print "----Event.share:", ip.share, "= Event.value:", ip.value, "* distro_fraction:", distro_fraction
                            elif ip.event_type.relationship == "use":
                                # use events are not contributions, but their resources may have contributions
                                # equip logging changes
                                # import pdb; pdb.set_trace()
                                if ip.resource:
                                    # price changes
                                    if ip.price:
                                        ip.value = ip.price
                                    else:
                                        ip.value = ip.quantity * ip.resource.value_per_unit_of_use
                                    ip.save()

                                    # experiment for equipment maintenance fee
                                    # ip.share = ip.value
                                    # events.append(ip)

                                    value = ip.value
                                    ip_value = value * distro_fraction
                                    d_qty = distro_qty
                                    if ip_value and value:
                                        d_qty = ip_value / value
                                    # d_qty may be the wrong qty to pass into compute_income_shares
                                    # and compute_income_shares may be the wrong method anyway
                                    # Maybe a use event method?
                                    # What we want to do is pass the ip_value down to the exchange...
                                    # Conceptually, we are distributing ip_value to the contributors to the resource!
                                    new_visited = set()
                                    path = []
                                    depth = 0
                                    resource_value = ip.resource.roll_up_value(path, depth, new_visited, value_equation)
                                    ip.resource.compute_income_shares_for_use(value_equation, ip, ip_value,
                                                                              resource_value, events, visited)
                            elif ip.event_type.relationship == "consume" or ip.event_type.name == "To Be Changed":
                                # consume events are not contributions, but their resources may have contributions
                                # equip logging changes
                                new_visited = set()
                                path = []
                                depth = 0

                                value_per_unit = ip.roll_up_value(path, depth, new_visited, value_equation)
                                ip.value = ip.quantity * value_per_unit
                                ip.save()
                                ip_value = ip.value * distro_fraction
                                d_qty = ip.quantity * distro_fraction
                                # if ip_value:
                                # print "consumption:", ip.id, ip, "ip.value:", ip.value
                                # print "----value:", ip_value, "d_qty:", d_qty, "distro_fraction:", distro_fraction
                                if ip.resource:
                                    # income_shares stage change
                                    ip.compute_income_shares(value_equation, d_qty, events, visited)
                            elif ip.event_type.relationship == "cite":
                                # import pdb; pdb.set_trace()
                                # citation events are not contributions, but their resources may have contributions
                                if ip.resource:
                                    # equip logging changes
                                    if ip.resource_type.unit_of_use:
                                        if ip.resource_type.unit_of_use.unit_type == "percent":
                                            citations.append(ip)
                                    else:
                                        ip.value = ip.quantity
                                    ip.save()
                                    value = ip.value
                                    ip_value = value * distro_fraction
                                    d_qty = distro_qty
                                    if ip_value and value:
                                        d_qty = ip_value / value
                                    # if ip.resource:
                                    #    ip.resource.compute_income_shares(value_equation, d_qty, events, visited)
                                    new_visited = set()
                                    path = []
                                    depth = 0
                                    resource_value = ip.resource.roll_up_value(path, depth, new_visited, value_equation)
                                    ip.resource.compute_income_shares_for_use(value_equation, ip, ip_value,
                                                                              resource_value, events, visited)

    def compute_income_shares_for_use(self, value_equation, use_event, use_value, resource_value, events, visited):
        # Resource method
        # import pdb; pdb.set_trace()
        contributions = self.resource_contribution_events()
        for evt in contributions:
            # todo exchange redesign fallout
            # import pdb; pdb.set_trace()
            br = evt.bucket_rule(value_equation)
            value = evt.value
            if br:
                value = br.compute_claim_value(evt)
            if value:
                vpu = value / evt.quantity
                evt.share = min(vpu, use_value)
                events.append(evt)
        buys = self.purchase_events()
        for evt in buys:
            # this is because purchase_events will duplicate resource_contribution_events
            if evt not in events:
                if evt.exchange:
                    evt.exchange.compute_income_shares_for_use(value_equation, use_event, use_value, resource_value,
                                                               events, visited)
        processes = self.producing_processes()
        # shd only be one producing process for a used resource..right?
        quantity = self.quantity
        for process in processes:
            if process not in visited:
                visited.add(process)
                if quantity:
                    # todo: how will this work for >1 processes producing the same resource?
                    # what will happen to the shares of the inputs of the later processes?
                    production_events = process.production_events()
                    produced_qty = sum(pe.quantity for pe in production_events)
                    # todo 3d: how to compute?
                    # this fraction stuff only applies to shipped qties
                    # which do not apply here...
                    distro_fraction = 1
                    distro_qty = quantity
                    if produced_qty > quantity:
                        distro_fraction = quantity / produced_qty
                        quantity = Decimal("0.0")
                    elif produced_qty <= quantity:
                        distro_qty = produced_qty
                        quantity -= produced_qty
                    for pe in production_events:
                        value = pe.quantity
                        br = pe.bucket_rule(value_equation)
                        if br:
                            value = br.compute_claim_value(pe)
                        # todo 3d: how to compute?
                        pe.share = value * distro_fraction
                        events.append(pe)
                    if process.context_agent.compatible_value_equation(value_equation):
                        inputs = process.incoming_events()
                        for ip in inputs:
                            # we assume here that work events are contributions
                            if ip.event_type.relationship == "work":
                                if ip.is_contribution:
                                    value = ip.value
                                    br = ip.bucket_rule(value_equation)
                                    if br:
                                        value = br.compute_claim_value(ip)
                                        ip.value = value
                                    # todo 3d: changed
                                    # import pdb; pdb.set_trace()
                                    fraction = ip.value / resource_value
                                    ip.share = use_value * fraction
                                    # ip.share = value * distro_fraction
                                    events.append(ip)
                            elif ip.event_type.relationship == "use":
                                # use events are not contributions, but their resources may have contributions
                                if ip.resource:
                                    # price changes
                                    if ip.price:
                                        ip.value = ip.price
                                    else:
                                        ip.value = ip.quantity * ip.resource.value_per_unit_of_use
                                    value = ip.value
                                    ip_value = value * distro_fraction
                                    d_qty = distro_qty
                                    if ip_value and value:
                                        d_qty = ip_value / value
                                    ip.resource.compute_income_shares_for_use(value_equation, ip, ip_value,
                                                                              resource_value, events, visited)
                            elif ip.event_type.relationship == "consume" or ip.event_type.name == "To Be Changed":
                                # consume events are not contributions, but their resources may have contributions
                                ip_value = ip.value * distro_fraction
                                d_qty = ip.quantity * distro_fraction
                                if ip.resource:
                                    ip.resource.compute_income_shares(value_equation, d_qty, events, visited)
                            elif ip.event_type.relationship == "cite":
                                # citation events are not contributions, but their resources may have contributions
                                # todo: use percent or compute_income_shares_for_use?
                                # value = ip.value
                                # ip_value = value * distro_fraction
                                # d_qty = distro_qty
                                # if ip_value and value:
                                #    d_qty = ip_value / value
                                # if ip.resource:
                                #    ip.resource.compute_income_shares(value_equation, d_qty, events, visited)
                                if ip.resource:
                                    value = ip.value
                                    ip_value = value * distro_fraction
                                    d_qty = distro_qty
                                    if ip_value and value:
                                        d_qty = ip_value / value
                                    new_visited = set()
                                    path = []
                                    depth = 0
                                    resource_value = ip.resource.roll_up_value(path, depth, new_visited, value_equation)
                                    ip.resource.compute_income_shares_for_use(value_equation, ip, ip_value,
                                                                              resource_value, events, visited)

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
                            # depth += 1
                            if ip.resource:
                                ip.resource.direct_value_components(components, visited, depth)
                                # depth += 1
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
        # rollup stage change
        pes = self.producing_events()
        processes = [pe.process for pe in pes if pe.process]
        processes = list(set(processes))
        if self.stage:
            try:
                processes = [p for p in processes if p.process_type == self.historical_stage]
            except AttributeError:
                processes = [p for p in processes if p.process_type == self.stage]
        return processes

    def producing_events_for_historical_stage(self):
        pes = self.producing_events()
        if self.stage:
            try:
                pes = [pe for pe in pes if pe.process and pe.process.process_type == self.historical_stage]
            except AttributeError:
                pes = [pe for pe in pes if pe.process and pe.process.process_type == self.stage]
        return pes

    def where_from_events(self):
        # todo exchange redesign fallout
        # these are all obsolete
        return self.events.filter(
            Q(event_type__relationship='out') | Q(event_type__relationship='receive') | Q(
                event_type__relationship='receivecash')
            | Q(event_type__relationship='cash') | Q(event_type__relationship='resource') | Q(
                event_type__relationship='change')
            | Q(event_type__relationship='distribute') | Q(event_type__relationship='available') | Q(
                event_type__relationship='transfer'))

    # todo: add transfer?
    def where_to_events(self):
        # todo exchange redesign fallout
        # shipment is obsolete
        return self.events.filter(
            Q(event_type__relationship='in') | Q(event_type__relationship='consume') | Q(event_type__relationship='use')
            | Q(event_type__relationship='cite') | Q(event_type__relationship='pay') | Q(
                event_type__relationship='shipment')
            | Q(event_type__relationship='shipment') | Q(event_type__relationship='disburse'))

    def last_exchange_event(self):  # todo: could a resource ever go thru the same exchange stage more than once?
        # import pdb; pdb.set_trace()
        # todo: this works for the moment because I'm storing exchange stage in the resource even if it came out of a process last (dhen)
        events = self.where_from_events().filter(exchange_stage=self.exchange_stage)
        if events:
            return events[0]
        else:
            return None

    def owner_based_on_exchange(self):
        event = self.last_exchange_event()
        if event:
            return event.to_agent
        else:
            return None

    def consuming_events(self):
        return self.events.filter(event_type__relationship='consume')

    def using_events(self):
        return self.events.filter(event_type__relationship="use")

    def resource_contribution_events(self):
        return self.events.filter(is_contribution=True)

    def cash_events(self):  # includes cash contributions, donations and loans
        # todo exchange redesign fallout
        rct_et = EventType.objects.get(name="Receive")
        with_xfer = [event for event in self.events.all() if event.transfer and event.event_type == rct_et]
        currencies = [event for event in with_xfer if event.transfer.transfer_type.is_currency]
        return currencies

    def cash_contribution_events(self):  # includes only cash contributions
        # todo exchange redesign fallout
        # import pdb; pdb.set_trace()
        from .types import EventType
        rct_et = EventType.objects.get(name="Receive")
        with_xfer = [event for event in self.events.all() if event.transfer and event.event_type == rct_et]
        contributions = [event for event in with_xfer if event.is_contribution]
        currencies = [event for event in contributions if event.transfer.transfer_type.is_currency]
        return currencies

    def purchase_events(self):
        # todo exchange redesign fallout
        # is this correct?
        from .types import EventType
        rct_et = EventType.objects.get(name="Receive")
        return self.events.filter(event_type=rct_et, is_contribution=False)

    def purchase_events_for_exchange_stage(self):
        # import pdb; pdb.set_trace()
        if self.exchange_stage:
            return self.purchase_events().filter(exchange_stage=self.exchange_stage)
        else:
            return self.purchase_events()

    def transfer_events(self):
        # obsolete
        # todo exchange redesign fallout
        print("obsolete resource.transfer_event")
        # import pdb; pdb.set_trace()
        from .types import EventType
        tx_et = EventType.objects.get(name="Receive")
        return self.events.filter(event_type=tx_et)

    def transfer_events_for_exchange_stage(self):
        # obsolete
        # todo exchange redesign fallout
        if self.exchange_stage:
            return self.transfer_events().filter(exchange_stage=self.exchange_stage)
        else:
            return self.transfer_events()

    def available_events(self):
        from .types import EventType
        av_et = EventType.objects.get(name="Make Available")
        return self.events.filter(event_type=av_et)

    def all_usage_events(self):
        # todo exchange redesign fallout
        # cash is obsolete
        return self.events.exclude(event_type__relationship="out").exclude(event_type__relationship="receive").exclude(
            event_type__relationship="resource").exclude(event_type__relationship="cash")

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
                if resource:
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
        visited = set()
        depth = 0
        self.depth = depth
        flows.append(self)
        self.incoming_value_flows_dfs(flows, visited, depth)
        return flows

    def process_exchange_flow(self):
        from .processes import Process
        from .trade import Exchange
        flows = self.incoming_value_flows()
        xnp = [f for f in flows if type(f) is Process or type(f) is Exchange]
        # import pdb; pdb.set_trace()
        for x in xnp:
            if type(x) is Process:
                x.type = "Process"
                x.stage = x.process_type
            else:
                x.type = "Exchange"
                x.stage = x.exchange_type
        return xnp

    def incoming_value_flows_dfs(self, flows, visited, depth):
        from .types import EventType
        # Resource method
        # import pdb; pdb.set_trace()
        if self not in visited:
            visited.add(self)
            resources = []
            events = self.event_sequence()
            events.reverse()
            pet = EventType.objects.get(name="Resource Production")
            # todo exchange redesign fallout
            # xet = EventType.objects.get(name="Transfer")
            # xfer events no longer exist
            # rcpt = EventType.objects.get(name="Receipt")
            rcpt = EventType.objects.get(name="Receive")

            for event in events:
                if event not in visited:
                    visited.add(event)
                    depth += 1
                    event.depth = depth
                    flows.append(event)
                    if event.event_type == rcpt:
                        if event.transfer:
                            exchange = event.transfer.exchange
                            if exchange:
                                if exchange not in visited:
                                    visited.add(exchange)
                                    exchange.depth = depth + 1
                                    flows.append(exchange)
                                    # todo exchange redesign fallout
                                    for pmt in exchange.reciprocal_transfer_events():
                                        pmt.depth = depth + 2
                                        flows.append(pmt)
                        event.incoming_value_flows_dfs(flows, visited, depth)
                    elif event.event_type == pet:
                        process = event.process
                        if process:
                            if process not in visited:
                                visited.add(process)
                                process.depth = depth + 1
                                flows.append(process)
                                for evt in process.incoming_events():
                                    if evt not in visited:
                                        visited.add(evt)
                                        evt.depth = depth + 2
                                        flows.append(evt)
                                        if evt.resource:
                                            if evt.resource == self:
                                                if self.stage and evt.stage:
                                                    self.historical_stage = evt.stage
                                                    self.incoming_value_flows_dfs(flows, visited, depth + 2)
                                            elif evt.resource not in resources:
                                                resources.append(evt.resource)

            for event in self.purchase_events_for_exchange_stage():
                if event not in visited:
                    visited.add(event)
                    event.depth = depth
                    flows.append(event)
                    if event.exchange:
                        exchange = event.exchange
                        exchange.depth = depth + 1
                        flows.append(exchange)
                        for pmt in event.exchange.payment_events():
                            pmt.depth = depth + 2
                            flows.append(pmt)

            for event in self.resource_contribution_events():
                if event not in visited:
                    visited.add(event)
                    event.depth = depth
                    flows.append(event)

            for resource in resources:
                resource.depth = depth + 3
                flows.append(resource)
                resource.incoming_value_flows_dfs(flows, visited, depth + 3)

    def incoming_events(self):
        flows = self.incoming_value_flows()
        events = []
        for flow in flows:
            if type(flow) is EconomicEvent:
                if flow not in events:
                    events.append(flow)
        return events

    def possible_root_events(self):
        root_names = ['Create Changeable', 'Resource Production', 'Receipt', 'Make Available']
        return self.events.filter(event_type__name__in=root_names)

    def value_flow_going_forward(self):
        # todo: needs rework, see next method
        # import pdb; pdb.set_trace()
        flows = []
        visited = set()
        depth = 0
        self.depth = depth
        flows.append(self)
        self.value_flow_going_forward_dfs(flows, visited, depth)
        events = self.possible_root_events()
        if events:
            processes = []
            exchanges = []
            for event in events:
                flows.insert(0, event)
                if event.process:
                    if event.process not in processes:
                        processes.append(event.process)
                if event.exchange:
                    if event.exchange not in exchanges:
                        exchanges.append(event.exchange)
            for process in processes:
                flows.insert(0, process)
            for exchange in exchanges:
                flows.insert(0, exchange)
        return flows

    def value_flow_going_forward_dfs(self, flows, visited, depth):
        # import pdb; pdb.set_trace()
        if not self in visited:
            visited.add(self)
            depth += 1
            # todo: this will break, depends on event creation order
            # also, all_usage_events does not include transfers
            # and, needs to consider stage and exchange_stage
            for event in self.all_usage_events().order_by("id"):
                event.depth = depth
                flows.append(event)
                proc = event.process
                exch = event.exchange
                if proc:
                    if not proc in visited:
                        visited.add(proc)
                        depth += 1
                        proc.depth = depth
                        flows.append(proc)
                        depth += 1
                        for evt in proc.production_events():
                            evt.depth = depth
                            flows.append(evt)
                            resource = evt.resource
                            if resource:
                                if resource not in flows:
                                    flows.append(resource)
                                    resource.value_flow_going_forward_dfs(flows, visited, depth)
                if exch:
                    if not exch in visited:
                        visited.add(exch)
                        depth += 1
                        exch.depth = depth
                        flows.append(exch)
                        depth += 1
                        # todo: transfers will be trouble...
                        # import pdb; pdb.set_trace()
                        # for evt in exch.production_events():
                        #    evt.depth = depth
                        #    flows.append(evt)
                        #    if evt.resource:
                        #        evt.resource.value_flow_going_forward_dfs(flows, visited, depth)

    def forward_flow(self):
        flows = []
        visited = []
        depth = 0
        self.depth = depth
        flows.append(self)
        usage_events = self.all_usage_events()
        # import pdb; pdb.set_trace()

    def staged_process_sequence_beyond_workflow(self):
        # todo: this was created for a DHen report
        # but does not work yet because the converted data
        # has no commitments
        # Plus, it can't be tested and so probably won't work.
        # also, needs to include exchanges
        processes = []
        if not self.stage:
            return processes
        creation_event = None
        # import pdb; pdb.set_trace()
        events = self.possible_root_events()
        if events:
            creation_event = events[0]
        if not creation_event:
            return processes
        if creation_event.process:
            creation_event.follow_process_chain_beyond_workflow(processes, all_events)

    def value_flow_going_forward_processes(self):
        # import pdb; pdb.set_trace()
        from .processes import Process
        in_out = self.value_flow_going_forward()
        processes = []
        for index, io in enumerate(in_out):
            if type(io) is Process:
                if io.input_includes_resource(self):
                    processes.append(io)
        return processes

    def receipt(self):
        from .types import EventType
        in_out = self.value_flow_going_forward()
        receipt = None
        et = EventType.objects.get(name='Receive')
        for index, io in enumerate(in_out):
            if type(io) is EconomicEvent:
                if io.event_type == et:
                    receipt = io
        return receipt

    def form_prefix(self):
        return "-".join(["RES", str(self.id)])

    def consumption_event_form(self):
        from django_rea.valueaccounting.forms import InputEventForm
        prefix = self.form_prefix()
        qty_help = " ".join(["unit:", self.unit_of_quantity().abbrev, ", up to 2 decimal places"])
        init = {"quantity": self.quantity, }
        return InputEventForm(qty_help=qty_help, prefix=prefix, initial=init)

    def use_event_form(self, data=None):
        from django_rea.valueaccounting.forms import InputEventForm
        prefix = self.form_prefix()
        unit = self.resource_type.directional_unit("use")
        qty_help = " ".join(["unit:", unit.abbrev, ", up to 2 decimal places"])
        return InputEventForm(qty_help=qty_help, prefix=prefix, data=data)

    def cite_event_form(self, data=None):
        from django_rea.valueaccounting.forms import InputEventForm
        prefix = self.form_prefix()
        unit = self.resource_type.directional_unit("cite")
        qty_help = " ".join(["unit:", unit.abbrev, ", up to 2 decimal places"])
        return InputEventForm(qty_help=qty_help, prefix=prefix, data=data)

    def input_event_form(self, data=None):
        from django_rea.valueaccounting.forms import InputEventForm
        prefix = self.form_prefix()
        qty_help = " ".join(["unit:", self.unit_of_quantity().abbrev, ", up to 2 decimal places"])
        return InputEventForm(qty_help=qty_help, prefix=prefix, data=data)

    def owner(self):  # returns first owner
        # owner_roles = self.agent_resource_roles.filter(role__is_owner=True)
        # if owner_roles:
        #    return owner_roles[0].agent
        owners = self.owners()
        if owners:
            return owners[0]
        else:
            return None

    def owners(self):
        # todo faircoin: possible problem with multiple owners of faircoin_resources?
        # mitigated by requiring owner or superuser to change faircoin resource
        return [arr.agent for arr in self.agent_resource_roles.filter(role__is_owner=True)]

    def is_virtual_account_of(self, agent):
        if self.resource_type.is_virtual_account():
            owners = [arr.agent for arr in self.agent_resource_roles.filter(role__is_owner=True)]
            if agent in owners:
                return True
        return False

    def all_owners(self):
        owner_assns = self.agent_resource_roles.filter(role__is_owner=True)
        owners = []
        for own in owner_assns:
            owners.append(own.agent.nick)
        return owners

    def all_contacts(self):
        return self.agent_resource_roles.filter(is_contact=True)

    def all_related_agents(self):
        # import pdb; pdb.set_trace()
        arrs = self.agent_resource_roles.all()
        agent_ids = []
        for arr in arrs:
            agent_ids.append(arr.agent.id)
        return EconomicAgent.objects.filter(pk__in=agent_ids)

    def related_agents(self, role):
        # import pdb; pdb.set_trace()
        arrs = self.agent_resource_roles.filter(role=role)
        agent_ids = []
        for arr in arrs:
            agent_ids.append(arr.agent.id)
        return EconomicAgent.objects.filter(pk__in=agent_ids)

    def equipment_users(self, context_agent):
        agent_list = context_agent.context_equipment_users()
        agent_list.extend([arr.agent for arr in self.agent_resource_roles.all()])
        agent_ids = [agent.id for agent in agent_list]
        return EconomicAgent.objects.filter(pk__in=agent_ids)

    def payout_contacts(self):
        """ this method only applies to virtual account resources """
        distributions = self.distribution_events()
        contacts = []
        for d in distributions:
            dex = d.exchange
            disbursements = dex.disbursement_events()
            for dis in disbursements:
                contacts.extend(dis.resource.all_contacts())
        return contacts

    def distribution_events(self):
        return self.events.filter(
            event_type__relationship='distribute')

    def disbursement_events(self):
        return self.events.filter(
            event_type__relationship='disburse')

    def revert_to_previous_stage(self):
        # import pdb; pdb.set_trace()
        current_stage = self.stage
        cts, inheritance = self.resource_type.staged_commitment_type_sequence()
        for ct in cts:
            if ct.stage == current_stage:
                break
            prev_stage = ct.stage
        self.stage = prev_stage
        self.save()
        return prev_stage


TX_STATE_CHOICES = (
    ('new', _('New')),
    ('pending', _('Pending')),
    ('broadcast', _('Broadcast')),
    ('confirmed', _('Confirmed')),
)


class EconomicEventManager(models.Manager):
    def virtual_account_events(self, start_date=None, end_date=None):
        if start_date and end_date:
            events = EconomicEvent.objects.filter(resource__resource_type__behavior="account",
                                                  event_date__gte=start_date, event_date__lte=end_date)
        elif start_date:
            events = EconomicEvent.objects.filter(resource__resource_type__behavior="account",
                                                  event_date__gte=start_date)
        elif end_date:
            events = EconomicEvent.objects.filter(resource__resource_type__behavior="account", event_date__lte=end_date)
        else:
            events = EconomicEvent.objects.filter(resource__resource_type__behavior="account")
        return events

    def contributions(self):
        return EconomicEvent.objects.filter(is_contribution=True)


def update_summary(agent, context_agent, resource_type, event_type):
    from .behavior import CachedEventSummary
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


@python_2_unicode_compatible
class EconomicEvent(models.Model):
    event_type = models.ForeignKey("EventType",
                                   related_name="events", verbose_name=_('event type'))
    event_date = models.DateField(_('event date'))
    from_agent = models.ForeignKey("EconomicAgent",
                                   blank=True, null=True,
                                   related_name="given_events", verbose_name=_('from'))
    to_agent = models.ForeignKey("EconomicAgent",
                                 blank=True, null=True,
                                 related_name="taken_events", verbose_name=_('to'))
    resource_type = models.ForeignKey("EconomicResourceType",
                                      verbose_name=_('resource type'), related_name='events')
    resource = models.ForeignKey("EconomicResource",
                                 blank=True, null=True,
                                 verbose_name=_('resource'), related_name='events')
    exchange_stage = models.ForeignKey("ExchangeType", related_name="events_creating_exchange_stage",
                                       verbose_name=_('exchange stage'), blank=True, null=True)
    process = models.ForeignKey("Process",
                                blank=True, null=True,
                                verbose_name=_('process'), related_name='events',
                                on_delete=models.SET_NULL)
    exchange = models.ForeignKey("Exchange",
                                 blank=True, null=True,
                                 verbose_name=_('exchange'), related_name='events',
                                 on_delete=models.SET_NULL)
    transfer = models.ForeignKey("Transfer",
                                 blank=True, null=True,
                                 related_name="events", verbose_name=_('transfer'),
                                 on_delete=models.SET_NULL)
    distribution = models.ForeignKey("Distribution",
                                     blank=True, null=True,
                                     related_name="events", verbose_name=_('distribution'),
                                     on_delete=models.SET_NULL)
    context_agent = models.ForeignKey("EconomicAgent",
                                      blank=True, null=True,
                                      limit_choices_to={"is_context": True, },
                                      related_name="events", verbose_name=_('context agent'),
                                      on_delete=models.SET_NULL)
    url = models.CharField(_('url'), max_length=255, blank=True)
    description = models.TextField(_('description'), null=True, blank=True)
    quantity = models.DecimalField(_('quantity'), max_digits=8, decimal_places=2)
    unit_of_quantity = models.ForeignKey("Unit", blank=True, null=True,
                                         verbose_name=_('unit'), related_name="event_qty_units")
    quality = models.DecimalField(_('quality'), max_digits=3, decimal_places=0, default=Decimal("0"))
    value = models.DecimalField(_('value'), max_digits=8, decimal_places=2,
                                default=Decimal("0.0"))
    unit_of_value = models.ForeignKey("Unit", blank=True, null=True,
                                      verbose_name=_('unit of value'), related_name="event_value_units")
    price = models.DecimalField(_('price'), max_digits=8, decimal_places=2,
                                default=Decimal("0.0"))
    unit_of_price = models.ForeignKey("Unit", blank=True, null=True,
                                      verbose_name=_('unit of price'), related_name="event_price_units")
    commitment = models.ForeignKey("Commitment", blank=True, null=True,
                                   verbose_name=_('fulfills commitment'), related_name="fulfillment_events",
                                   on_delete=models.SET_NULL)
    is_contribution = models.BooleanField(_('is contribution'), default=False)
    is_to_distribute = models.BooleanField(_('is to distribute'), default=False)
    accounting_reference = models.ForeignKey("AccountingReference", blank=True, null=True,
                                             verbose_name=_('accounting reference'), related_name="events",
                                             help_text=_('optional reference to an accounting grouping'))
    event_reference = models.CharField(_('reference'), max_length=128, blank=True, null=True)
    digital_currency_tx_hash = models.CharField(_("digital currency transaction hash"), max_length=96,
                                                blank=True, null=True, editable=False)
    digital_currency_tx_state = models.CharField(_('digital currency transaction state'),
                                                 max_length=12, choices=TX_STATE_CHOICES,
                                                 blank=True, null=True)
    created_by = models.ForeignKey(User, verbose_name=_('created by'),
                                   related_name='events_created', blank=True, null=True, editable=False)
    changed_by = models.ForeignKey(User, verbose_name=_('changed by'),
                                   related_name='events_changed', blank=True, null=True, editable=False)

    slug = models.SlugField(_("Page name"), editable=False)

    objects = EconomicEventManager()

    class Meta:
        ordering = ('-event_date', '-pk')

    def __str__(self):
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
            resource_string = self.resource.__str__()
        event_name = self.event_type.name
        # if self.exchange_type_item_type:
        #    event_name = self.exchange_type_item_type.name
        return ' '.join([
            event_name,
            self.event_date.strftime('%Y-%m-%d'),
            'from',
            from_agt,
            'to',
            to_agt,
            quantity_string,
            resource_string,
        ])

    def undistributed_description(self):
        if self.unit_of_quantity:
            quantity_string = " ".join([str(self.undistributed_amount()), self.unit_of_quantity.abbrev])
        else:
            quantity_string = str(self.undistributed_amount())
        from_agt = 'Unassigned'
        if self.from_agent:
            from_agt = self.from_agent.name
        to_agt = 'Unassigned'
        if self.recipient():
            to_agt = self.recipient().name
        resource_string = self.resource_type.name
        if self.resource:
            resource_string = self.resource.__str__()
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
        from .types import AgentResourceType
        # import pdb; pdb.set_trace()

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
                # todo ART: bugs in this code cause dup records
                if self.event_type.relationship == "work" or self.event_type.related_to == "agent":
                    try:
                        art, created = AgentResourceType.objects.get_or_create(
                            agent=agent,
                            resource_type=resource_type,
                            event_type=event_type)
                    except:
                        # todo: this shd not happen, but it does...
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

            # for handling faircoin
            # if self.resource:
            #    if self.resource.resource_type.is_virtual_account():
            # call the faircoin method here, pass the event info needed

    def delete(self, *args, **kwargs):
        from .behavior import CachedEventSummary
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

    def previous_events(self):
        """ Experimental method:
        Trying to use properties of events to determine event sequence.
        Can't count on dates or event ids.
        This is currently for the DHen resource_flow_report
        and takes advantage of DHen data shape.
        For example, Consumption events will have no successors.
        Receives will have no prevs except a Give event
        in the same Transfer.
        Will most likely not work (yet) more generally.
        """
        from .types import EventType
        # import pdb; pdb.set_trace()
        prevs = []
        # todo exchange redesign fallout
        give = EventType.objects.get(name="Give")
        ret = EventType.objects.get(name="Receive")
        cet = EventType.objects.get(name="Resource Consumption")
        if self.event_type == ret:
            if self.transfer:
                give_evt = self.transfer.give_event()
                if give_evt:
                    prevs.append(give_evt)
                return prevs
        resource = self.resource
        if resource:
            candidates = resource.events.all()
            prevs = candidates.filter(to_agent=self.from_agent).exclude(event_type=give)
            prevs = prevs.exclude(event_type=cet)
            if self.event_type == give:
                if self.transfer:
                    prevs = prevs.exclude(transfer=self.transfer)
        return prevs

    def next_events(self):
        nexts = []
        resource = self.resource
        if resource:
            candidates = resource.events.all()
            nexts = candidates.filter(from_agent=self.to_agent).exclude(id=self.id)
        return nexts

    def transaction_state(self):
        # import pdb; pdb.set_trace()
        if not settings.use_faircoins:
            return None
        state = self.digital_currency_tx_state
        new_state = None
        if state == "pending" or state == "broadcast":
            tx = self.digital_currency_tx_hash
            if tx:
                from django_rea.valueaccounting.faircoin_utils import get_confirmations
                confirmations, timestamp = get_confirmations(tx)
                if confirmations > 0:
                    if state != "broadcast":
                        new_state = "broadcast"
                if confirmations > 6:
                    new_state = "confirmed"
        if new_state:
            state = new_state
            self.digital_currency_tx_state = new_state
            self.save()
        return state

    def to_faircoin_address(self):
        if self.resource.is_digital_currency_resource():
            event_reference = self.event_reference
            if event_reference:
                answer = event_reference
                to_resources = EconomicResource.objects.filter(digital_currency_address=event_reference)
                if to_resources:
                    answer = to_resources[0].identifier
        return answer

    def seniority(self):
        return (datetime.date.today() - self.event_date).days

    def value_per_unit(self):
        from .types import AgentResourceType
        # import pdb; pdb.set_trace()
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

    # obsolete
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
            # todo: needs price changes
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

    def incoming_value_flows_dfs(self, flows, visited, depth):
        # EconomicEvent method
        # todo dhen_bug:
        if self.event_type.relationship == "receive":
            if self.transfer:
                exchange = self.transfer.exchange
                if exchange:
                    if exchange not in visited:
                        visited.add(exchange)
                        exchange.depth = depth + 1
                        flows.append(exchange)
                        for pmt in exchange.reciprocal_transfer_events():
                            pmt.depth = depth + 2
                            flows.append(pmt)
        if self.resource:
            depth = depth + 1
            # the exclude clause tries to head off infinite loops
            prevs = self.resource.events.filter(to_agent=self.from_agent).exclude(from_agent=self.from_agent)
            for prev in prevs:
                if prev not in visited:
                    visited.add(prev)
                    prev.depth = depth
                    flows.append(prev)
                    prev.incoming_value_flows_dfs(flows, visited, depth)

    def roll_up_value(self, path, depth, visited, value_equation):
        # EconomicEvent method
        # rollup stage change
        stage = None
        # what is no commitment? Can that happen with staged events?
        if self.commitment:
            stage = self.commitment.stage
        if stage:
            self.resource.historical_stage = stage
        # todo 3d:
        return self.resource.roll_up_value(path, depth, visited, value_equation)

    def compute_income_shares(self, value_equation, d_qty, events, visited):
        # EconomicEvent method
        # income_shares stage change
        stage = None
        # what is no commitment? Can that happen with staged events?
        if self.commitment:
            stage = self.commitment.stage
        if stage:
            self.resource.historical_stage = stage
        # todo 3d:
        return self.resource.compute_income_shares(value_equation, d_qty, events, visited)

    def bucket_rule(self, value_equation):
        from .behavior import ValueEquationBucketRule
        brs = ValueEquationBucketRule.objects.filter(
            value_equation_bucket__value_equation=value_equation,
            event_type=self.event_type)
        # import pdb; pdb.set_trace()
        candidates = []
        for br in brs:
            if br.claim_creation_equation:
                filter = br.filter_rule_deserialized()
                if filter:
                    rts = filter.get('resource_types')
                    if rts:
                        if self.resource_type in rts:
                            br.filter = filter
                            candidates.append(br)
                    pts = filter.get('process_types')
                    if pts:
                        if self.process:
                            if self.process.process_type:
                                if self.process.process_type in pts:
                                    br.filter = filter
                                    candidates.append(br)
                else:
                    br.filter = filter
                    candidates.append(br)
        if not candidates:
            return None
        candidates = list(set(candidates))
        # import pdb; pdb.set_trace()
        if len(candidates) == 1:
            return candidates[0]
        filtered = [c for c in candidates if c.filter]
        if not filtered:
            return candidates[0]
        best_fit = []
        if filtered:
            if len(filtered) == 1:
                return filtered[0]
            for f in filtered:
                pts = f.filter.get("process_types")
                rts = filter.get('resource_types')
                if pts and rts:
                    f.score = 2
                    best_fit.append(f)
                elif pts:
                    f.score = 1.5
                    better = [b for b in best_fit if b.score > 1.5]
                    if not better:
                        best_fit.append(f)
                elif rts:
                    if not best_fit:
                        f.score = 1
                        best_fit.append(f)
        if best_fit:
            # todo: necessary? I doubt it...
            # best_fit = list(set(best_fit))
            # todo: this (below) must be mediated by which VE
            # if len(best_fit) > 1:
            #    import pdb; pdb.set_trace()
            if len(best_fit) == 1:
                return best_fit[0]
            return best_fit[0]
        return None

    def bucket_rule_for_context_agent(self):
        bucket_rule = None
        if self.context_agent:
            ves = self.context_agent.live_value_equations()
            for ve in ves:
                bucket_rule = self.bucket_rule(ve)
                if bucket_rule:
                    break
        return bucket_rule

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
        return [claim for claim in claims if claim.value_equation_bucket_rule == bucket_rule]

    def create_claim(self, bucket_rule):
        from .processes import Claim, ClaimEvent
        # import pdb; pdb.set_trace()
        # claims = self.outstanding_claims_for_bucket_rule(bucket_rule)
        # if claims:
        if self.created_claim():
            return self.created_claim()
        else:
            order = None
            if self.commitment:
                order = self.commitment.independent_demand
            else:
                if self.process:
                    order = self.process.independent_demand()
            claim_value = bucket_rule.compute_claim_value(self)
            claim = Claim(
                order=order,
                value_equation_bucket_rule=bucket_rule,
                claim_date=datetime.date.today(),
                has_agent=self.from_agent,
                against_agent=self.to_agent,
                context_agent=self.context_agent,
                unit_of_value=self.unit_of_value,
                value=claim_value,
                original_value=claim_value,
                claim_creation_equation=bucket_rule.claim_creation_equation,
            )
            claim.save()
            claim_event = ClaimEvent(
                event=self,
                claim=claim,
                claim_event_date=datetime.date.today(),
                value=claim_value,
                unit_of_value=self.unit_of_value,
                event_effect="+",
            )
            claim_event.save()
            # claim_event.update_claim()
            return claim

    def get_unsaved_contribution_claim(self, bucket_rule):
        from .processes import Claim, ClaimEvent
        # import pdb; pdb.set_trace()
        claim = self.created_claim()
        if claim:
            claim.new = False
            return claim
        else:
            value = bucket_rule.compute_claim_value(self)
            against_agent = self.to_agent
            if self.event_type.name == "Payment":
                against_agent = self.context_agent
            claim = Claim(
                value_equation_bucket_rule=bucket_rule,
                claim_date=datetime.date.today(),
                has_agent=self.from_agent,
                against_agent=against_agent,
                context_agent=self.context_agent,
                value=value,
                unit_of_value=self.unit_of_value,
                original_value=value,
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
            claim.new = True
            return claim

    def get_unsaved_context_agent_claim(self, against_agent, bucket_rule):
        from .processes import Claim, ClaimEvent
        # import pdb; pdb.set_trace()
        # changed for contextAgentDistributions
        # todo: how to find created_context_agent_claims?
        # claim = self.created_claim()
        # if claim:
        #    claim.new = False
        #    return claim

        value = bucket_rule.compute_claim_value(self)
        claim = Claim(
            # order=order,
            value_equation_bucket_rule=bucket_rule,
            claim_date=datetime.date.today(),
            has_agent=self.context_agent,
            against_agent=against_agent,
            context_agent=self.context_agent,
            value=value,
            unit_of_value=self.unit_of_value,
            original_value=value,
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
        claim.new = True
        return claim

    def undistributed_amount(self):
        # import pdb; pdb.set_trace()
        # todo: partial
        # et_cr = EventType.objects.get(name="Cash Receipt")
        # et_id = EventType.objects.get(name="Distribution")
        if self.is_to_distribute:
            crd_amounts = sum(d.quantity for d in self.distributions.all())
            return self.quantity - crd_amounts
        else:
            return Decimal("0.0")

    def is_undistributed(self):
        # import pdb; pdb.set_trace()
        # todo: partial
        # et_cr = EventType.objects.get(name="Cash Receipt")
        # et_id = EventType.objects.get(name="Distribution")
        # if self.event_type == et_cr or self.event_type == et_id:
        #    crds = self.distributions.all()
        #    if crds:
        #        return False
        #    else:
        #        return True
        # else:
        #    return False
        if self.undistributed_amount():
            return True
        else:
            return False

    def shorter_label(self):
        if self.unit_of_quantity:
            quantity_string = " ".join([str(self.quantity), self.unit_of_quantity.abbrev])
        else:
            quantity_string = str(self.quantity)
        agt_string = ""
        if self.from_agent != self.to_agent:
            from_agt = 'Unassigned'
            if self.from_agent:
                from_agt = self.from_agent.nick
            to_agt = 'Unassigned'
            if self.recipient():
                to_agt = self.recipient().nick
            agt_string = ' to '.join([from_agt, to_agt])
        rname = self.resource_type.name
        if self.resource:
            rname = self.resource.resource_type.name
        return ' '.join([
            agt_string,
            rname,
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
        if self.transfer:
            return self.transfer.transfer_type.name
        else:
            return self.event_type.name
        """
        answer = self.event_type.name
        if answer=="Receive":
            if self.transfer:
                if self.transfer.is_reciprocal():
                    answer = self.transfer.transfer_type.name
        return answer
        """

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
            # rollup stage change
            # import pdb; pdb.set_trace()
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

    # compensation methods obsolete
    # def my_compensations(self):
    #    return self.initiated_compensations.all()

    # def compensation(self):
    #    return sum(c.compensating_value for c in self.my_compensations())

    # def value_due(self):
    #    return self.value - self.compensation()

    # def is_compensated(self):
    #    if self.value_due() > 0:
    #        return False
    #    return True

    def claimed_amount(self):  # for contribution events
        if self.is_contribution:
            if self.created_claim():
                return self.created_claim().original_value
            else:
                return None
        else:
            return None

    def owed_amount(self):  # for contribution events
        if self.is_contribution:
            if self.claimed_amount():
                return self.created_claim().value
            else:
                return None
        else:
            return None

    def distributed_amount(self):  # for contribution events
        if self.is_contribution:
            if self.created_claim():
                return self.created_claim().original_value - self.created_claim().value
        else:
            return Decimal("0.0")

    def unit(self):
        if self.unit_of_quantity:
            return self.unit_of_quantity.abbrev
        else:
            return self.resource_type.unit.abbrev

    def own_or_resource_type_unit(self):
        if self.unit_of_quantity:
            return self.unit_of_quantity
        else:
            return self.resource_type.unit

    def quantity_formatted(self):
        return " ".join([
            str(self.quantity.quantize(Decimal('.01'), rounding=ROUND_HALF_UP)),
            self.unit(),
        ])

    def distribution_quantity_formatted(self):
        unit = self.own_or_resource_type_unit()
        qty_string = str(self.quantity.quantize(Decimal('.01'), rounding=ROUND_HALF_UP))
        if unit.symbol:
            return "".join([
                unit.symbol,
                qty_string,
            ])
        else:
            return " ".join([
                qty_string,
                unit,
            ])

    def value_formatted_decimal(self):
        # import pdb; pdb.set_trace()
        val = self.value.quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
        if self.unit_of_value:
            if self.unit_of_value.symbol:
                value_string = "".join([self.unit_of_value.symbol, str(val)])
            else:
                value_string = " ".join([str(val), self.unit_of_value.abbrev])
        else:
            value_string = str(val)
        return value_string

    def price_formatted_decimal(self):
        # import pdb; pdb.set_trace()
        val = self.price.quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
        if self.unit_of_price:
            if self.unit_of_price.symbol:
                price_string = "".join([self.unit_of_price.symbol, str(val)])
            else:
                price_string = " ".join([str(val), self.unit_of_price.abbrev])
        else:
            price_string = str(val)
        return price_string

    def form_prefix(self):
        return "-".join(["EVT", str(self.id)])

    def work_event_change_form(self):
        from django_rea.valueaccounting.forms import WorkEventChangeForm
        prefix = self.form_prefix()
        return WorkEventChangeForm(instance=self, prefix=prefix, )

    def change_form_old(self, data=None):
        # import pdb; pdb.set_trace()
        from django_rea.valueaccounting.forms import TimeEventForm, InputEventForm
        unit = self.unit_of_quantity
        if not unit:
            unit = self.resource_type.unit
        prefix = self.form_prefix()
        if unit.unit_type == "time":
            return TimeEventForm(instance=self, prefix=prefix, data=data)
        else:
            qty_help = " ".join(["unit:", unit.abbrev, ", up to 2 decimal places"])
            return InputEventForm(qty_help=qty_help, instance=self, prefix=prefix, data=data)

    def change_form(self, data=None):
        # import pdb; pdb.set_trace()
        from django_rea.valueaccounting.forms import InputEventForm
        unit = self.unit_of_quantity
        if not unit:
            unit = self.resource_type.unit
        prefix = self.form_prefix()
        qty_help = " ".join(["unit:", unit.abbrev, ", up to 2 decimal places"])
        return InputEventForm(qty_help=qty_help, instance=self, prefix=prefix, data=data)

    def distribution_change_form(self, data=None):
        # import pdb; pdb.set_trace()
        from django_rea.valueaccounting.forms import DistributionEventForm
        prefix = self.form_prefix()
        return DistributionEventForm(instance=self, prefix=prefix, data=data)

    def disbursement_change_form(self, data=None):
        # import pdb; pdb.set_trace()
        from django_rea.valueaccounting.forms import DisbursementEventForm
        prefix = self.form_prefix()
        return DisbursementEventForm(instance=self, prefix=prefix, data=data)

    # def exchange_change_form(self, data=None):
    #    #import pdb; pdb.set_trace()
    #    from django_rea.valueaccounting.forms import ExchangeEventForm
    #    unit = self.unit_of_quantity
    #    if not unit:
    #        unit = self.resource_type.unit
    #    prefix = self.form_prefix()
    #    qty_help = " ".join(["unit:", unit.abbrev, ", up to 2 decimal places"])
    #    return ExchangeEventForm(qty_help=qty_help, instance=self, prefix=prefix, data=data)

    def unplanned_work_event_change_form(self):
        from django_rea.valueaccounting.forms import UnplannedWorkEventForm
        return UnplannedWorkEventForm(instance=self, prefix=str(self.id))

    def change_date_form(self):
        from django_rea.valueaccounting.forms import EventChangeDateForm
        return EventChangeDateForm(instance=self, prefix=str(self.id))

    def change_quantity_form(self):
        from django_rea.valueaccounting.forms import EventChangeQuantityForm
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
        # import pdb; pdb.set_trace()
        # todo: this was created for a DHen report
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

    def compute_income_fractions_for_process(self, value_equation):
        # EconomicEvent (shipment) method
        # import pdb; pdb.set_trace()
        shares = []
        # todo exchange redesign fallout
        # shipment events are no longer event_type.name == "Shipment"
        # they are et.name == "Give"
        if self.event_type.name == "Give":
            commitment = self.commitment
            # problem: if the shipment event with no (an uninventoried) resource has no commitment,
            # we can't find the process it came from.
            if commitment:
                production_commitments = commitment.get_production_commitments_for_shipment()
                if production_commitments:
                    visited = set()
                    path = []
                    depth = 0
                    # todo: later, work out how to handle multiple production commitments
                    pc = production_commitments[0]
                    p = pc.process
                    if p:
                        visited = set()
                        p.compute_income_shares(value_equation, self, self.quantity, shares, visited)

        return shares

    def get_shipment_commitment_for_production_event(self):
        if self.event_type.relationship == "out":
            if self.commitment:
                return self.commitment.order_item
        return None

    def get_shipment_commitment_for_distribution_event(self):
        if self.event_type.name == "Distribution":
            claims = self.claims()
            if claims:
                claim = claims[0]
                event = claim.creating_event()
                return event.get_shipment_commitment_for_production_event()
        return None

    def get_shipment_for_distribution(self):
        the_shipment = None
        if self.event_type.name == "Distribution":
            ship_ct = self.get_shipment_commitment_for_distribution_event()
            if ship_ct:
                ex = self.exchange
                dve = ex.distribution_value_equation()
                ship_evts = dve.shipments()
                for se in ship_evts:
                    if se.commitment:
                        if ship_ct == se.commitment:
                            the_shipment = se
        return the_shipment

    def get_order_for_distribution(self):
        the_order = None
        if self.event_type.name == "Distribution":
            ex = self.exchange
            dve = ex.distribution_value_equation()
            orders = dve.orders()
            if orders:
                the_order = orders[0]
        return the_order

    def independent_demand(self):
        if self.commitment:
            return self.commitment.independent_demand
        else:
            return self.process.independent_demand()

    def order_item(self):
        if self.commitment:
            return self.commitment.order_item
        else:
            return self.process.order_item()


@python_2_unicode_compatible
class EconomicAgent(models.Model):
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

    def membership_request(self):
        reqs = self.membership_requests.all()
        if reqs:
            return reqs[0]
        else:
            return None

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

    def joinaproject_requests(self):
        reqs = self.project_join_requests.all()
        if reqs:
            return reqs
        else:
            return None

    def joinaproject_requests_projects(self):
        reqs = self.project_join_requests.all()
        projects = []
        if reqs:
            for req in reqs:
                projects.append(req.project)
            return projects
        else:
            return None

    def request_faircoin_address(self):
        # import pdb; pdb.set_trace()
        address = self.faircoin_address()
        if not address:
            address = "address_requested"
            resource = self.create_faircoin_resource(address)
        return address

    def create_fake_faircoin_address(self):
        # import pdb; pdb.set_trace()
        address = self.faircoin_address()
        if not address:
            address = str(time.time())
            resource = self.create_faircoin_resource(address)
            print("created fake faircoin address")
        return address

    def create_faircoin_resource(self, address):
        from .types import AgentResourceRoleType, EconomicResourceType
        if not settings.use_faircoins:
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

    def faircoin_address(self):
        if not settings.use_faircoins:
            return None
        fcr = self.faircoin_resource()
        if fcr:
            return fcr.digital_currency_address
        else:
            return None

    def faircoin_resource(self):
        if not settings.use_faircoins:
            return None
        candidates = self.agent_resource_roles.filter(
            role__is_owner=True,
            resource__resource_type__behavior="dig_acct",
            resource__digital_currency_address__isnull=False)
        if candidates:
            return candidates[0].resource
        else:
            return None

    def candidate_membership(self):
        aa = self.candidate_association()
        if aa:
            if aa.state == "potential":
                return aa.has_associate
        return None

    def candidate_association(self):
        aas = self.is_associate_of.all()
        if aas:
            aa = aas[0]
            if aa.state == "potential":
                return aa

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

    def is_active_freedom_coop_member(self):
        if not settings.use_faircoins:
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
        from .types import EventType
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
        from .behavior import Distribution
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
        from .types import ProcessType
        pts = list(ProcessType.objects.filter(context_agent=self))
        parent = self.parent()
        while parent:
            pts.extend(ProcessType.objects.filter(context_agent=parent))
            parent = parent.parent()
        pt_ids = [pt.id for pt in pts]
        return ProcessType.objects.filter(id__in=pt_ids)

    def get_resource_types_with_recipe(self):
        from .types import ProcessType
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
        from .types import AgentAssociationType
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
        from .types import AgentResourceRoleType
        # import pdb; pdb.set_trace()
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
        from .processes import Order
        # import pdb; pdb.set_trace()
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
        from .types import EventType
        from .behavior import UseCase
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
        from .types import EventType
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


class ResourceState(models.Model):
    name = models.CharField(_('name'), max_length=128, unique=True)
    description = models.TextField(_('description'), blank=True, null=True)


@python_2_unicode_compatible
class ResourceClass(models.Model):
    name = models.CharField(_('name'), max_length=128, unique=True)
    description = models.TextField(_('description'), blank=True, null=True)

    def __str__(self):
        return self.name
