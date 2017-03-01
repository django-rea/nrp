from __future__ import print_function

import datetime
from decimal import *

import simplejson
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from django_rea.valueaccounting.models.agent import EconomicAgent
from django_rea.valueaccounting.models.event import EconomicEvent
from django_rea.valueaccounting.models.recipe import EventType
from django_rea.valueaccounting.models.trade import Exchange
from django_rea.valueaccounting.models.schedule import Order
from django_rea.valueaccounting.models.facetconfig import (ProcessPattern, UseCase)


class DistributionManager(models.Manager):
    def distributions(self, start=None, end=None):
        if start and end:
            dists = Distribution.objects.filter(distribution_date__range=[start, end])
        else:
            dists = Distribution.objects.all()
        return dists


@python_2_unicode_compatible
class Distribution(models.Model):
    name = models.CharField(_('name'), blank=True, max_length=128)
    process_pattern = models.ForeignKey("ProcessPattern",
                                        blank=True, null=True,
                                        verbose_name=_('pattern'), related_name='distributions')
    context_agent = models.ForeignKey("EconomicAgent",
                                      blank=True, null=True,
                                      limit_choices_to={"is_context": True, },
                                      verbose_name=_('context agent'), related_name='distributions')
    url = models.CharField(_('url'), max_length=255, blank=True, null=True)
    distribution_date = models.DateField(_('distribution date'))
    notes = models.TextField(_('notes'), blank=True)
    value_equation = models.ForeignKey("ValueEquation",
                                       blank=True, null=True,
                                       verbose_name=_('value equation link'), related_name='distributions')
    value_equation_content = models.TextField(_('value equation formulas used'), null=True, blank=True)
    created_by = models.ForeignKey(User, verbose_name=_('created by'),
                                   related_name='distributions_created', blank=True, null=True, editable=False)
    changed_by = models.ForeignKey(User, verbose_name=_('changed by'),
                                   related_name='distributions_changed', blank=True, null=True, editable=False)
    created_date = models.DateField(auto_now_add=True, blank=True, null=True, editable=False)
    changed_date = models.DateField(auto_now=True, blank=True, null=True, editable=False)
    slug = models.SlugField(_("Page name"), editable=False)

    objects = DistributionManager()

    class Meta:
        ordering = ('-distribution_date',)
        verbose_name_plural = _("distributions")

    def __str__(self):
        show_name = "Distribution"
        name = ""
        if self.name:
            name = self.name + ","
        return " ".join([
            name,
            show_name,
            "starting",
            self.distribution_date.strftime('%Y-%m-%d'),
        ])

    def deserialize_value_equation_content(self):
        return simplejson.loads(self.value_equation_content)

    def buckets(self):
        dict = self.deserialize_value_equation_content()
        bucket_dict = dict["buckets"]
        buckets = []
        for key, value in bucket_dict.iteritems():
            bucket = ValueEquationBucket.objects.get(id=key)
            bucket.value = value
            buckets.append(bucket)
        return buckets

    def bucket_rules(self):
        buckets = self.buckets()
        answer = []
        for bucket in buckets:
            rules = bucket.value.get("bucket_rules")
            if rules:
                for key, value in rules.iteritems():
                    rule = ValueEquationBucketRule.objects.get(id=key)
                    rule.value = value
                    answer.append(rule)
        return answer

    def orders(self):
        buckets = self.buckets()
        orders = []
        for b in buckets:
            filter = b.value.get("filter")
            if filter:
                method = filter.get("method")
                if method:
                    if method == "Order":
                        oids = filter["orders"]
                        for oid in oids:
                            orders.append(Order.objects.get(id=oid))
        return orders

    def shipments(self):
        buckets = self.buckets()
        shipments = []
        for b in buckets:
            filter = b.value.get("filter")
            if filter:
                method = filter.get("method")
                if method:
                    if method == "Shipment":
                        ship_ids = filter["shipments"]
                        for sid in ship_ids:
                            shipments.append(EconomicEvent.objects.get(id=sid))
        return shipments

    def distribution_events(self):
        return self.events.filter(
            event_type__relationship='distribute')

    def disbursement_events(self):
        return self.events.filter(
            event_type__relationship='disburse')

    def distribution_total(self):
        dists = self.distribution_events()
        total = 0
        for dist in dists:
            total += dist.quantity
        return total

    def disbursement_total(self):
        disbs = self.disbursement_events()
        total = 0
        for disb in disbs:
            total += disb.quantity
        return total

    def flow_type(self):
        return "Distribution"

    def flow_class(self):
        return "distribution"

    def flow_description(self):
        return self.__str__()


# obsolete
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
                                 verbose_name=_('exchange'), related_name='value_equation')
    value_equation_link = models.ForeignKey("ValueEquation",
                                            blank=True, null=True,
                                            verbose_name=_('value equation link'), related_name='distributions_ve')
    value_equation_content = models.TextField(_('value equation formulas used'), null=True, blank=True)

    def deserialize_value_equation_content(self):
        return simplejson.loads(self.value_equation_content)

    def buckets(self):
        dict = self.deserialize_value_equation_content()
        bucket_dict = dict["buckets"]
        buckets = []
        for key, value in bucket_dict.iteritems():
            bucket = ValueEquationBucket.objects.get(id=key)
            bucket.value = value
            buckets.append(bucket)
        return buckets

    def bucket_rules(self):
        buckets = self.buckets()
        answer = []
        for bucket in buckets:
            rules = bucket.value.get("bucket_rules")
            if rules:
                for key, value in rules.iteritems():
                    rule = ValueEquationBucketRule.objects.get(id=key)
                    rule.value = value
                    answer.append(rule)
        return answer

    def orders(self):
        buckets = self.buckets()
        orders = []
        for b in buckets:
            filter = b.value.get("filter")
            if filter:
                method = filter.get("method")
                if method:
                    if method == "Order":
                        oids = filter["orders"]
                        for oid in oids:
                            orders.append(Order.objects.get(id=oid))
        return orders

    def shipments(self):
        buckets = self.buckets()
        shipments = []
        for b in buckets:
            filter = b.value.get("filter")
            if filter:
                method = filter.get("method")
                if method:
                    if method == "Shipment":
                        ship_ids = filter["shipments"]
                        for sid in ship_ids:
                            shipments.append(EconomicEvent.objects.get(id=sid))
        return shipments


PERCENTAGE_BEHAVIOR_CHOICES = (
    ('remaining', _('Remaining percentage')),
    ('straight', _('Straight percentage')),
)


@python_2_unicode_compatible
class ValueEquation(models.Model):
    name = models.CharField(_('name'), max_length=255, blank=True)
    context_agent = models.ForeignKey(EconomicAgent,
                                      limit_choices_to={"is_context": True, },
                                      related_name="value_equations", verbose_name=_('context agent'))
    description = models.TextField(_('description'), null=True, blank=True)
    percentage_behavior = models.CharField(_('percentage behavior'),
                                           max_length=12, choices=PERCENTAGE_BEHAVIOR_CHOICES, default='straight',
                                           help_text=_(
                                               'Remaining percentage uses the %% of the remaining amount to be distributed.  Straight percentage uses the %% of the total distribution amount.'))
    live = models.BooleanField(_('live'), default=False,
                               help_text=_("Make this value equation available for use in real distributions."))
    created_by = models.ForeignKey(User, verbose_name=_('created by'),
                                   related_name='value_equations_created', blank=True, null=True)
    created_date = models.DateField(auto_now_add=True, blank=True, null=True, editable=False)

    def __str__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('edit_value_equation', (),
                {'value_equation_id': str(self.id), })

    def is_deletable(self):
        if self.distributions.all() or self.live:
            return False
        else:
            return True

    def run_value_equation_and_save(self, distribution, money_resource, amount_to_distribute, serialized_filters,
                                    events_to_distribute=None):
        # import pdb; pdb.set_trace()
        distribution_events, contribution_events = self.run_value_equation(
            amount_to_distribute=amount_to_distribute,
            serialized_filters=serialized_filters)
        context_agent = self.context_agent
        testing = False
        if context_agent.name == "test context agent":
            testing = True
        for dist_event in distribution_events:
            va = None
            # todo faircoin distribution
            # import pdb; pdb.set_trace()
            to_agent = dist_event.to_agent
            if money_resource.is_digital_currency_resource():
                if testing:
                    # todo faircoin distribution: shd put this into models
                    # no need to import from faircoin_utils
                    from django_rea.valueaccounting.faircoin_utils import send_fake_faircoins
                    # faircoins are the only digital currency we handle now
                va = to_agent.faircoin_resource()
                if va:
                    if va.resource_type != money_resource.resource_type:
                        raise ValidationError(" ".join([
                            money_resource.identifier,
                            va.identifier,
                            "digital currencies do not match."]))

                else:
                    if testing:
                        address = to_agent.create_fake_faircoin_address()
                    else:
                        address = to_agent.request_faircoin_address()
                    va = to_agent.faircoin_resource()
                if va:
                    dist_event.resource = va
                    dist_event.resource_type = va.resource_type
                    dist_event.unit_of_quantity = va.resource_type.unit
                else:
                    raise ValidationError(dist_event.to_agent.nick + ' needs faircoin address, unable to create one.')
            else:
                vas = dist_event.to_agent.virtual_accounts()
                if vas:
                    for vacct in vas:
                        if vacct.resource_type.unit == money_resource.resource_type.unit:
                            va = vacct
                            break
                if not va:
                    va = dist_event.to_agent.create_virtual_account(resource_type=money_resource.resource_type)
                if va:
                    dist_event.resource = va
                    dist_event.resource_type = va.resource_type
                    dist_event.unit_of_quantity = va.resource_type.unit
                else:
                    raise ValidationError(dist_event.to_agent.nick + ' needs a virtual account, unable to create one.')
        et = EventType.objects.get(name='Cash Disbursement')
        # distribution.save() #?? used to be exchange; was anything changed?
        buckets = {}
        # import pdb; pdb.set_trace()
        for bucket in self.buckets.all():
            filter = serialized_filters.get(bucket.id) or "{}"
            filter = simplejson.loads(filter)
            bucket_rules = {}
            for br in bucket.bucket_rules.all():
                filter_rule = simplejson.loads(br.filter_rule)
                br_dict = {
                    "event_type": br.event_type.name,
                    "filter_rule": filter_rule,
                    "claim creation equation": br.claim_creation_equation,
                }
                bucket_rules[br.id] = br_dict
            bucket_dict = {
                "name": bucket.name,
                "filter": filter,
                "bucket_rules": bucket_rules,
            }
            buckets[bucket.id] = bucket_dict
        # import pdb; pdb.set_trace()
        content = {"buckets": buckets}
        json = simplejson.dumps(content, ensure_ascii=False, indent=4)
        # dist_ve = DistributionValueEquation(
        #    distribution_date = exchange.start_date,
        #   exchange = exchange,
        #    value_equation_link = self,
        #    value_equation_content = json, #todo
        # )
        # dist_ve.save()
        distribution.value_equation_link = self
        distribution.value_equation_content = json
        distribution.save()
        # import pdb; pdb.set_trace()
        if money_resource.owner():
            fa = money_resource.owner()
        else:
            fa = self.context_agent
        disbursement_event = EconomicEvent(
            event_type=et,
            event_date=distribution.distribution_date,
            from_agent=fa,
            to_agent=self.context_agent,
            context_agent=self.context_agent,
            distribution=distribution,
            quantity=amount_to_distribute,
            unit_of_quantity=money_resource.resource_type.unit,
            value=amount_to_distribute,
            unit_of_value=money_resource.resource_type.unit,
            is_contribution=False,
            resource_type=money_resource.resource_type,
            resource=money_resource,
        )
        # todo faircoin distribution
        # import pdb; pdb.set_trace()
        disbursement_event.save()
        if not money_resource.is_digital_currency_resource():
            money_resource.quantity -= amount_to_distribute
            money_resource.save()
        if events_to_distribute:
            # import pdb; pdb.set_trace()
            if len(events_to_distribute) == 1:
                cr = events_to_distribute[0]
                crd = IncomeEventDistribution(
                    distribution_date=distribution.distribution_date,
                    income_event=cr,
                    distribution_ref=distribution,
                    quantity=amount_to_distribute,
                    unit_of_quantity=cr.unit_of_quantity,
                )
                crd.save()
            else:
                for cr in events_to_distribute:
                    crd = IncomeEventDistribution(
                        distribution_date=distribution.distribution_date,
                        income_event=cr,
                        distribution_ref=distribution,
                        quantity=cr.quantity,
                        unit_of_quantity=cr.unit_of_quantity,
                    )
                    crd.save()
        # if input_distributions:
        #    for ind in input_distributions:
        #        ied = IncomeEventDistribution(
        #            distribution_date=distribution.distribution_date,
        #            income_event=ind,
        #            distribution=distribution,
        #            quantity=ind.quantity,
        #            unit_of_quantity=ind.unit_of_quantity,
        #        )
        #        ied.save()
        # import pdb; pdb.set_trace()
        for dist_event in distribution_events:
            dist_event.distribution = distribution
            dist_event.event_date = distribution.distribution_date
            # todo faircoin distribution
            # import pdb; pdb.set_trace()
            # digital_currency_resources for to_agents were created earlier in this method
            if dist_event.resource.is_digital_currency_resource():
                address_origin = self.context_agent.faircoin_address()
                address_end = dist_event.resource.digital_currency_address
                # what about network_fee?
                # handle when tx is broadcast
                quantity = dist_event.quantity
                state = "new"
                if testing:
                    tx_hash, broadcasted = send_fake_faircoins(address_origin, address_end, quantity)
                    state = "pending"
                    if broadcasted:
                        state = "broadcast"
                    dist_event.digital_currency_tx_hash = tx_hash
                dist_event.digital_currency_tx_state = state
                dist_event.event_reference = address_end
            dist_event.save()
            to_resource = dist_event.resource
            to_resource.quantity += dist_event.quantity
            to_resource.save()
            for dist_claim_event in dist_event.dist_claim_events:
                claim_from_contribution = dist_claim_event.claim
                if claim_from_contribution.new == True:
                    claim_from_contribution.unit_of_value = dist_event.unit_of_quantity
                    claim_from_contribution.date = distribution.distribution_date
                    claim_from_contribution.save()
                    ce_for_contribution = dist_claim_event.claim.claim_event
                    ce_for_contribution.claim = claim_from_contribution
                    ce_for_contribution.unit_of_value = dist_event.unit_of_quantity
                    ce_for_contribution.claim_event_date = distribution.distribution_date
                    ce_for_contribution.save()
                dist_claim_event.claim = claim_from_contribution
                dist_claim_event.event = dist_event
                dist_claim_event.unit_of_value = dist_event.unit_of_quantity
                dist_claim_event.claim_event_date = distribution.distribution_date
                dist_claim_event.save()

        return distribution

    def run_value_equation(self, amount_to_distribute, serialized_filters):
        # import pdb; pdb.set_trace()
        # start_time = time.time()
        atd = amount_to_distribute
        detail_sums = []
        claim_events = []
        contribution_events = []
        for bucket in self.buckets.all():
            # import pdb; pdb.set_trace()
            bucket_amount = bucket.percentage * amount_to_distribute / 100
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
                        # import pdb; pdb.set_trace()
                        ces, contributions = bucket.run_bucket_value_equation(amount_to_distribute=bucket_amount,
                                                                              context_agent=self.context_agent,
                                                                              serialized_filter=serialized_filter)
                        for ce in ces:
                            detail_sums.append(str(ce.claim.has_agent.id) + "~" + str(ce.value))
                            amount_distributed += ce.value
                        claim_events.extend(ces)
                        contribution_events.extend(contributions)
            if self.percentage_behavior == "remaining":
                amount_to_distribute = amount_to_distribute - amount_distributed
        agent_amounts = {}
        # import pdb; pdb.set_trace()
        for dtl in detail_sums:
            detail = dtl.split("~")
            if detail[0] in agent_amounts:
                amt = agent_amounts[detail[0]]
                agent_amounts[detail[0]] = amt + Decimal(detail[1])
            else:
                agent_amounts[detail[0]] = Decimal(detail[1])
        # import pdb; pdb.set_trace()
        et = EventType.objects.get(name='Distribution')
        distribution_events = []
        # import pdb; pdb.set_trace()
        for agent_id in agent_amounts:
            distribution_event = EconomicEvent(
                event_type=et,
                event_date=datetime.date.today(),
                from_agent=self.context_agent,
                to_agent=EconomicAgent.objects.get(id=int(agent_id)),
                context_agent=self.context_agent,
                quantity=agent_amounts[agent_id].quantize(Decimal('.01'), rounding=ROUND_HALF_UP),
                is_contribution=False,
                is_to_distribute=True,
            )
            agent_claim_events = [ce for ce in claim_events if ce.claim.has_agent.id == int(agent_id)]
            for ce in agent_claim_events:
                ce.event = distribution_event
            distribution_event.dist_claim_events = agent_claim_events
            distribution_events.append(distribution_event)
        # clean up rounding errors
        distributed = sum(de.quantity for de in distribution_events)
        delta = atd - distributed
        # import pdb; pdb.set_trace()
        if delta and distribution_events:
            max_dist = distribution_events[0]
            for de in distribution_events:
                if de.quantity > max_dist.quantity:
                    max_dist = de
            # import pdb; pdb.set_trace()
            max_dist.quantity = (max_dist.quantity + delta).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
            claim_events = max_dist.dist_claim_events
            for ce in claim_events:
                if ce.value > abs(delta):
                    ce.value += delta
                    claim = ce.claim
                    if claim.value_equation_bucket_rule.claim_rule_type == "debt-like":
                        claim.value += delta
                        if claim.value < 0:
                            claim.value = 0
                    break
        # end_time = time.time()
        # print("run_value_equation elapsed time was %g seconds" % (end_time - start_time))
        return distribution_events, contribution_events


FILTER_METHOD_CHOICES = (
    ('order', _('Order')),
    ('shipment', _('Shipment or Delivery')),
    ('dates', _('Date range')),
    ('process', _('Process')),
)


@python_2_unicode_compatible
class ValueEquationBucket(models.Model):
    name = models.CharField(_('name'), max_length=32)
    sequence = models.IntegerField(_('sequence'), default=0)
    value_equation = models.ForeignKey(ValueEquation,
                                       verbose_name=_('value equation'), related_name='buckets')
    filter_method = models.CharField(_('filter method'), null=True, blank=True,
                                     max_length=12, choices=FILTER_METHOD_CHOICES)
    percentage = models.DecimalField(_('bucket percentage'), max_digits=8, decimal_places=2, default=Decimal("0.0"))
    distribution_agent = models.ForeignKey(EconomicAgent,
                                           blank=True, null=True,
                                           related_name="value_equation_buckets", verbose_name=_('distribution agent'))
    filter_agent = models.ForeignKey(EconomicAgent,
                                     blank=True, null=True,
                                     related_name="value_equation_filter_buckets", verbose_name=_('filter agent'))
    created_by = models.ForeignKey(User, verbose_name=_('created by'),
                                   related_name='buckets_created', blank=True, null=True, editable=False)
    changed_by = models.ForeignKey(User, verbose_name=_('changed by'),
                                   related_name='buckets_changed', blank=True, null=True, editable=False)
    created_date = models.DateField(auto_now_add=True, blank=True, null=True, editable=False)
    changed_date = models.DateField(auto_now=True, blank=True, null=True, editable=False)

    class Meta:
        ordering = ('sequence',)

    def __str__(self):
        return ' '.join([
            'Bucket',
            str(self.sequence),
            '-',
            str(self.percentage) + '%',
            '-',
            self.name,
        ])

    def run_bucket_value_equation(self, amount_to_distribute, context_agent, serialized_filter):
        # import pdb; pdb.set_trace()
        # start_time = time.time()
        rules = self.bucket_rules.all()
        claim_events = []
        contribution_events = []
        bucket_events = self.gather_bucket_events(context_agent=context_agent, serialized_filter=serialized_filter)
        # import pdb; pdb.set_trace()
        # tot = Decimal("0.0")
        for vebr in rules:
            vebr_events = vebr.filter_events(bucket_events)
            contribution_events.extend(vebr_events)
            # hours = sum(e.quantity for e in vebr_events)
            # print vebr.filter_rule_deserialized(), "hours:", hours
            # tot += hours

        # print "total vebr hours:", tot
        claims = self.claims_from_events(contribution_events)
        # import pdb; pdb.set_trace()
        if claims:
            total_amount = 0
            for claim in claims:
                total_amount = total_amount + claim.share
            if total_amount > 0:
                # import pdb; pdb.set_trace()
                portion_of_amount = amount_to_distribute / total_amount
            else:
                portion_of_amount = Decimal("0.0")
            # import pdb; pdb.set_trace()
            if self.value_equation.percentage_behavior == "remaining":
                if portion_of_amount > 1:
                    portion_of_amount = Decimal("1.0")
            # import pdb; pdb.set_trace()
            ces = self.create_distribution_claim_events(claims=claims, portion_of_amount=portion_of_amount)
            claim_events.extend(ces)
        # end_time = time.time()
        # print("run_bucket_value_equation elapsed time was %g seconds" % (end_time - start_time))
        return claim_events, contribution_events

    def gather_bucket_events(self, context_agent, serialized_filter):
        # import pdb; pdb.set_trace()
        # start_time = time.time()
        ve = self.value_equation
        events = []
        filter = ""
        if self.filter_method == 'dates':
            from django_rea.valueaccounting.forms import DateRangeForm
            form = DateRangeForm()
            bucket_filter = form.deserialize(serialized_filter)
            start_date = None
            end_date = None
            bucket_context_agent = None
            if "start_date" in bucket_filter:
                start_date = bucket_filter["start_date"]
                filter = "".join([
                    filter,
                    "Start date: ",
                    start_date.strftime('%Y-%m-%d')
                ])
            if "end_date" in bucket_filter:
                end_date = bucket_filter["end_date"]
                filter = " ".join([
                    filter,
                    "End date:",
                    end_date.strftime('%Y-%m-%d')
                ])
            if "context_agent" in bucket_filter:
                bucket_context_agent = bucket_filter["context_agent"]
                filter = "".join([
                    filter,
                    "Context agent: ",
                    bucket_context_agent.nick
                ])
            if bucket_context_agent:
                events = EconomicEvent.objects.filter(context_agent=bucket_context_agent)
            else:
                events = EconomicEvent.objects.filter(context_agent=context_agent)
            if start_date and end_date:
                events = events.filter(event_date__range=(start_date, end_date))
            elif start_date:
                events = events.filter(event_date__gte=start_date)
            elif end_date:
                events = events.filter(event_date__gte=end_date)
            for evt in events:
                br = evt.bucket_rule(ve)
                value = evt.value
                if br:
                    # import pdb; pdb.set_trace()
                    value = br.compute_claim_value(evt)
                if value:
                    vpu = value / evt.quantity
                    evt.share = evt.quantity * vpu

        elif self.filter_method == 'order':
            from django_rea.valueaccounting.forms import OrderMultiSelectForm
            form = OrderMultiSelectForm(context_agent=context_agent)
            bucket_filter = form.deserialize(serialized_filter)
            orders = bucket_filter["orders"]
            if orders:
                order_string = ", ".join([str(o.id) for o in orders])
                filter = "".join([
                    "Orders: ",
                    order_string,
                ])
            events = []
            # import pdb; pdb.set_trace()
            for order in orders:
                for order_item in order.order_items():
                    # todo 3d: one method to chase
                    oi_events = order_item.compute_income_fractions(ve)
                    events.extend(oi_events)
                exchanges = Exchange.objects.filter(order=order)
                # import pdb; pdb.set_trace()
                for exchange in exchanges:
                    for payment in exchange.payment_events():  # todo: fix!
                        events.append(payment)
                    for work in exchange.work_events():
                        events.append(work)
        elif self.filter_method == 'shipment':
            from django_rea.valueaccounting.forms import ShipmentMultiSelectForm
            form = ShipmentMultiSelectForm(context_agent=context_agent)
            bucket_filter = form.deserialize(serialized_filter)
            shipment_events = bucket_filter["shipments"]
            if shipment_events:
                ship_string = ", ".join([str(s.id) for s in shipment_events])
                filter = "".join([
                    "Shipments: ",
                    ship_string,
                ])
            # lots = [e.resource for e in shipment_events]
            # import pdb; pdb.set_trace()
            events = []
            # tot = Decimal("0.0")
            for ship in shipment_events:
                resource = ship.resource
                qty = ship.quantity
                # todo 3d: two methods to chase
                if resource:
                    events.extend(resource.compute_shipment_income_shares(ve, qty))  # todo: fix
                else:
                    events.extend(ship.compute_income_fractions_for_process(ve))
                    # hours = sum(e.quantity for e in events)
                    # print ship, "hours:", hours
                    # tot += hours

                    # print "total event hours:", tot
        elif self.filter_method == 'process':
            # todo exchange redesign fallout
            from django_rea.valueaccounting.forms import ProcessMultiSelectForm
            form = ProcessMultiSelectForm(context_agent=context_agent)
            bucket_filter = form.deserialize(serialized_filter)
            processes = bucket_filter["processes"]
            if processes:
                process_string = ", ".join([str(proc.id) for proc in processes])
                filter = "".join([
                    "Processes: ",
                    process_string,
                ])
            events = []
            # import pdb; pdb.set_trace()
            visited = set()
            for proc in processes:
                order_item = None
                qty = sum(pe.quantity for pe in proc.production_events())
                if not qty:
                    qty = Decimal("1.0")
                proc_events = []
                # visited = set()
                proc.compute_income_shares(ve, order_item, qty, proc_events, visited)
                events.extend(proc_events)

        for event in events:
            event.filter = filter
        # end_time = time.time()
        # print("gather_bucket_events elapsed time was %g seconds" % (end_time - start_time))
        return events

    def claims_from_events(self, events):
        # import pdb; pdb.set_trace()
        claims = []
        for event in events:
            fraction = 1
            if event.value:
                try:
                    fraction = event.share / event.value
                except AttributeError:
                    pass
            existing_claim = next((c for c in claims if c.event == event), 0)
            if existing_claim:
                claim = existing_claim
                addition = claim.original_value * fraction
                claim.share += addition
            else:
                if not event.context_agent.compatible_value_equation(self.value_equation):
                    context_agent = self.value_equation.context_agent
                    claim = event.get_unsaved_context_agent_claim(context_agent, event.vebr)
                else:
                    claim = event.get_unsaved_contribution_claim(event.vebr)
                if claim.value:
                    claim.share = claim.original_value * fraction
                    claim.event = event
                    claims.append(claim)
        return claims

    def create_distribution_claim_events(self, portion_of_amount, claims):
        # import pdb; pdb.set_trace()
        claim_events = []
        # if claims == None:
        #    claims = self.gather_claims()
        for claim in claims:
            distr_amt = claim.share * portion_of_amount
            distr_amt = distr_amt.quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
            # if distr_amt > claim.value:
            #    distr_amt = claim.value
            if claim.value_equation_bucket_rule.claim_rule_type == "debt-like":
                claim.value = claim.value - distr_amt
            elif claim.value_equation_bucket_rule.claim_rule_type == "once":
                claim.value = 0
            claim.event.distr_amt = distr_amt
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
                reason = " The reason the value added is less than the contribution value is that the contribution's value was not all used for this deliverable."
            claim.event.explanation = "".join([
                "This contribution added ", str(share), " ", unit_of_value,
                " of value",
                sel,
                excuse,
                ".",
                reason,
            ])

            claim_event = ClaimEvent(
                claim=claim,
                value=distr_amt,
                unit_of_value=claim.unit_of_value,
                event_effect="-",
            )
            claim_events.append(claim_event)
        return claim_events

    def change_form(self):
        from django_rea.valueaccounting.forms import ValueEquationBucketForm
        return ValueEquationBucketForm(instance=self, prefix=str(self.id))

    def rule_form(self):
        from django_rea.valueaccounting.forms import ValueEquationBucketRuleForm
        return ValueEquationBucketRuleForm(prefix=str(self.id))

    def rule_filter_form(self):
        from django_rea.valueaccounting.forms import BucketRuleFilterSetForm
        ca = None
        pattern = None
        # import pdb; pdb.set_trace()
        if self.value_equation.context_agent:
            ca = self.value_equation.context_agent
        uc = UseCase.objects.get(identifier='val_equation')
        patterns = ProcessPattern.objects.usecase_patterns(use_case=uc)
        if patterns.count() > 0:
            pattern = patterns[0]
        return BucketRuleFilterSetForm(prefix=str(self.id), context_agent=ca, event_type=None, pattern=pattern)

    def filter_entry_form(self, data=None):
        # import pdb; pdb.set_trace()
        form = None
        if self.filter_method == "order":
            from django_rea.valueaccounting.forms import OrderMultiSelectForm
            if data == None:
                form = OrderMultiSelectForm(prefix=str(self.id), context_agent=self.value_equation.context_agent)
            else:
                form = OrderMultiSelectForm(prefix=str(self.id), context_agent=self.value_equation.context_agent,
                                            data=data)
        elif self.filter_method == "shipment":
            from django_rea.valueaccounting.forms import ShipmentMultiSelectForm  # todo: fix
            if data == None:
                form = ShipmentMultiSelectForm(prefix=str(self.id), context_agent=self.value_equation.context_agent)
            else:
                form = ShipmentMultiSelectForm(prefix=str(self.id), context_agent=self.value_equation.context_agent,
                                               data=data)
        elif self.filter_method == "process":
            from django_rea.valueaccounting.forms import ProcessMultiSelectForm
            if data == None:
                form = ProcessMultiSelectForm(prefix=str(self.id), context_agent=self.value_equation.context_agent)
            else:
                form = ProcessMultiSelectForm(prefix=str(self.id), context_agent=self.value_equation.context_agent,
                                              data=data)
        elif self.filter_method == "dates":
            from django_rea.valueaccounting.forms import DateRangeForm
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


@python_2_unicode_compatible
class ValueEquationBucketRule(models.Model):
    value_equation_bucket = models.ForeignKey(ValueEquationBucket,
                                              verbose_name=_('value equation bucket'), related_name='bucket_rules')
    event_type = models.ForeignKey(EventType,
                                   related_name="bucket_rules", verbose_name=_('event type'))
    filter_rule = models.TextField(_('filter rule'), null=True, blank=True)
    # todo: thinking we can get rid of division_rule, see if we have requirement
    division_rule = models.CharField(_('division rule'),
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

    def __str__(self):
        return ' '.join([
            'rule for:',
            self.value_equation_bucket.__str__(),
            '-',
            self.event_type.name,
        ])

    def filter_rule_deserialized(self):
        if self.filter_rule:
            from django_rea.valueaccounting.forms import BucketRuleFilterSetForm
            form = BucketRuleFilterSetForm(prefix=str(self.id), context_agent=None, event_type=None, pattern=None)
            # import pdb; pdb.set_trace()
            return form.deserialize(json=self.filter_rule)
        else:
            return self.filter_rule

    def filter_events(self, events):
        # import pdb; pdb.set_trace()
        json = self.filter_rule_deserialized()
        process_types = []
        resource_types = []
        if 'process_types' in json.keys():
            process_types = json['process_types']
        if 'resource_types' in json.keys():
            resource_types = json['resource_types']
        vebr_filter = self.filter_rule_display_list()
        events = [e for e in events if e.event_type == self.event_type]
        if process_types:
            events_with_processes = [e for e in events if e.process]
            events = [e for e in events_with_processes if e.process.process_type in process_types]
        if resource_types:
            events = [e for e in events if e.resource_type in resource_types]
        for e in events:
            e.vebr = self
            e.vebr.filter = vebr_filter + " " + e.filter
        return events

    def normalize_equation(self):
        eq = self.claim_creation_equation.split(" ")
        for i, x in enumerate(eq):
            eq[i] = x.replace("_", "")
            try:
                y = Decimal(x)
                eq[i] = "".join(["Decimal('", x, "')"])
            except InvalidOperation:
                continue
        s = " "
        return s.join(eq)

    def compute_claim_value(self, event):
        # import pdb; pdb.set_trace()
        equation = self.normalize_equation()
        safe_list = ['math', ]
        safe_dict = dict([(k, locals().get(k, None)) for k in safe_list])
        safe_dict['Decimal'] = Decimal
        safe_dict['quantity'] = event.quantity
        safe_dict['valuePerUnit'] = event.value_per_unit()
        safe_dict['pricePerUnit'] = event.resource_type.price_per_unit
        if event.resource:
            safe_dict['valuePerUnitOfUse'] = event.resource.value_per_unit_of_use
        safe_dict['value'] = event.value
        # safe_dict['importance'] = event.importance()
        # safe_dict['reputation'] = event.from_agent.reputation
        # safe_dict['seniority'] = Decimal(event.seniority())
        value = eval(equation, {"__builtins__": None}, safe_dict)
        return value

    def default_equation(self):
        et = self.event_type
        return et.default_event_value_equation()

    def filter_rule_display_list(self):
        json = self.filter_rule_deserialized()
        pts = []
        rts = []
        if 'process_types' in json.keys():
            pts = json['process_types']
        if 'resource_types' in json.keys():
            rts = json['resource_types']
        filter = ""
        # for pt in pts:
        #    filter += pt.name + ", "
        # for rt in rts:
        #    filter += rt.name + ","
        if pts:
            filter = ", ".join([pt.name for pt in pts])
        if pts and rts:
            filter = ", ".join(filter, [pt.name for pt in pts])
        elif rts:
            filter = ", ".join([rt.name for rt in rts])
        return filter

    def test_results(self):
        # import pdb; pdb.set_trace()
        fr = self.filter_rule_deserialized()
        pts = []
        rts = []
        if 'process_types' in fr.keys():
            pts = fr['process_types']
        if 'resource_types' in fr.keys():
            rts = fr['resource_types']
        events = EconomicEvent.objects.filter(context_agent=self.value_equation_bucket.value_equation.context_agent,
                                              event_type=self.event_type)
        if pts:
            events = events.filter(process__process_type__in=pts)
        if rts:
            events = events.filter(resource_type__in=rts)
        return events

    def change_form(self):
        from django_rea.valueaccounting.forms import ValueEquationBucketRuleForm
        return ValueEquationBucketRuleForm(prefix="vebr" + str(self.id), instance=self)

    def change_filter_form(self):
        from django_rea.valueaccounting.forms import BucketRuleFilterSetForm
        ca = None
        pattern = None
        # import pdb; pdb.set_trace()
        if self.value_equation_bucket.value_equation.context_agent:
            ca = self.value_equation_bucket.value_equation.context_agent
        uc = UseCase.objects.get(identifier='val_equation')
        patterns = ProcessPattern.objects.usecase_patterns(use_case=uc)
        if patterns.count() > 0:
            pattern = patterns[0]
        json = self.filter_rule_deserialized()
        return BucketRuleFilterSetForm(prefix="vebrf" + str(self.id), initial=json, context_agent=ca,
                                       event_type=self.event_type, pattern=pattern)


class IncomeEventDistribution(models.Model):
    distribution_date = models.DateField(_('distribution date'))
    # next field obsolete
    distribution = models.ForeignKey(Exchange,
                                     blank=True, null=True,
                                     verbose_name=_('distribution'), related_name='cash_receipts', default=None)
    distribution_ref = models.ForeignKey("Distribution",
                                         blank=True, null=True,
                                         verbose_name=_('distribution'), related_name='income_events')
    income_event = models.ForeignKey(EconomicEvent,
                                     related_name="distributions", verbose_name=_('income event'))
    quantity = models.DecimalField(_('quantity'), max_digits=8, decimal_places=2,
                                   default=Decimal("0.0"))
    unit_of_quantity = models.ForeignKey("Unit", blank=True, null=True,
                                         verbose_name=_('unit'), related_name="units")


@python_2_unicode_compatible
class Claim(models.Model):
    value_equation_bucket_rule = models.ForeignKey("ValueEquationBucketRule",
                                                   blank=True, null=True,
                                                   related_name="claims", verbose_name=_('value equation bucket rule'))
    claim_date = models.DateField(_('claim date'))
    has_agent = models.ForeignKey("EconomicAgent",
                                  blank=True, null=True,
                                  related_name="has_claims", verbose_name=_('has'))
    against_agent = models.ForeignKey("EconomicAgent",
                                      blank=True, null=True,
                                      related_name="claims_against", verbose_name=_('against'))
    context_agent = models.ForeignKey("EconomicAgent",
                                      blank=True, null=True,
                                      limit_choices_to={"is_context": True, },
                                      related_name="claims", verbose_name=_('context agent'),
                                      on_delete=models.SET_NULL)
    value = models.DecimalField(_('value'), max_digits=8, decimal_places=2,
                                default=Decimal("0.0"))
    unit_of_value = models.ForeignKey("Unit", blank=True, null=True,
                                      verbose_name=_('unit of value'), related_name="claim_value_units")
    original_value = models.DecimalField(_('original value'), max_digits=8, decimal_places=2,
                                         default=Decimal("0.0"))
    claim_creation_equation = models.TextField(_('creation equation'), null=True, blank=True)

    slug = models.SlugField(_("Page name"), editable=False)

    class Meta:
        ordering = ('claim_date',)

    def __str__(self):
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

    def format_value(self, value):
        if self.unit_of_value:
            if self.unit_of_value.symbol:
                value_string = "".join([self.unit_of_value.symbol, str(value)])
            else:
                value_string = " ".join([str(value), self.unit_of_value.abbrev])
        else:
            value_string = str(value)
        return value_string

    def original_value_formatted(self):
        value = self.original_value
        return self.format_value(value)

    def value_formatted(self):
        value = self.value
        return self.format_value(value)

    def distribution_events(self):
        return self.claim_events.filter(event__event_type__name="Distribution")


EVENT_EFFECT_CHOICES = (
    ('+', _('increase')),
    ('-', _('decrease')),
)


@python_2_unicode_compatible
class ClaimEvent(models.Model):
    event = models.ForeignKey("EconomicEvent",
                              blank=True, null=True,
                              related_name="claim_events", verbose_name=_('claim event'))
    claim = models.ForeignKey(Claim,
                              related_name="claim_events", verbose_name=_('claims'))
    claim_event_date = models.DateField(_('claim event date'), default=datetime.date.today)
    value = models.DecimalField(_('value'), max_digits=8, decimal_places=2)
    unit_of_value = models.ForeignKey("Unit", blank=True, null=True,
                                      verbose_name=_('unit of value'), related_name="claim_event_value_units")
    event_effect = models.CharField(_('event effect'),
                                    max_length=12, choices=EVENT_EFFECT_CHOICES)

    class Meta:
        ordering = ('claim_event_date',)

    def __str__(self):
        if self.unit_of_value:
            value_string = " ".join([str(self.value), self.unit_of_value.abbrev])
        else:
            value_string = str(self.value)
        if self.event:
            event_str = self.event.__str__()
        else:
            event_str = "none"
        return ' '.join([
            'event:',
            event_str,
            'affecting claim:',
            self.claim.__str__(),
            'value:',
            value_string,
        ])

    def update_claim(self):
        if self.event_effect == "+":
            self.claim.value += self.value
        else:
            self.claim.value -= self.value
        self.claim.save()

    def value_formatted(self):
        # import pdb; pdb.set_trace()
        value = self.value
        if self.unit_of_value:
            if self.unit_of_value.symbol:
                value_string = "".join([self.unit_of_value.symbol, str(value)])
            else:
                value_string = " ".join([str(value), self.unit_of_value.abbrev])
        else:
            value_string = str(value)
        return value_string

