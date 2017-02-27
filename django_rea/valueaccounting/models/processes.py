from __future__ import print_function
from decimal import *
import datetime

from django.db import models
from django.contrib.auth.models import User
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _


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


# todo: Order is used for both of the above types.
# maybe shd be renamed?
@python_2_unicode_compatible
class Order(models.Model):
    order_type = models.CharField(_('order type'), max_length=12,
                                  choices=ORDER_TYPE_CHOICES, default='customer')
    name = models.CharField(_('name'), max_length=255, blank=True,
                            help_text=_("appended to process labels for Work orders"))
    receiver = models.ForeignKey("EconomicAgent",
                                 blank=True, null=True,
                                 related_name="purchase_orders", verbose_name=_('receiver'))
    provider = models.ForeignKey("EconomicAgent",
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

    def __str__(self):
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
            provider_name = self.provider.nick
            provider_label = ", provider:"
        receiver_name = ""
        if self.receiver:
            receiver_name = self.receiver.nick
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
                {'order_id': str(self.id), })

    def exchange(self):
        # import pdb; pdb.set_trace()
        exs = Exchange.objects.filter(order=self)
        if exs:
            return exs[0]
        return None

    def node_id(self):
        return "-".join(["Order", str(self.id)])

    def timeline_title(self):
        return self.__str__()

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

    def process(self):  # todo: should this be on order_item?
        answer = None
        # todo: why rand, what difference does it make?
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
        # todo: needs process and project. Anything else? >>context agent
        # might not be worth refactoring out.
        if not due:
            due = self.due_date
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
        # todo: shd this generate_producing_process?
        return ct

    def create_order_item(self,
                          resource_type,
                          quantity,
                          user):
        # todo pr: may need return inheritance?
        # import pdb; pdb.set_trace()
        ptrt, inheritance = resource_type.main_producing_process_type_relationship()
        description = ""
        context_agent = None
        stage = None
        state = None
        if ptrt:
            event_type = ptrt.event_type
            stage = ptrt.stage
            state = ptrt.state
            description = ptrt.description
            context_agent = ptrt.process_type.context_agent
        else:
            if self.order_type == "customer":
                # todo exchange redesign fallout
                event_type = EventType.objects.get(name="Give")
                ois = self.order_items()
                if ois:
                    context_agent = ois[0].context_agent
            else:
                # todo wha?
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
        # import pdb; pdb.set_trace()
        if not due:
            due = self.due_date
        event_type = EventType.objects.get(name="Give")  # (relationship="shipment")
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
        # import pdb; pdb.set_trace()
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
        ends = []
        # import pdb; pdb.set_trace()
        for proc in processes:
            if not proc.next_processes_for_order(self):
                ends.append(proc)
        ordered_processes = []
        for end in ends:
            visited = []
            end.all_previous_processes_for_order(self, ordered_processes, visited, 0)
        ordered_processes.reverse()
        # todo: review bug fixes
        # this code might need more testing for orders with more than one end process
        return ordered_processes

    def unordered_processes(self):
        # this cd be cts = order.dependent_commitments.all()
        # or self.all_dependent_commitments()
        cts = Commitment.objects.filter(independent_demand=self)
        processes = set()
        for ct in cts:
            if ct.process:
                processes.add(ct.process)
        return processes

    def all_dependent_commitments(self):
        # this cd be return order.dependent_commitments.all()
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

    def first_process_in_order(self):
        # import pdb; pdb.set_trace()
        processes = list(self.unordered_processes())
        if processes:
            first = processes[0]
            for p in processes:
                if p.start_date < first.start_date:
                    first = p
            return first
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
        sale = None
        if self.order_type == "customer":
            exchange = Exchange.objects.filter(order=self).filter(use_case__identifier="sale")
            sale = exchange[0]
        return sale

    def reschedule_forward(self, delta_days, user):
        # import pdb; pdb.set_trace()
        self.due_date = self.due_date + datetime.timedelta(days=delta_days)
        self.changed_by = user
        self.save()
        ois = self.order_items()
        for oi in ois:
            if oi.due_date != self.due_date:
                oi.due_date = self.due_date
                oi.save()


class ProcessPatternManager(models.Manager):
    def production_patterns(self):
        # import pdb; pdb.set_trace()
        use_cases = PatternUseCase.objects.filter(
            Q(use_case__identifier='rand') | Q(use_case__identifier='design') | Q(use_case__identifier='recipe'))
        pattern_ids = [uc.pattern.id for uc in use_cases]
        return ProcessPattern.objects.filter(id__in=pattern_ids)

    def recipe_patterns(self):
        # import pdb; pdb.set_trace()
        use_cases = PatternUseCase.objects.filter(use_case__identifier='recipe')
        pattern_ids = [uc.pattern.id for uc in use_cases]
        return ProcessPattern.objects.filter(id__in=pattern_ids)

    def usecase_patterns(self, use_case):
        # import pdb; pdb.set_trace()
        use_cases = PatternUseCase.objects.filter(
            Q(use_case=use_case))
        pattern_ids = [uc.pattern.id for uc in use_cases]
        return ProcessPattern.objects.filter(id__in=pattern_ids)

    def all_production_resource_types(self):
        patterns = self.production_patterns()
        rt_ids = []
        for pat in patterns:
            # todo pr: shd this be own or own_or_parent_recipes?
            rt_ids.extend([rt.id for rt in pat.output_resource_types() if rt.producing_process_type_relationships()])
        return EconomicResourceType.objects.filter(id__in=rt_ids)


class ProcessPattern(models.Model):
    name = models.CharField(_('name'), max_length=32)
    objects = ProcessPatternManager()

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name

    def event_types(self):
        facets = self.facets.all()
        slots = [facet.event_type for facet in facets]
        slots = list(set(slots))
        # slots.sort(lambda x, y: cmp(x.label, y.label))
        # slots = sorted(slots, key=attrgetter('label'))
        # slots = sorted(slots, key=attrgetter('relationship'), reverse=True)
        slots = sorted(slots, key=attrgetter('name'))
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

        # import pdb; pdb.set_trace()
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

        # import pdb; pdb.set_trace()
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
        # import pdb; pdb.set_trace()
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
        # must be changed, in no longer covers
        # or event types must be changed so all ins are ins
        # return self.resource_types_for_relationship("in")
        answer = list(self.resource_types_for_relationship("in"))
        answer.extend(list(self.resource_types_for_relationship("consume")))
        answer.extend(list(self.resource_types_for_relationship("use")))
        return answer

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

    # def payment_resource_types(self):
    #    return self.resource_types_for_relationship("pay")

    # def receipt_resource_types(self):
    #    return self.resource_types_for_relationship("receive")

    # def receipt_resource_types_with_resources(self):
    #    #import pdb; pdb.set_trace()
    #    rts = [rt for rt in self.resource_types_for_relationship("receive") if rt.all_resources()] # if rt.onhand()]
    #    rt_ids = [rt.id for rt in rts]
    #    return EconomicResourceType.objects.filter(id__in=rt_ids)

    # def matl_contr_resource_types_with_resources(self):
    #    #import pdb; pdb.set_trace()
    #    rts = [rt for rt in self.resource_types_for_relationship("resource") if rt.onhand()]
    #    rt_ids = [rt.id for rt in rts]
    #    return EconomicResourceType.objects.filter(id__in=rt_ids)

    # def expense_resource_types(self):
    #    #import pdb; pdb.set_trace()
    #    return self.resource_types_for_relationship("expense")

    # def process_expense_resource_types(self):
    #    return self.resource_types_for_relationship("payexpense")

    # def cash_contr_resource_types(self): #now includes cash contributions and donations
    #    return self.resource_types_for_relationship("cash")

    # def shipment_resource_types(self):
    #    return self.resource_types_for_relationship("shipment")

    # def shipment_uninventoried_resource_types(self):
    #    rts = [rt for rt in self.resource_types_for_relationship("shipment") if rt.uninventoried()]
    #    rt_ids = [rt.id for rt in rts]
    #    return EconomicResourceType.objects.filter(id__in=rt_ids)

    # def shipment_resources(self):
    #    #import pdb; pdb.set_trace()
    #    rts = self.shipment_resource_types()
    #    resources = []
    #    for rt in rts:
    #        rt_resources = rt.all_resources()
    #        for res in rt_resources:
    #            resources.append(res)
    #    resource_ids = [res.id for res in resources]
    #    return EconomicResource.objects.filter(id__in=resource_ids).order_by("-created_date")

    # def material_contr_resource_types(self):
    #    return self.resource_types_for_relationship("resource")

    # def cash_receipt_resource_types(self):
    #    return self.resource_types_for_relationship("receivecash")

    def distribution_resource_types(self):
        return self.resource_types_for_relationship("distribute")

    def disbursement_resource_types(self):
        return self.resource_types_for_relationship("disburse")

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
        # import pdb; pdb.set_trace()
        fv_intersect = set(rt_fvs) & set(pat_fvs)
        event_type = None
        # todo bug: this method can find more than one pfv
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
                    event_type = et
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


class ProcessManager(models.Manager):
    def unfinished(self):
        return Process.objects.filter(finished=False)

    def finished(self):
        return Process.objects.filter(finished=True)

    def current(self):
        return Process.objects.filter(finished=False).filter(start_date__lte=datetime.date.today()).filter(
            end_date__gte=datetime.date.today())

    def current_or_future(self):
        return Process.objects.filter(finished=False).filter(end_date__gte=datetime.date.today())

    def current_or_future_with_use(self):
        # import pdb; pdb.set_trace()
        processes = Process.objects.current_or_future()
        ids = []
        use_et = EventType.objects.get(name="Resource use")
        for process in processes:
            if process.process_pattern:
                if use_et in process.process_pattern.event_types():
                    ids.append(process.id)
        return Process.objects.filter(pk__in=ids)


class Process(models.Model):
    name = models.CharField(_('name'), max_length=128)
    parent = models.ForeignKey('self', blank=True, null=True,
                               verbose_name=_('parent'), related_name='sub_processes', editable=False)
    process_pattern = models.ForeignKey(ProcessPattern,
                                        blank=True, null=True,
                                        verbose_name=_('process pattern'), related_name='processes')
    process_type = models.ForeignKey("ProcessType",
                                     blank=True, null=True,
                                     verbose_name=_('process type'), related_name='processes',
                                     on_delete=models.SET_NULL)
    context_agent = models.ForeignKey("EconomicAgent",
                                      blank=True, null=True,
                                      limit_choices_to={"is_context": True, },
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

    def __str__(self):
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
                {'process_id': str(self.id), })

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
        # import pdb; pdb.set_trace()
        for commit in self.commitments.all():
            if commit.context_agent != self.context_agent:
                old_agent = commit.context_agent
                commit.context_agent = self.context_agent
                if commit.from_agent == old_agent:
                    commit.from_agent = self.context_agent
                if commit.to_agent == old_agent:
                    commit.to_agent = self.context_agent
                commit.save()
        for event in self.events.all():
            if event.context_agent != self.context_agent:
                old_agent = event.context_agent
                event.context_agent = self.context_agent
                if event.from_agent == old_agent:
                    event.from_agent = self.context_agent
                if event.to_agent == old_agent:
                    event.to_agent = self.context_agent
                event.save()

    def is_deletable(self):
        if self.events.all():
            return False
        return True

    def set_started(self, date, user):
        if not self.started:
            self.started = date
            self.changed_by = user
            self.save()

    def default_agent(self):
        if self.context_agent:
            return self.context_agent.default_agent()
        return None

    def flow_type(self):
        return "Process"

    def flow_class(self):
        return "process"

    def flow_description(self):
        return self.__str__()

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
        # return " ".join([self.name, "Process"])
        return self.name

    def timeline_description(self):
        if self.notes:
            return self.notes
        elif self.process_type:
            return self.process_type.description
        else:
            return ""

    def is_orphan(self):
        # todo: if agents on graph, stop excluding work
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
        # import pdb; pdb.set_trace()
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

    def input_includes_resource(self, resource):
        inputs = self.incoming_events()
        answer = False
        for event in inputs:
            if event.resource == resource:
                answer = True
                break
        return answer

    def previous_processes(self):
        answer = []
        dmnd = None
        moc = self.main_outgoing_commitment()
        # import pdb; pdb.set_trace()
        if moc:
            dmnd = moc.order_item
        # output_rts = [oc.resource_type for oc in self.outgoing_commitments()]
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
            # todo: check stage of ie.resource != self.process_type
            if not ie.commitment:
                if ie.resource:
                    for evt in ie.resource.producing_events():
                        if evt.process:
                            if evt.process != self:
                                if evt.process not in answer:
                                    answer.append(evt.process)
        return answer

    def previous_processes_for_order(self, order):
        # this is actually previous_processes_for_order_item
        answer = []
        dmnd = None
        moc = self.main_outgoing_commitment()
        # import pdb; pdb.set_trace()
        if moc:
            dmnd = moc.order_item
        # output_rts = [oc.resource_type for oc in self.outgoing_commitments()]
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
        # import pdb; pdb.set_trace()
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
        # this is actually all_previous_processes_for_order_item
        # import pdb; pdb.set_trace()
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
        # import pdb; pdb.set_trace()
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
                                if cc.process:
                                    if cc.process not in answer:
                                        answer.append(cc.process)
                        else:
                            if not cc.order_item:
                                if cc.quantity >= oc.quantity:
                                    compare_date = self.end_date
                                    if not compare_date:
                                        compare_date = self.start_date
                                    if cc.due_date >= compare_date:
                                        if cc.process:
                                            if cc.process not in answer:
                                                answer.append(cc.process)
        for oe in self.production_events():
            if not oe.commitment:
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
        # import pdb; pdb.set_trace()
        input_ids = [ic.cycle_id() for ic in self.incoming_commitments()]
        for oc in self.outgoing_commitments():
            dmnd = oc.order_item
            stage = oc.stage
            state = oc.state
            rt = oc.resource_type
            if oc.cycle_id() not in input_ids:
                # todo: this can be slow for non-sub rts
                for cc in rt.wanting_commitments():
                    if cc.process:
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

    def finished_work_requirements(self):
        return self.commitments.filter(
            finished=True,
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

    def unplanned_work_events(self):
        return self.work_events().filter(commitment__isnull=True)

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
        if event_type.relationship == "out":
            due_date = self.end_date
        else:
            due_date = self.start_date
        ct = Commitment(
            independent_demand=demand,
            order=order,
            order_item=order_item,
            process=self,
            description=description,
            # Todo: apply selected_context_agent here? Dnly if inheritance?
            # or has that already been set on the process in explode_demands?
            context_agent=self.context_agent,
            event_type=event_type,
            resource_type=resource_type,
            stage=stage,
            state=state,
            quantity=quantity,
            unit_of_quantity=unit,
            due_date=due_date,
            from_agent=from_agent,
            to_agent=to_agent,
            created_by=user)
        ct.save()
        return ct

    def add_stream_commitments(self, last_process, user):  # for adding to the end of the order
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

    def insert_stream_commitments(self, last_process,
                                  user):  # for inserting in order (not first and not last process in order)
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

    def insert_first_stream_commitments(self, next_commitment, user):  # for inserting as first process in order
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
        # import pdb; pdb.set_trace()
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
        # import pdb; pdb.set_trace()
        # todo pr: may need get and use RecipeInheritance object
        pt = self.process_type
        output = self.main_outgoing_commitment()
        order_item = output.order_item
        # if not output:
        # import pdb; pdb.set_trace()
        visited_id = output.cycle_id()
        if visited_id not in visited:
            visited.append(visited_id)
        for ptrt in pt.all_input_resource_type_relationships():
            # import pdb; pdb.set_trace()
            if output.stage:
                # if output.resource_type == ptrt.resource_type:
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
                # todo: must consider ratio of PT output qty to PT input qty
            # pr changed
            resource_type = ptrt.resource_type
            # todo dhen: this is where species would be used
            if inheritance:
                if resource_type == inheritance.parent:
                    resource_type = inheritance.substitute(resource_type)
                else:
                    resource_class = output.resource_type.resource_class
                    candidate = resource_type.child_of_class(resource_class)
                    if candidate:
                        resource_type = candidate
            # Todo: apply selected_context_agent here? Dnly if inheritance?
            # import pdb; pdb.set_trace()
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
            # cycles broken here
            # flow todo: consider order_item for non-substitutables?
            # seemed to work without doing that...?
            # import pdb; pdb.set_trace()
            visited_id = ptrt.cycle_id()
            if visited_id not in visited:
                visited.append(visited_id)
                qty_to_explode = commitment.net()
                if qty_to_explode:
                    # todo: shd commitment.generate_producing_process?
                    # no, this an input commitment
                    # shd pt create process?
                    # shd pptr create next_commitment, and then
                    # shd next_commitment.generate_producing_process?
                    # import pdb; pdb.set_trace()
                    # pr changed
                    stage = commitment.stage
                    state = commitment.state
                    pptr, inheritance = resource_type.main_producing_process_type_relationship(stage=stage, state=state)
                    if pptr:
                        resource_type = pptr.resource_type
                        # todo dhen: this is where species would be used? Or not?
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
                            # Todo: apply selected_context_agent here? Dnly if inheritance?
                            context_agent=next_pt.context_agent,
                            url=next_pt.url,
                            end_date=self.start_date,
                            start_date=start_date,
                        )
                        next_process.save()
                        # this is the output commitment
                        # import pdb; pdb.set_trace()
                        if output.stage:
                            qty = output.quantity
                        else:
                            # todo: this makes no sense, why did I do that?
                            # temporary insanity or some reason that escapes me now?
                            # ps. prior to this commented-out code, it was
                            # qty = qty_to_explode * pptr.quantity
                            # I did this when making that salsa recipe work.
                            # 2014-11-05
                            # if not multiplier:
                            #    multiplier = pptr.quantity
                            # qty = (qty_to_explode * multiplier).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
                            qty = qty_to_explode
                        # todo: must consider ratio of PT output qty to PT input qty
                        # Todo: apply selected_context_agent here? Dnly if inheritance?
                        # import pdb; pdb.set_trace()
                        next_commitment = next_process.add_commitment(
                            resource_type=resource_type,
                            stage=pptr.stage,
                            state=pptr.state,
                            demand=demand,
                            order_item=order_item,
                            quantity=qty,
                            event_type=pptr.event_type,
                            unit=resource_type.directional_unit(pptr.event_type.relationship),
                            description=pptr.description or "",
                            user=user,
                        )
                        # todo pr: may need pass RecipeInheritance object
                        next_process.explode_demands(demand, user, visited, inheritance)

    def reschedule_forward(self, delta_days, user):
        # import pdb; pdb.set_trace()
        if not self.started:
            fps = self.previous_processes()
            if fps:
                slack = 99999
                for fp in fps:
                    slax = self.start_date - fp.end_date
                    slack = min(slack, slax.days)
                slack = max(slack, 0)
                delta_days -= slack
                delta_days = max(delta_days, 0)
                # munge for partial days
                delta_days += 1
        if delta_days:
            if self.started:
                if not self.end_date:
                    self.end_date = self.started + datetime.timedelta(minutes=self.estimated_duration)
                self.end_date = self.end_date + datetime.timedelta(days=delta_days)
            else:
                self.start_date = self.start_date + datetime.timedelta(days=delta_days)
                if self.end_date:
                    self.end_date = self.end_date + datetime.timedelta(days=delta_days)
                else:
                    self.end_date = self.start_date + datetime.timedelta(minutes=self.estimated_duration)
            self.changed_by = user
            self.save()
            self.reschedule_connections(delta_days, user)

    def reschedule_connections(self, delta_days, user):
        # import pdb; pdb.set_trace()
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
        from django_rea.valueaccounting.forms import ScheduleProcessForm
        init = {"start_date": self.start_date, "end_date": self.end_date, "notes": self.notes}
        return ScheduleProcessForm(prefix=str(self.id), initial=init)

    def plan_change_form(self):
        from django_rea.valueaccounting.forms import PlanProcessForm
        init = {"start_date": self.start_date, "end_date": self.end_date, "name": self.name}
        return PlanProcessForm(prefix=self.plan_form_prefix(), initial=init)

    def insert_process_form(self):
        # import pdb; pdb.set_trace()
        from django_rea.valueaccounting.forms import WorkflowProcessForm
        init = {"start_date": self.start_date, "end_date": self.start_date}
        return WorkflowProcessForm(prefix=str(self.id), initial=init, order_item=self.order_item())

    def roll_up_value(self, path, depth, visited):
        # process method
        # todo rollup
        # import pdb; pdb.set_trace()
        # Value_per_unit will be the result of this method.
        depth += 1
        self.depth = depth
        # self.explanation = "Value per unit consists of all the input values on the next level"
        path.append(self)
        process_value = Decimal("0.0")
        # Values of all of the inputs will be added to this list.
        values = []
        citations = []
        production_value = Decimal("0.0")

        production_qty = self.production_quantity()
        if production_qty:
            inputs = self.incoming_events()
            for ip in inputs:
                # Work contributions use resource_type.value_per_unit
                if ip.event_type.relationship == "work":
                    ip.value = ip.quantity * ip.value_per_unit()
                    ip.save()
                    process_value += ip.value
                    ip.depth = depth
                    path.append(ip)
                # Use contributions use resource value_per_unit_of_use.
                elif ip.event_type.relationship == "use":
                    if ip.resource:
                        # price changes
                        if ip.price:
                            ip.value = ip.price
                        else:
                            ip.value = ip.quantity * ip.resource.value_per_unit_of_use
                        ip.save()
                        process_value += ip.value
                        ip.resource.roll_up_value(path, depth, visited)
                        ip.depth = depth
                        path.append(ip)
                # Consume contributions use resource rolled up value_per_unit
                elif ip.event_type.relationship == "consume" or ip.event_type.name == "To Be Changed":
                    ip.depth = depth
                    path.append(ip)
                    if ip.resource:
                        value_per_unit = ip.resource.roll_up_value(path, depth, visited)
                        ip.value = ip.quantity * value_per_unit
                        ip.save()
                        process_value += ip.value
                # Citations valued later, after all other inputs added up
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
            # These citations use percentage of the sum of other input values.
            for c in citations:
                percentage = c.quantity / 100
                c.value = process_value * percentage
                c.save()
            for c in citations:
                process_value += c.value
        return process_value

    def compute_income_shares(self, value_equation, order_item, quantity, events, visited):
        # Process method
        # print "running quantity:", quantity, "running value:", value
        # import pdb; pdb.set_trace()
        if self not in visited:
            visited.add(self)
            if quantity:
                # todo: how will this work for >1 processes producing the same resource?
                # what will happen to the shares of the inputs of the later processes?
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
                    # todo br
                    # import pdb; pdb.set_trace()
                    value = pe.quantity
                    br = pe.bucket_rule(value_equation)
                    if br:
                        # import pdb; pdb.set_trace()
                        value = br.compute_claim_value(pe)
                    pe.share = value * distro_fraction
                    events.append(pe)
                if self.context_agent.compatible_value_equation(value_equation):
                    inputs = self.incoming_events()
                    for ip in inputs:
                        # we assume here that work events are contributions
                        if ip.event_type.relationship == "work":
                            if ip.is_contribution:
                                # todo br
                                # import pdb; pdb.set_trace()
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
                                new_visited = set()
                                path = []
                                depth = 0
                                # import pdb; pdb.set_trace()
                                # todo exchange redesign fallout
                                # resource_value was 0
                                resource_value = ip.resource.roll_up_value(path, depth, new_visited, value_equation)
                                ip.resource.compute_income_shares_for_use(value_equation, ip, ip_value, resource_value,
                                                                          events, visited)
                        elif ip.event_type.relationship == "consume" or ip.event_type.name == "To Be Changed":
                            # consume events are not contributions, but their resources may have contributions
                            ##todo ve test: is this a bug? how does consumption event value get set?
                            # ip_value = ip.value * distro_fraction
                            # if ip_value:
                            d_qty = ip.quantity * distro_fraction
                            # import pdb; pdb.set_trace()
                            if d_qty:
                                # print "consumption:", ip.id, ip, "ip.value:", ip.value
                                # print "----value:", ip_value, "d_qty:", d_qty, "distro_fraction:", distro_fraction
                                if ip.resource:
                                    ip.resource.compute_income_shares(value_equation, d_qty, events, visited)
                        elif ip.event_type.relationship == "cite":
                            # import pdb; pdb.set_trace()
                            # citation events are not contributions, but their resources may have contributions
                            # ip_value = ip.value * distro_fraction
                            # if ip_value:
                            #    d_qty = ip_value / value
                            #    if ip.resource:
                            #        ip.resource.compute_income_shares(value_equation, d_qty, events, visited)
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
                                ip.resource.compute_income_shares_for_use(value_equation, ip, ip_value, resource_value,
                                                                          events, visited)


@python_2_unicode_compatible
class PatternUseCase(models.Model):
    pattern = models.ForeignKey(ProcessPattern,
                                verbose_name=_('pattern'), related_name='use_cases')
    use_case = models.ForeignKey("UseCase",
                                 blank=True, null=True,
                                 verbose_name=_('use case'), related_name='patterns')

    def __str__(self):
        use_case_name = ""
        if self.use_case:
            use_case_name = self.use_case.name
        return ": ".join([self.pattern.name, use_case_name])


@python_2_unicode_compatible
class ResourceTypeFacetValue(models.Model):
    resource_type = models.ForeignKey("EconomicResourceType",
                                      verbose_name=_('resource type'), related_name='facets')
    facet_value = models.ForeignKey("FacetValue",
                                    verbose_name=_('facet value'), related_name='resource_types')

    class Meta:
        unique_together = ('resource_type', 'facet_value')
        ordering = ('resource_type', 'facet_value')

    def __str__(self):
        return ": ".join([self.resource_type.name, self.facet_value.facet.name, self.facet_value.value])


class UseCaseManager(models.Manager):
    def get_by_natural_key(self, identifier):
        # import pdb; pdb.set_trace()
        return self.get(identifier=identifier)

    def exchange_use_cases(self):
        return UseCase.objects.filter(
            Q(identifier="supply_xfer") | Q(identifier="demand_xfer") | Q(identifier="intrnl_xfer"))


@python_2_unicode_compatible
class UseCase(models.Model):
    identifier = models.CharField(_('identifier'), max_length=12)
    name = models.CharField(_('name'), max_length=128)
    restrict_to_one_pattern = models.BooleanField(_('restrict_to_one_pattern'), default=False)

    objects = UseCaseManager()

    def __str__(self):
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
                    print("Updated %s UseCase" % identifier)
        except cls.DoesNotExist:
            cls(identifier=identifier, name=name, restrict_to_one_pattern=restrict_to_one_pattern).save()
            if verbosity > 1:
                print("Created %s UseCase" % identifier)

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

    def allowed_patterns(self):  # patterns must not have event types not assigned to the use case
        # import pdb; pdb.set_trace()
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
