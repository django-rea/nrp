from __future__ import print_function

import datetime
from decimal import *

from toposort import toposort_flatten

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from easy_thumbnails.fields import ThumbnailerImageField

from django_rea.valueaccounting.models.agent import EconomicAgent
from django_rea.valueaccounting.models.event import EconomicEvent

FAIRCOIN_DIVISOR = Decimal("1000000.00")


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
        if not settings.USE_FAIRCOINS:
            return False
        if self.digital_currency_address:
            return True
        else:
            return False

    def address_is_activated(self):
        if not settings.USE_FAIRCOINS:
            return False
        address = self.digital_currency_address
        if address:
            if address != "address_requested":
                return True
        return False

    def digital_currency_history(self):
        history = []
        if not settings.USE_FAIRCOINS:
            return history
        address = self.digital_currency_address
        if address:
            from django_rea.valueaccounting.faircoin_utils import get_address_history
            history = get_address_history(address)
        return history

    def digital_currency_balance(self):
        bal = 0
        if not settings.USE_FAIRCOINS:
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
        if not settings.USE_FAIRCOINS:
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
        from django_rea.valueaccounting.models.recipe import EventType
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
        from django_rea.valueaccounting.models.facetconfig import UseCase
        from django_rea.valueaccounting.models.recipe import EventType
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
        from django_rea.valueaccounting.models.recipe import EventType
        rct_et = EventType.objects.get(name="Receive")
        with_xfer = [event for event in self.events.all() if event.transfer and event.event_type == rct_et]
        currencies = [event for event in with_xfer if event.transfer.transfer_type.is_currency]
        return currencies

    def cash_contribution_events(self):  # includes only cash contributions
        # todo exchange redesign fallout
        from django_rea.valueaccounting.models.recipe import EventType
        # import pdb; pdb.set_trace()
        rct_et = EventType.objects.get(name="Receive")
        with_xfer = [event for event in self.events.all() if event.transfer and event.event_type == rct_et]
        contributions = [event for event in with_xfer if event.is_contribution]
        currencies = [event for event in contributions if event.transfer.transfer_type.is_currency]
        return currencies

    def purchase_events(self):
        # todo exchange redesign fallout
        from django_rea.valueaccounting.models.recipe import EventType
        # is this correct?
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
        from django_rea.valueaccounting.models.recipe import EventType
        print("obsolete resource.transfer_event")
        # import pdb; pdb.set_trace()
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
        from django_rea.valueaccounting.models.recipe import EventType
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
        flows = self.incoming_value_flows()
        from django_rea.valueaccounting.models.process import Process
        from django_rea.valueaccounting.models.trade import Exchange
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
        from django_rea.valueaccounting.models.recipe import EventType
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
        from django_rea.valueaccounting.models.process import Process
        in_out = self.value_flow_going_forward()
        processes = []
        for index, io in enumerate(in_out):
            if type(io) is Process:
                if io.input_includes_resource(self):
                    processes.append(io)
        return processes

    def receipt(self):
        from django_rea.valueaccounting.models.recipe import EventType
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


class ResourceState(models.Model):
    name = models.CharField(_('name'), max_length=128, unique=True)
    description = models.TextField(_('description'), blank=True, null=True)


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
class AgentResourceType(models.Model):
    agent = models.ForeignKey("EconomicAgent",
                              verbose_name=_('agent'), related_name='resource_types')
    resource_type = models.ForeignKey("EconomicResourceType",
                                      verbose_name=_('resource type'), related_name='agents')
    score = models.DecimalField(_('score'), max_digits=8, decimal_places=2,
                                default=Decimal("0.0"),
                                help_text=_("the quantity of contributions of this resource type from this agent"))
    event_type = models.ForeignKey("EventType",
                                   verbose_name=_('event type'), related_name='agent_resource_types')
    lead_time = models.IntegerField(_('lead time'),
                                    default=0, help_text=_("in days"))
    value = models.DecimalField(_('value'), max_digits=8, decimal_places=2,
                                default=Decimal("0.0"))
    unit_of_value = models.ForeignKey("Unit", blank=True, null=True,
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

    def __str__(self):
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
        # return self.event_type.infer_label()
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
        from django_rea.valueaccounting.forms import AgentResourceTypeForm
        return AgentResourceTypeForm(instance=self, prefix=self.xbill_change_prefix())

    def total_required(self):
        from .schedule import Commitment
        commitments = Commitment.objects.unfinished().filter(resource_type=self.resource_type)
        return sum(req.quantity_to_buy() for req in commitments)

    def comparative_scores(self):
        scores = AgentResourceType.objects.filter(resource_type=self.resource_type).values_list('score', flat=True)
        average = str((sum(scores) / len(scores)).quantize(Decimal('.01'), rounding=ROUND_HALF_UP))
        return "".join([
            "Min: ", str(min(scores).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)),
            ", Average: ", average,
            ", Max: ", str(max(scores).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)),
        ])


class AgentResourceRoleTypeManager(models.Manager):
    def owner_role(self):
        role_types = AgentResourceRoleType.objects.filter(is_owner=True)
        owner_role_type = None
        if role_types:
            return role_types[0]
        else:
            raise ValidationError("No owner AgentResourceRoleType")


@python_2_unicode_compatible
class AgentResourceRoleType(models.Model):
    name = models.CharField(_('name'), max_length=128)
    description = models.TextField(_('description'), blank=True, null=True)
    is_owner = models.BooleanField(_('is owner'), default=False)

    objects = AgentResourceRoleTypeManager()

    def __str__(self):
        return self.name
