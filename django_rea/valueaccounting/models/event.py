from __future__ import print_function

import datetime
from decimal import *

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from django_rea.valueaccounting.models.agent import EconomicAgent

from ._utils import unique_slugify


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


TX_STATE_CHOICES = (
    ('new', _('New')),
    ('pending', _('Pending')),
    ('broadcast', _('Broadcast')),
    ('confirmed', _('Confirmed')),
)


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
        from django_rea.valueaccounting.models.resource import AgentResourceType
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
        from django_rea.valueaccounting.models.recipe import EventType
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
        from django_rea.valueaccounting.models.resource import EconomicResource
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
        from django_rea.valueaccounting.models.resource import AgentResourceType
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
        from django_rea.valueaccounting.models.distribution import ValueEquationBucketRule
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
        from django_rea.valueaccounting.models.distribution import (Claim, ClaimEvent)
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
        from django_rea.valueaccounting.models.distribution import (Claim, ClaimEvent)
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
        from django_rea.valueaccounting.models.distribution import (Claim, ClaimEvent)
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


class EventSummary(object):
    def __init__(self, agent, context_agent, resource_type, event_type, quantity, value=Decimal('0.0')):
        self.agent = agent
        self.context_agent = context_agent
        self.resource_type = resource_type
        self.event_type = event_type
        self.quantity = quantity
        self.value = value

    def key(self):
        return "-".join([
            str(self.agent.id),
            str(self.resource_type.id),
            str(self.project.id),
            str(self.event_type.id),
        ])

    def quantity_formatted(self):
        return self.quantity.quantize(Decimal('.01'), rounding=ROUND_HALF_UP)


class CachedEventSummary(models.Model):
    agent = models.ForeignKey(EconomicAgent,
                              blank=True, null=True,
                              related_name="cached_events", verbose_name=_('agent'))
    context_agent = models.ForeignKey("EconomicAgent",
                                      blank=True, null=True,
                                      verbose_name=_('context agent'), related_name='context_cached_events')
    resource_type = models.ForeignKey("EconomicResourceType",
                                      blank=True, null=True,
                                      verbose_name=_('resource type'), related_name='cached_events')
    event_type = models.ForeignKey("EventType",
                                   verbose_name=_('event type'), related_name='cached_events')
    resource_type_rate = models.DecimalField(_('resource type rate'), max_digits=8, decimal_places=2,
                                             default=Decimal("1.0"))
    importance = models.DecimalField(_('importance'), max_digits=3, decimal_places=0, default=Decimal("1"))
    reputation = models.DecimalField(_('reputation'), max_digits=8, decimal_places=2,
                                     default=Decimal("1.00"))
    quantity = models.DecimalField(_('quantity'), max_digits=8, decimal_places=2,
                                   default=Decimal("0.0"))
    value = models.DecimalField(_('value'), max_digits=8, decimal_places=2,
                                default=Decimal("0.0"))

    class Meta:
        ordering = ('agent', 'context_agent', 'resource_type')

    def __str__(self):
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
        # import pdb; pdb.set_trace()
        # todo: this code is obsolete, we don't want to roll up sub-projects anymore
        all_subs = context_agent.with_all_sub_agents()
        event_list = EconomicEvent.objects.filter(context_agent__in=all_subs)
        summaries = {}
        for event in event_list:
            key = "-".join([str(event.from_agent.id), str(event.context_agent.id), str(event.resource_type.id)])
            if not key in summaries:
                summaries[key] = EventSummary(event.from_agent, event.context_agent, event.resource_type,
                                              Decimal('0.0'))
            summaries[key].quantity += event.quantity
        summaries = summaries.values()
        for summary in summaries:
            ces = cls(
                agent=summary.agent,
                context_agent=summary.context_agent,
                resource_type=summary.resource_type,
                resource_type_rate=summary.resource_type.value_per_unit,
                # importance=summary.project.importance, todo: need this in agent?
                quantity=summary.quantity,
            )
            ces.save()
        return cls.objects.all()

    @classmethod
    def summarize_all_events(cls):
        # import pdb; pdb.set_trace()
        old_summaries = CachedEventSummary.objects.all()
        old_summaries.delete()
        event_list = EconomicEvent.objects.filter(is_contribution="true")
        summaries = {}
        # todo: very temporary hack
        context_agent = EconomicAgent.objects.get(name="Not defined")
        for event in event_list:
            # todo: very temporary hack
            if not event.context_agent:
                event.context_agent = context_agent
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
                quantity=summary.quantity,
            )
            ces.save()
        return cls.objects.all()

    def quantity_formatted(self):
        return self.quantity.quantize(Decimal('.01'), rounding=ROUND_HALF_UP)

    def value_formatted(self):
        return self.value.quantize(Decimal('.01'), rounding=ROUND_HALF_UP)

    def quantity_label(self):
        # return " ".join([self.resource_type.name, self.resource_type.unit.abbrev])
        return self.resource_type.name


@python_2_unicode_compatible
class AccountingReference(models.Model):
    code = models.CharField(_('code'), max_length=128, unique=True)
    name = models.CharField(_('name'), max_length=128)

    def __str__(self):
        return self.name
