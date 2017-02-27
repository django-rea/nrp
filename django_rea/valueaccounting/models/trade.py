from __future__ import print_function
from decimal import *
import datetime

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import python_2_unicode_compatible

from ._utils import unique_slugify

from .types import EventType


class ExchangeManager(models.Manager):
    def demand_exchanges(self, start=None, end=None):
        if start and end:
            exchanges = Exchange.objects.filter(use_case__identifier="demand_xfer").filter(
                start_date__range=[start, end])
        else:
            exchanges = Exchange.objects.filter(use_case__identifier="demand_xfer")
        # exchs = list(exchanges)
        # exchs.sort(lambda x, y: cmp(y.start_date, x.start_date))
        # return exchs
        return exchanges

    def supply_exchanges(self, start=None, end=None):
        if start and end:
            exchanges = Exchange.objects.filter(use_case__identifier="supply_xfer").filter(
                start_date__range=[start, end])
        else:
            exchanges = Exchange.objects.filter(use_case__identifier="supply_xfer")
        # exchs = list(exchanges)
        # exchs.sort(lambda x, y: cmp(y.start_date, x.start_date))
        # return exchs
        return exchanges

    def internal_exchanges(self, start=None, end=None):
        if start and end:
            exchanges = Exchange.objects.filter(use_case__identifier="intrnl_xfer").filter(
                start_date__range=[start, end])
        else:
            exchanges = Exchange.objects.filter(use_case__identifier="intrnl_xfer")
        return exchanges


@python_2_unicode_compatible
class Exchange(models.Model):
    name = models.CharField(_('name'), blank=True, max_length=128)
    process_pattern = models.ForeignKey("ProcessPattern",
                                        blank=True, null=True,
                                        verbose_name=_('pattern'), related_name='exchanges')
    use_case = models.ForeignKey("UseCase",
                                 blank=True, null=True,
                                 verbose_name=_('use case'), related_name='exchanges')
    exchange_type = models.ForeignKey("ExchangeType",
                                      blank=True, null=True,
                                      verbose_name=_('exchange type'), related_name='exchanges')
    context_agent = models.ForeignKey("EconomicAgent",
                                      blank=True, null=True,
                                      limit_choices_to={"is_context": True, },
                                      verbose_name=_('context agent'), related_name='exchanges')
    url = models.CharField(_('url'), max_length=255, blank=True, null=True)
    start_date = models.DateField(_('start date'))
    notes = models.TextField(_('notes'), blank=True)
    supplier = models.ForeignKey("EconomicAgent",
                                 blank=True, null=True,
                                 related_name="exchanges_as_supplier", verbose_name=_('supplier'))
    customer = models.ForeignKey("EconomicAgent",
                                 blank=True, null=True,
                                 related_name="exchanges_as_customer", verbose_name=_('customer'))
    order = models.ForeignKey("Order",
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

    def __str__(self):
        show_name = ""
        name = ""
        if self.name:
            name = self.name
        else:
            if self.exchange_type:
                show_name = self.exchange_type.name
            else:
                if self.use_case:
                    show_name = self.use_case.name
        return " ".join([
            name,
            show_name,
            "starting",
            self.start_date.strftime('%Y-%m-%d'),
        ])

    @models.permalink
    def get_absolute_url(self):
        return ('exchange_logging', (), {
            'exchange_type_id': "0",
            'exchange_id': str(self.id),
        })

    def save(self, *args, **kwargs):
        ext_name = ""
        # if self.exchange_type:
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
        if self.transfers.all():
            answer = False
        # elif self.resources.all():
        #    answer = False
        # elif self.commitments.all():
        #    answer = False
        return answer

    def slots_with_detail(self):
        # import pdb; pdb.set_trace()
        slots = self.exchange_type.transfer_types.all()
        slots = list(slots)
        transfers = self.transfers.all()
        default_to_agent = None
        default_from_agent = None
        for transfer in transfers:
            if transfer.transfer_type not in slots:
                slots.append(transfer.transfer_type)
            if not default_to_agent:
                if transfer.is_reciprocal():
                    default_to_agent = transfer.from_agent()
                else:
                    default_to_agent = transfer.to_agent()
            if not default_from_agent:
                if transfer.is_reciprocal():
                    default_from_agent = transfer.to_agent()
                else:
                    default_from_agent = transfer.from_agent()
        for slot in slots:
            slot.xfers = []
            slot.total = 0
            for transfer in transfers:
                if transfer.transfer_type == slot:
                    slot.xfers.append(transfer)
                    if transfer.actual_value():
                        slot.total += transfer.actual_value()
                    elif transfer.actual_quantity():
                        slot.total += transfer.actual_quantity()
            # import pdb; pdb.set_trace()
            if slot.is_reciprocal:
                slot.default_from_agent = default_to_agent
                slot.default_to_agent = default_from_agent
            else:
                slot.default_from_agent = default_from_agent
                slot.default_to_agent = default_to_agent
            if slot.is_currency and self.exchange_type.use_case != UseCase.objects.get(identifier="intrnl_xfer"):
                if not slot.give_agent_is_context:
                    slot.default_from_agent = None  # logged on agent
                if not slot.receive_agent_is_context:
                    slot.default_to_agent = None  # logged on agent
        return slots

    def work_events(self):
        return self.events.filter(
            event_type__relationship='work')

    def events(self):
        events = []
        for transfer in self.transfers.all():
            for event in transfer.events.all():
                events.append(event)
        return events

    def transfer_events(self):
        # todo exchange redesign fallout?
        # obsolete? or just used wrong?
        # exchange method
        print("obsolete exchange.transfer_event?")
        events = []
        for transfer in self.transfers.all():
            if not transfer.is_reciprocal():
                for event in transfer.events.all():
                    events.append(event)
        return events

    def reciprocal_transfer_events(self):
        # todo exchange redesign fallout?
        # exchange method
        events = []
        for transfer in self.transfers.all():
            if transfer.is_reciprocal():
                for event in transfer.events.all():
                    events.append(event)
        return events

    def can_have_reciprocal_transfers(self):
        ext = self.exchange_type
        if ext.transfer_types_reciprocal():
            return True
        return False

    # todo:not tested
    def transfer_give_events(self):
        # not reciprocal
        events = []
        et_give = EventType.objects.get(name="Give")
        for transfer in self.transfers.all():
            if not transfer.is_reciprocal():
                for event in transfer.events.all():
                    if event.event_type == et_give:
                        events.append(event)
        return events

    # todo:not tested
    def transfer_receive_events(self):
        # not reciprocal
        events = []
        et_receive = EventType.objects.get(name="Receive")
        for transfer in self.transfers.all():
            if not transfer.is_reciprocal():
                for event in transfer.events.all():
                    if event.event_type == et_receive:
                        events.append(event)
        return events

    # todo:not tested
    def reciprocal_transfer_give_events(self):
        events = []
        et_give = EventType.objects.get(name="Give")
        for transfer in self.transfers.all():
            if transfer.is_reciprocal():
                for event in transfer.events.all():
                    if event.event_type == et_give:
                        events.append(event)
        return events

    def payment_events(self):
        events = self.reciprocal_transfer_give_events()
        return [evt for evt in events if evt.transfer.transfer_type.is_currency]

    # todo:not tested
    def reciprocal_transfer_receive_events(self):
        events = []
        et_receive = EventType.objects.get(name="Receive")
        for transfer in self.transfers.all():
            if transfer.is_reciprocal():
                for event in transfer.events.all():
                    if event.event_type == et_receive:
                        events.append(event)
        return events

    # todo: do we need these?  if not, delete
    # def uncommitted_transfer_events(self):
    #    return self.events.filter(
    #        event_type__name='Transfer',
    #        commitment=None)

    # def uncommitted_rec_transfer_events(self):
    #    return self.events.filter(
    #        event_type__name='Reciprocal Transfer',
    #        commitment=None)

    def sorted_events(self):
        events = self.events().order_by("event_type__name")
        return events

    def flow_type(self):
        return "Exchange"

    def flow_class(self):
        return "exchange"

    def flow_description(self):
        return self.__str__()

    def resource_receive_events(self):
        # todo exchange redesign fallout
        if self.use_case.name == "Incoming Exchange":
            return [evt for evt in self.transfer_receive_events() if evt.resource]
        else:
            return []

    def expense_events(self):
        # todo exchange redesign fallout
        if self.use_case.name == "Incoming Exchange":
            return [evt for evt in self.transfer_receive_events() if not evt.resource]
        else:
            return []

    def roll_up_value(self, trigger_event, path, depth, visited, value_equation=None):
        """ Rolling up value from an exchange for a resource.

            trigger_event is a receipt for a resource.
            All of the expenses and work contributions in the Exchange
            must be spread among all of the receipts, with this receipt
            getting its share.
        """

        # exchange method
        # import pdb; pdb.set_trace()
        values = Decimal("0.0")
        if trigger_event not in visited:
            visited.add(trigger_event)
            depth += 1
            self.depth = depth
            depth += 1
            path.append(self)
            values = Decimal("0.0")
            # todo exchange redesign fallout
            # just guessing at receipts and payments
            # to eliminate error messages
            # Note: trigger_event is also one of the receipts
            receipts = self.resource_receive_events()
            trigger_fraction = 1
            if len(receipts) > 1:
                # what fraction is the trigger_event of the total value of receipts
                rsum = sum(r.value for r in receipts)
                trigger_fraction = trigger_event.value / rsum
            payments = [evt for evt in self.payment_events() if evt.to_agent == trigger_event.from_agent]
            # share =  quantity / trigger_event.quantity
            if len(payments) == 1:
                evt = payments[0]
                # import pdb; pdb.set_trace()
                value = evt.quantity
                br = evt.bucket_rule(value_equation)
                if br:
                    # import pdb; pdb.set_trace()
                    value = br.compute_claim_value(evt)
                values += value * trigger_fraction
                evt.depth = depth
                path.append(evt)
                if evt.resource:
                    contributions = evt.resource.cash_contribution_events()
                    depth += 1
                    # todo 3d: done, maybe
                    for c in contributions:
                        c.depth = depth
                        path.append(c)
            elif len(payments) > 1:
                total = sum(p.quantity for p in payments)
                for evt in payments:
                    fraction = evt.quantity / total
                    # depth += 1
                    if evt.resource:
                        contributions = evt.resource.cash_contribution_events()
                        # evt.share = evt.quantity * share * fraction * trigger_fraction
                        evt.share = evt.quantity * fraction * trigger_fraction
                        evt.depth = depth
                        path.append(evt)
                        values += evt.share
                        # todo 3d: do multiple payments make sense for cash contributions?
                    else:
                        value = evt.quantity
                        br = evt.bucket_rule(value_equation)
                        if br:
                            # import pdb; pdb.set_trace()
                            value = br.compute_claim_value(evt)
                        evt.share = value * fraction * trigger_fraction
                        evt.depth = depth
                        path.append(evt)
                        values += evt.share
            # todo exchange redesign fallout
            # import pdb; pdb.set_trace()
            expenses = self.expense_events()
            for ex in expenses:
                ex.depth = depth
                path.append(ex)
                value = ex.value
                values += value * trigger_fraction
                exp_payments = [evt for evt in self.payment_events() if evt.to_agent == ex.from_agent]
                # exp_payments = self.payment_events().filter(to_agent=ex.from_agent)
                for exp in exp_payments:
                    depth += 1
                    exp.depth = depth
                    path.append(exp)
                    depth -= 1
                depth -= 1

            for evt in self.work_events():
                # import pdb; pdb.set_trace()
                value = evt.quantity
                br = evt.bucket_rule(value_equation)
                if br:
                    # import pdb; pdb.set_trace()
                    value = br.compute_claim_value(evt)
                # evt.share = value * share * trigger_fraction
                evt.share = value * trigger_fraction
                values += evt.share
                evt.depth = depth
                path.append(evt)
        event_value = values
        return event_value

    def compute_income_shares(self, value_equation, trigger_event, quantity, events, visited):
        # exchange method
        # import pdb; pdb.set_trace()
        if trigger_event not in visited:
            visited.add(trigger_event)

            trigger_fraction = 1
            share = quantity / trigger_event.quantity
            # todo exchange redesign fallout
            receipts = self.resource_receive_events()
            if receipts:
                if len(receipts) > 1:
                    rsum = sum(r.value for r in receipts)
                    trigger_fraction = trigger_event.value / rsum
            payments = [evt for evt in self.payment_events() if evt.to_agent == trigger_event.from_agent]
            """
            else:
                #todo exchange redesign fallout
                #change transfer_events, that method is obsolete
                xfers = self.transfer_events()
                if xfers:
                    payments = self.cash_receipt_events().filter(from_agent=trigger_event.to_agent)
            """
            if len(payments) == 1:
                evt = payments[0]
                value = evt.quantity
                contributions = []
                # import pdb; pdb.set_trace()
                if evt.resource:
                    # todo exchange redesign fallout
                    # do cash_contribution_events work?
                    candidates = evt.resource.cash_contribution_events()
                    for cand in candidates:
                        br = cand.bucket_rule(value_equation)
                        if br:
                            cand.value = br.compute_claim_value(cand)
                            if cand.value:
                                contributions.append(cand)
                    for ct in contributions:
                        fraction = ct.quantity / value
                        ct.share = ct.value * share * fraction * trigger_fraction
                        # ct.share = ct.value * fraction * trigger_fraction
                        events.append(ct)
                if not contributions:
                    # if contributions were credited,
                    # do not give credit for payment.
                    # import pdb; pdb.set_trace()
                    br = evt.bucket_rule(value_equation)
                    if br:
                        value = br.compute_claim_value(evt)
                    evt.value = value
                    evt.save()
                    evt.share = value * share * trigger_fraction
                    events.append(evt)

            elif len(payments) > 1:
                total = sum(p.quantity for p in payments)
                for evt in payments:
                    fraction = evt.quantity / total
                    # if evt.resource:
                    if evt.resource and not xfers:
                        contributions = evt.resource.cash_contribution_events()
                        evt.share = evt.quantity * share * fraction * trigger_fraction
                        # evt.share = evt.quantity * fraction * trigger_fraction
                        events.append(evt)
                        # todo 3d: do multiple payments make sense for cash contributions?
                        # equip logging changes
                        # apparently: see treatment in compute_income_shares_for_use below
                    else:
                        value = evt.quantity
                        br = evt.bucket_rule(value_equation)
                        if br:
                            # import pdb; pdb.set_trace()
                            value = br.compute_claim_value(evt)
                        evt.value = value
                        evt.save()
                        evt.share = value * share * fraction * trigger_fraction
                        # evt.share = value * fraction * trigger_fraction
                        events.append(evt)

            expenses = self.expense_events()
            for ex in expenses:
                exp_payments = [evt for evt in self.payment_events() if evt.to_agent == ex.from_agent]
                for exp in exp_payments:
                    value = exp.quantity
                    br = exp.bucket_rule(value_equation)
                    if br:
                        # import pdb; pdb.set_trace()
                        value = br.compute_claim_value(exp)
                    exp.value = value
                    exp.save()
                    exp.share = value * share * trigger_fraction
                    events.append(exp)

            for evt in self.work_events():
                # import pdb; pdb.set_trace()
                if evt.is_contribution:
                    value = evt.quantity
                    br = evt.bucket_rule(value_equation)
                    if br:
                        # import pdb; pdb.set_trace()
                        value = br.compute_claim_value(evt)
                    # evt.share = value * share * trigger_fraction
                    evt.value = value
                    evt.save()
                    evt.share = value * share * trigger_fraction
                    # evt.share = value * trigger_fraction
                    events.append(evt)

    def compute_income_shares_for_use(self, value_equation, use_event, use_value, resource_value, events, visited):
        # exchange method
        # import pdb; pdb.set_trace()
        locals = []
        if self not in visited:
            visited.add(self)
            resource = use_event.resource
            trigger_fraction = 1
            # equip logging changes
            # todo exchange redesign fallout
            receipts = self.resource_receive_events()
            # needed?
            # payments = [evt for evt in self.payment_events() if evt.to_agent==trigger_event.from_agent]
            payments = self.payment_events()
            if receipts:
                if len(receipts) > 1:
                    rsum = sum(r.value for r in receipts)
                    # trigger_fraction = use_event.value / rsum
                    # payments = self.payment_events().filter(to_agent=trigger_event.from_agent)
                    # share =  quantity / trigger_event.quantity
            """
            else:
                #todo exchange redesign fallout
                xfers = self.transfers.all()
                if xfers:
                    #payments = self.cash_receipt_events().filter(from_agent=trigger_event.to_agent)
                    payments = self.reciprocal_transfer_receive_events()
            """
            cost = Decimal("0")
            if payments:
                cost = sum(p.quantity for p in payments)
            # equip logging changes
            # does this make any sense for use events?
            use_share = use_value
            if cost:
                use_share = use_value / cost
            if len(payments) == 1:
                evt = payments[0]
                contributions = []
                if evt.resource:
                    contributions = evt.resource.cash_contribution_events()
                    # import pdb; pdb.set_trace()
                    for ct in contributions:
                        fraction = ct.quantity / resource_value
                        # todo 3d: changed
                        ct.share = use_value * fraction
                        events.append(ct)
                if not contributions:
                    # if contributions were credited,
                    # do not give credit for payment.
                    value = evt.quantity
                    br = evt.bucket_rule(value_equation)
                    if br:
                        value = br.compute_claim_value(evt)
                    # evt.share = value * use_share?
                    evt.share = use_value
                    events.append(evt)
            elif len(payments) > 1:
                total = sum(p.quantity for p in payments)
                for evt in payments:
                    # equip logging changes
                    # import pdb; pdb.set_trace()
                    payment_fraction = evt.quantity / total
                    value = evt.quantity
                    br = evt.bucket_rule(value_equation)
                    if br:
                        value = br.compute_claim_value(evt)
                    if evt.resource:
                        contributions = evt.resource.cash_contribution_events()
                        for ct in contributions:
                            # shd this be based on resource_value or cost/total?
                            resource_fraction = ct.quantity / resource_value
                            # is use_value relevant here? Or use_share (use_value / cost)?
                            # and since we have multiple payments, must consider total!
                            # share_addition = use_value * use_share * resource_fraction * payment_fraction
                            share_addition = use_value * resource_fraction * payment_fraction
                            existing_ct = next((evt for evt in events if evt == ct), 0)
                            # import pdb; pdb.set_trace()
                            if existing_ct:
                                # import pdb; pdb.set_trace()
                                existing_ct.share += share_addition

                            else:
                                ct.share = share_addition
                                events.append(ct)
                                locals.append(ct)
                    if not contributions:
                        # if contributions were credited,
                        # do not give credit for payment.
                        # evt.share = value * use_share * payment_fraction
                        evt.share = use_value * payment_fraction
                        events.append(evt)
            # import pdb; pdb.set_trace()
            for evt in self.work_events():
                # import pdb; pdb.set_trace()
                value = evt.quantity
                br = evt.bucket_rule(value_equation)
                if br:
                    # import pdb; pdb.set_trace()
                    value = br.compute_claim_value(evt)
                evt.value = value
                # todo 3d: changed
                fraction = value / resource_value
                evt.share = use_value * fraction
                events.append(evt)
            if locals:
                local_total = sum(lo.share for lo in locals)
                delta = use_value - local_total
                if delta:
                    max_share = locals[0]
                    for lo in locals:
                        if lo.share > max_share.share:
                            max_share = lo
                max_share.share = (max_share.share + delta)
                # local_total = sum(lo.share for lo in locals)
                # print "local_total:", local_total


@python_2_unicode_compatible
class Transfer(models.Model):
    name = models.CharField(_('name'), blank=True, max_length=128)
    transfer_type = models.ForeignKey("TransferType",
                                      blank=True, null=True,
                                      verbose_name=_('transfer type'), related_name='transfers')
    exchange = models.ForeignKey("Exchange",
                                 blank=True, null=True,
                                 verbose_name=_('exchange'), related_name='transfers')
    context_agent = models.ForeignKey("EconomicAgent",
                                      blank=True, null=True,
                                      limit_choices_to={"is_context": True, },
                                      verbose_name=_('context agent'), related_name='transfers')
    transfer_date = models.DateField(_('transfer date'))
    notes = models.TextField(_('notes'), blank=True)
    created_by = models.ForeignKey(User, verbose_name=_('created by'),
                                   related_name='transfers_created', blank=True, null=True, editable=False)
    changed_by = models.ForeignKey(User, verbose_name=_('changed by'),
                                   related_name='transfers_changed', blank=True, null=True, editable=False)
    created_date = models.DateField(auto_now_add=True, blank=True, null=True, editable=False)
    changed_date = models.DateField(auto_now=True, blank=True, null=True, editable=False)
    slug = models.SlugField(_("Page name"), editable=False)

    objects = ExchangeManager()

    class Meta:
        ordering = ('transfer_date',)
        verbose_name_plural = _("transfers")

    def __str__(self):
        show_name = ""
        from_name = ""
        to_name = ""
        unit = ""
        resource_string = ""
        qty = ""
        if self.transfer_type:
            show_name = self.transfer_type.name
        event = None
        if self.events.all():
            event = self.events.all()[0]
        if event:
            if event.from_agent:
                from_name = "from " + event.from_agent.name
            if event.to_agent:
                to_name = "to " + event.to_agent.name
            if event.resource_type:
                resource_string = event.resource_type.name
            if event.resource:
                resource_string = event.resource.__str__()
            qty = str(event.quantity)
            if event.unit_of_quantity:
                unit = event.unit_of_quantity.name
        else:
            commits = self.commitments.all()
            if commits:
                commit = commits[0]
                show_name = "(Planned) " + show_name
                if commit.from_agent:
                    from_name = "from " + commit.from_agent.name
                if commit.to_agent:
                    to_name = "to " + commit.to_agent.name
                if commit.resource_type:
                    resource_string = commit.resource_type.name
                qty = str(commit.quantity)
                if commit.unit_of_quantity:
                    unit = commit.unit_of_quantity.name

        return " ".join([
            #    name,
            show_name,
            from_name,
            to_name,
            qty,
            unit,
            resource_string,
            "on",
            self.transfer_date.strftime('%Y-%m-%d'),
        ])

    def commit_text(self):
        text = None
        give = None
        receive = None
        unit = ""
        resource = ""
        from_to = ""
        qty = ""
        give_text = ""
        receive_text = ""
        commits = self.commitments.all()
        if commits:
            et_give = EventType.objects.get(name="Give")
            et_receive = EventType.objects.get(name="Receive")
            for commit in commits:
                if commit.event_type == et_give:
                    give = commit
                elif commit.event_type == et_receive:
                    receive = commit
            either = commits[0]
            if either.resource_type:
                resource = either.resource_type.name + ","
            qty = str(either.quantity)
            if either.unit_of_quantity:
                unit = either.unit_of_quantity.abbrev
            if give:
                if give.to_agent:
                    give_text = "GIVE to " + give.to_agent.nick
            if receive:
                if receive.from_agent:
                    receive_text = "RECEIVE from " + receive.from_agent.nick
            if give:
                from_to = give_text
                if receive:
                    from_to += " "
            if receive:
                from_to = from_to + receive_text
            text = " ".join([
                qty,
                unit,
                resource,
                from_to,
            ])
        return text

    def commit_event_text(self):
        # import pdb; pdb.set_trace()
        text = None
        give = None
        receive = None
        unit = ""
        resource = ""
        from_to = ""
        qty = ""
        give_text = ""
        receive_text = ""
        events = self.events.all()
        if events:
            et_give = EventType.objects.get(name="Give")
            et_receive = EventType.objects.get(name="Receive")
            for event in events:
                if event.event_type == et_give:
                    give = event
                elif event.event_type == et_receive:
                    receive = event
            either = events[0]
            if either.resource_type:
                resource = either.resource_type.name + ","
            if either.resource:
                resource = str(either.resource) + ","
            qty = str(either.quantity)
            if either.unit_of_quantity:
                unit = either.unit_of_quantity.abbrev
            if give:
                if give.event_date:
                    give_text = "GIVE on " + str(give.event_date)
            if receive:
                if receive.event_date:
                    receive_text = "RECEIVE on " + str(receive.event_date)
            if give:
                from_to = give_text
                if receive:
                    from_to += ", "
            if receive:
                from_to = from_to + receive_text
            text = " ".join([
                qty,
                unit,
                resource,
                from_to,
            ])
        return text

    def event_text(self):
        # import pdb; pdb.set_trace()
        text = None
        give = None
        receive = None
        unit = ""
        resource = ""
        from_to = ""
        qty = ""
        give_text = ""
        receive_text = ""
        events = self.events.all()
        if events:
            et_give = EventType.objects.get(name="Give")
            et_receive = EventType.objects.get(name="Receive")
            for event in events:
                if event.event_type == et_give:
                    give = event
                elif event.event_type == et_receive:
                    receive = event
            either = events[0]
            if either.resource_type:
                resource = either.resource_type.name + ","
            if either.resource:
                resource = str(either.resource) + ","
            qty = str(either.quantity)
            if either.unit_of_quantity:
                unit = either.unit_of_quantity.abbrev
            if give:
                if give.to_agent:
                    give_text = "GIVE to " + give.to_agent.nick
                if give.event_date:
                    give_text += " on " + str(give.event_date)
            if receive:
                if receive.from_agent:
                    receive_text = "RECEIVE from " + receive.from_agent.nick
                if receive.event_date:
                    receive_text += " on " + str(receive.event_date)
            if give:
                from_to = give_text
                if receive:
                    from_to += ", "
            if receive:
                from_to = from_to + receive_text
            text = " ".join([
                qty,
                unit,
                resource,
                from_to,
            ])
        return text

    def commit_description(self):
        # import pdb; pdb.set_trace()
        commits = self.commitments.all()
        if commits:
            return commits[0].description
        else:
            return None

    def save(self, *args, **kwargs):
        if self.id:
            if not self.transfer_type:
                msg = " ".join(["No transfer type on transfer: ", str(self.id)])
                assert False, msg
        if self.transfer_type:
            super(Transfer, self).save(*args, **kwargs)

    def is_reciprocal(self):
        return self.transfer_type.is_reciprocal

    def give_event(self):
        # import pdb; pdb.set_trace()
        try:
            return self.events.get(event_type__name="Give")
        except EconomicEvent.DoesNotExist:
            return None

    def receive_event(self):
        try:
            return self.events.get(event_type__name="Receive")
        except EconomicEvent.DoesNotExist:
            return None

    def quantity(self):
        events = self.events.all()
        if events:
            return events[0].quantity
        else:
            commits = self.commitments.all()
            if commits:
                return commits[0].quantity
        return Decimal("0.0")

    def actual_quantity(self):
        events = self.events.all()
        if events:
            return events[0].quantity
        return Decimal("0.0")

    def unit_of_quantity(self):
        events = self.events.all()
        if events:
            return events[0].unit_of_quantity
        else:
            commits = self.commitments.all()
            if commits:
                return commits[0].unit_of_quantity
        return None

    def value(self):
        events = self.events.all()
        if events:
            return events[0].value
        else:
            commits = self.commitments.all()
            if commits:
                return commits[0].value
        return None

    def actual_value(self):
        events = self.events.all()
        if events:
            return events[0].value
        return Decimal("0.0")

    def unit_of_value(self):
        events = self.events.all()
        if events:
            return events[0].unit_of_value
        else:
            commits = self.commitments.all()
            if commits:
                return commits[0].unit_of_value
        return None

    def from_agent(self):
        events = self.events.all()
        if events:
            return events[0].from_agent
        else:
            commits = self.commitments.all()
            if commits:
                return commits[0].from_agent
        return None

    def to_agent(self):
        events = self.events.all()
        if events:
            return events[0].to_agent
        else:
            commits = self.commitments.all()
            if commits:
                return commits[0].to_agent
        return None

    def resource_type(self):
        events = self.events.all()
        if events:
            event = events[0]
            return event.resource_type
        else:
            commits = self.commitments.all()
            if commits:
                return commits[0].resource_type
        return None

    def resource_name(self):
        events = self.events.all()
        if events:
            event = events[0]
            resource_string = event.resource_type.name
            if event.resource:
                resource_string = event.resource.__str__()
            return resource_string
        return None

    def resource(self):
        events = self.events.all()
        resource = None
        if events:
            resource = events[0].resource
        return resource

    def is_deletable(self):
        if self.commitments.all():
            return False
        if self.events.all():
            return False
        return True

    def flow_type(self):
        return "Transfer"

    def flow_class(self):
        return "transfer"

    def flow_description(self):
        return self.__str__()

    def give_and_receive_resources(self):
        events = self.events.all()
        give_resource = None
        receive_resource = None
        et_give = EventType.objects.get(name="Give")
        if events:
            for ev in events:
                if ev.event_type == et_give:
                    give_resource = ev.resource
                else:
                    receive_resource = ev.resource
        return give_resource, receive_resource

    def form_prefix(self):
        return "TR" + str(self.id)

    def commit_transfer_form(self):
        from django_rea.valueaccounting.forms import TransferForm
        prefix = self.form_prefix()
        # import pdb; pdb.set_trace()
        init = {
            "event_date": datetime.date.today(),
            "resource_type": self.resource_type(),
            "quantity": self.quantity(),
            "value": self.value(),
            "unit_of_value": self.unit_of_value(),
            "from_agent": self.from_agent(),
            "to_agent": self.to_agent(),
        }
        return TransferForm(initial=init, transfer_type=self.transfer_type, context_agent=self.context_agent,
                            posting=False, prefix=prefix)

    def create_role_formset(self, data=None):
        # import pdb; pdb.set_trace()
        from django_rea.valueaccounting.views import resource_role_agent_formset
        return resource_role_agent_formset(prefix=self.form_prefix(), data=data)

    def change_commitments_form(self):
        from django_rea.valueaccounting.forms import TransferCommitmentForm
        prefix = self.form_prefix() + "C"
        commits = self.commitments.all()
        if commits:
            commit = commits[0]
            init = {
                "commitment_date": commit.commitment_date,
                "due_date": commit.due_date,
                "description": commit.description,
                "resource_type": commit.resource_type,
                "quantity": commit.quantity,
                "value": commit.value,
                "unit_of_value": commit.unit_of_value,
                "from_agent": commit.from_agent,
                "to_agent": commit.to_agent,
            }
            return TransferCommitmentForm(initial=init, transfer_type=self.transfer_type,
                                          context_agent=self.context_agent, posting=False, prefix=prefix)
        return None

    def change_events_form(self):
        # import pdb; pdb.set_trace()
        from django_rea.valueaccounting.forms import TransferForm
        prefix = self.form_prefix() + "E"
        events = self.events.all()
        if events:
            event = events[0]
            from_resource, resource = self.give_and_receive_resources()
            if from_resource and not resource:
                resource = from_resource
            init = {
                "resource": resource,
                "from_resource": from_resource,
                "description": event.description,
                "is_contribution": event.is_contribution,
                "event_reference": event.event_reference,
                "event_date": event.event_date,
                "description": event.description,
                "resource_type": event.resource_type,
                "quantity": event.quantity,
                "value": event.value,
                "unit_of_value": event.unit_of_value,
                "from_agent": event.from_agent,
                "to_agent": event.to_agent,
            }
            return TransferForm(initial=init, transfer_type=self.transfer_type, context_agent=self.context_agent,
                                resource_type=event.resource_type, posting=False, prefix=prefix)
        return None
