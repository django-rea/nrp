from __future__ import print_function
from decimal import *
import datetime

from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import python_2_unicode_compatible

from ._utils import (
    unique_slugify,
    collect_trash,
    collect_lower_trash,
)


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
        # exclude finished
        cts = self.unfinished()
        reqs = cts.filter(
            Q(event_type__relationship='consume') | Q(event_type__relationship='use')).order_by("resource_type__name")
        rts = _all_purchased_resource_types()
        answer = []
        for req in reqs:
            qtb = req.quantity_to_buy()
            if qtb > 0:
                if req.resource_type in rts:
                    req.purchase_quantity = qtb
                    answer.append(req)
        return answer


@python_2_unicode_compatible
class Commitment(models.Model):
    order = models.ForeignKey("Order",
                              blank=True, null=True,
                              related_name="commitments", verbose_name=_('order'))
    independent_demand = models.ForeignKey("Order",
                                           blank=True, null=True,
                                           related_name="dependent_commitments", verbose_name=_('independent demand'))
    order_item = models.ForeignKey("self",
                                   blank=True, null=True,
                                   related_name="stream_commitments", verbose_name=_('order item'))
    event_type = models.ForeignKey("EventType",
                                   related_name="commitments", verbose_name=_('event type'))
    stage = models.ForeignKey("ProcessType", related_name="commitments_at_stage",
                              verbose_name=_('stage'), blank=True, null=True)
    exchange_stage = models.ForeignKey("ExchangeType", related_name="commitments_at_exchange_stage",
                                       verbose_name=_('exchange stage'), blank=True, null=True)
    state = models.ForeignKey("ResourceState", related_name="commitments_at_state",
                              verbose_name=_('state'), blank=True, null=True)
    commitment_date = models.DateField(_('commitment date'), default=datetime.date.today)
    start_date = models.DateField(_('start date'), blank=True, null=True)
    due_date = models.DateField(_('due date'))
    finished = models.BooleanField(_('finished'), default=False)
    from_agent_type = models.ForeignKey("AgentType",
                                        blank=True, null=True,
                                        related_name="given_commitments", verbose_name=_('from agent type'))
    from_agent = models.ForeignKey("EconomicAgent",
                                   blank=True, null=True,
                                   related_name="given_commitments", verbose_name=_('from'))
    to_agent = models.ForeignKey("EconomicAgent",
                                 blank=True, null=True,
                                 related_name="taken_commitments", verbose_name=_('to'))
    resource_type = models.ForeignKey("EconomicResourceType",
                                      blank=True, null=True,
                                      verbose_name=_('resource type'), related_name='commitments')
    resource = models.ForeignKey("EconomicResource",
                                 blank=True, null=True,
                                 verbose_name=_('resource'), related_name='commitments')
    process = models.ForeignKey("Process",
                                blank=True, null=True,
                                verbose_name=_('process'), related_name='commitments')
    exchange = models.ForeignKey("Exchange",
                                 blank=True, null=True,
                                 verbose_name=_('exchange'), related_name='commitments')
    transfer = models.ForeignKey("Transfer",
                                 blank=True, null=True,
                                 related_name="commitments")
    context_agent = models.ForeignKey("EconomicAgent",
                                      blank=True, null=True,
                                      limit_choices_to={"is_context": True, },
                                      verbose_name=_('context agent'), related_name='commitments')
    description = models.TextField(_('description'), null=True, blank=True)
    url = models.CharField(_('url'), max_length=255, blank=True)
    quantity = models.DecimalField(_('quantity'), max_digits=8, decimal_places=2)
    unit_of_quantity = models.ForeignKey("Unit", blank=True, null=True,
                                         verbose_name=_('unit'), related_name="commitment_qty_units")
    quality = models.DecimalField(_('quality'), max_digits=3, decimal_places=0, default=Decimal("0"))
    value = models.DecimalField(_('value'), max_digits=8, decimal_places=2,
                                default=Decimal("0.0"))
    unit_of_value = models.ForeignKey("Unit", blank=True, null=True,
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

    def __str__(self):
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
        # notify_here?
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
                return types_models.CommitmentType.objects.get(
                    resource_type=rt, process_type=pt)
            except types_models.CommitmentType.DoesNotExist:
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

    def invite_form_prefix(self):
        return "-".join(["invite", str(self.id)])

    def commitment_form(self):
        from django_rea.valueaccounting.forms import CommitmentForm
        prefix = self.form_prefix()
        return CommitmentForm(instance=self, prefix=prefix)

    def join_form_prefix(self):
        return "-".join(["JOIN", str(self.id)])

    def join_form(self):
        from django_rea.valueaccounting.forms import CommitmentForm
        prefix = self.join_form_prefix()
        init = {
            "start_date": datetime.date.today,
            "unit_of_quantity": self.unit_of_quantity,
            "description": "Explain how you propose to help.",
        }
        return CommitmentForm(initial=init, prefix=prefix)

    def change_form(self):
        from django_rea.valueaccounting.forms import ChangeCommitmentForm
        prefix = self.form_prefix()
        return ChangeCommitmentForm(instance=self, prefix=prefix)

    def process_form(self):
        from django_rea.valueaccounting.forms import ProcessForm
        start_date = self.start_date
        if not start_date:
            start_date = self.due_date
        name = " ".join(["Produce", self.resource_type.name])
        init = {
            "name": name,
            "context_agent": self.context_agent,
            "start_date": start_date,
            "end_date": self.due_date,
        }
        prefix = self.form_prefix()
        return ProcessForm(initial=init, prefix=prefix)

    def change_work_form(self):
        from django_rea.valueaccounting.forms import WorkCommitmentForm
        prefix = self.form_prefix()
        pattern = None
        if self.process:
            pattern = self.process.process_pattern
        return WorkCommitmentForm(instance=self, pattern=pattern, prefix=prefix)

    def invite_collaborator_form(self):
        from django_rea.valueaccounting.forms import InviteCollaboratorForm
        prefix = self.invite_form_prefix()
        unit = self.resource_type.unit
        qty_help = ""
        if unit:
            rt_name = self.resource_type.name
            unit_string = unit.abbrev
            qty_help = " ".join(["Type of work:", rt_name, ", unit:", unit.abbrev, ", up to 2 decimal places"])
        form = InviteCollaboratorForm(
            qty_help=qty_help,
            prefix=prefix)

        # import pdb; pdb.set_trace()
        return form

    def can_add_to_resource(self):
        # todo: figure out how to allow for workflow stream resources
        # easy way: edit previous change event
        # hard way: a new change event (or is that really a change event?)
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
        # import pdb; pdb.set_trace()
        if self.resource_type.inventory_rule == "yes":
            from django_rea.valueaccounting.forms import CreateEconomicResourceForm
            init = {
                "from_agent": self.from_agent,
                "quantity": self.quantity,
                "unit_of_quantity": self.resource_type.unit,
            }
            return CreateEconomicResourceForm(prefix=self.form_prefix(), initial=init, data=data)
        else:
            from django_rea.valueaccounting.forms import UninventoriedProductionEventForm
            init = {
                "from_agent": self.from_agent,
                "quantity": self.quantity,
            }
            unit = self.resource_type.unit
            qty_help = ""
            if unit:
                unit_string = unit.abbrev
                qty_help = " ".join(["unit:", unit.abbrev, ", up to 2 decimal places"])
            return UninventoriedProductionEventForm(qty_help=qty_help, prefix=self.form_prefix(), initial=init,
                                                    data=data)

    def resource_transform_form(self, data=None):
        # import pdb; pdb.set_trace()
        from django_rea.valueaccounting.forms import TransformEconomicResourceForm
        quantity = self.quantity
        resources = self.resources_ready_to_be_changed()
        if resources:
            quantity = resources[0].quantity
        init = {
            "from_agent": self.from_agent,
            "event_date": datetime.date.today(),
            "quantity": quantity,
        }
        unit = self.resource_type.unit
        qty_help = ""
        if unit:
            unit_string = unit.abbrev
            qty_help = " ".join(["unit:", unit.abbrev, ", up to 2 decimal places"])
        return TransformEconomicResourceForm(qty_help=qty_help, prefix=self.form_prefix(), initial=init, data=data)

    def select_resource_form(self, data=None):
        from django_rea.valueaccounting.forms import SelectResourceForm
        init = {
            "quantity": self.quantity,
            # "unit_of_quantity": self.resource_type.unit,
        }
        return SelectResourceForm(prefix=self.form_prefix(), resource_type=self.resource_type, initial=init, data=data)

    def resource_change_form(self):
        resource = self.output_resource()
        if resource:
            return resource.change_form(self.form_prefix())
        else:
            return self.resource_type.resource_create_form(self.form_prefix())

    def todo_change_form(self):
        # import pdb; pdb.set_trace()
        from django_rea.valueaccounting.forms import TodoForm
        prefix = self.form_prefix()
        return TodoForm(instance=self, prefix=prefix)

    def work_todo_change_form(self):
        # import pdb; pdb.set_trace()
        from ocp.work.forms import WorkTodoForm
        agent = self.to_agent  # poster of todo
        prefix = self.form_prefix()
        patterns = PatternUseCase.objects.filter(use_case__identifier='todo')
        if patterns:
            pattern = patterns[0].pattern
            todo_form = WorkTodoForm(agent=agent, pattern=pattern, instance=self, prefix=prefix)
        else:
            todo_form = WorkTodoForm(agent=agent, instance=self, prefix=prefix)
        return todo_form

    # obsolete?
    """
    def work_event_form(self, data=None):
        from django_rea.valueaccounting.forms import TimeEventForm, InputEventForm
        prefix=self.form_prefix()
        unit = self.resource_type.unit
        if unit.unit_type == "time":
            return TimeEventForm(prefix=prefix, data=data)
        else:
            qty_help = " ".join(["unit:", unit.abbrev, ", up to 2 decimal places"])
            return InputDistributionEventForm(qty_help=qty_help, prefix=prefix, data=data)
    """

    def input_event_form(self, data=None):
        from django_rea.valueaccounting.forms import InputEventForm
        prefix = self.form_prefix()
        qty_help = " ".join(["unit:", self.unit_of_quantity.abbrev, ", up to 2 decimal places"])
        return InputEventForm(qty_help=qty_help, prefix=prefix, data=data)

    def input_event_form_init(self, init=None, data=None):
        # import pdb; pdb.set_trace()
        from django_rea.valueaccounting.forms import InputEventAgentForm
        prefix = self.form_prefix()
        qty_help = ""
        unit = self.resource_type.unit
        if unit:
            if unit.abbrev:
                unit_string = unit.abbrev
            else:
                unit_string = unit.name
            qty_help = " ".join(["unit:", unit_string, ", up to 2 decimal places"])
        if init:
            return InputEventAgentForm(qty_help=qty_help, prefix=prefix, initial=init, data=data)
        else:
            return InputEventAgentForm(qty_help=qty_help, prefix=prefix, data=data)

    def consumption_event_form(self):
        from django_rea.valueaccounting.forms import InputEventForm
        prefix = self.form_prefix()
        qty_help = " ".join(["unit:", self.unit_of_quantity.abbrev, ", up to 2 decimal places"])
        return InputEventForm(qty_help=qty_help, prefix=prefix)

    # obsolete
    def old_use_event_form(self):
        from django_rea.valueaccounting.forms import TimeEventForm, InputEventForm
        prefix = self.form_prefix()
        unit = self.resource_type.directional_unit("use")
        if unit.unit_type == "time":
            return TimeEventForm(prefix=prefix)
        else:
            qty_help = " ".join(["unit:", unit.abbrev, ", up to 2 decimal places"])
            return InputEventForm(qty_help=qty_help, prefix=prefix)

    def use_event_form(self, data=None):
        from django_rea.valueaccounting.forms import InputEventForm
        prefix = self.form_prefix()
        unit = self.resource_type.directional_unit("use")
        qty_help = " ".join(["unit:", unit.abbrev, ", up to 2 decimal places"])
        return InputEventForm(qty_help=qty_help, prefix=prefix, data=data)

    def resources_ready_to_be_changed(self):
        # import pdb; pdb.set_trace()
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

    def fulfilling_events_condensed(self):
        # import pdb; pdb.set_trace()
        event_list = self.fulfillment_events.all()
        condensed_events = []
        if event_list:
            summaries = {}
            for event in event_list:
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
            condensed_events = summaries.values()
        return condensed_events

    # obsolete
    def fulfilling_shipment_events(self):
        return self.fulfillment_events.filter(event_type__name="Shipment")

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
        # import pdb; pdb.set_trace()
        if self.fulfillment_events.filter(from_agent=agent):
            return True
        else:
            return False

    def fulfilled_quantity(self):
        return sum(evt.quantity for evt in self.fulfilling_events())

    def unfilled_quantity(self):
        return self.quantity - self.fulfilled_quantity()

    def remaining_formatted_quantity(self):
        qty = self.unfilled_quantity()
        unit = self.unit_of_quantity
        if unit:
            if unit.symbol:
                answer = "".join([unit.symbol, str(qty)])
            else:
                answer = " ".join([str(qty), unit.abbrev])
        else:
            answer = str(qty)
        return answer

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
        # import pdb; pdb.set_trace()
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
        # import pdb; pdb.set_trace()
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

    def net_for_order(self):
        # this method does netting after an order has been scheduled
        # see tiddler Bug 2105-01-25
        # import pdb; pdb.set_trace()
        rt = self.resource_type
        stage = self.stage
        due_date = self.due_date
        if not rt.substitutable:
            if stage:
                onhand = rt.onhand_for_stage(stage)
            else:
                onhand = rt.onhand()
            oh_qty = sum(oh.quantity for oh in onhand if oh.order_item == self.order_item)
        else:
            oh_qty = rt.onhand_qty_for_commitment(self)
        if oh_qty >= self.quantity:
            return 0
        sked_rcts = rt.producing_commitments().filter(due_date__lte=self.due_date)
        if stage:
            sked_rcts = sked_rcts.filter(stage=stage)
            priors = rt.consuming_commitments_for_stage(stage).filter(due_date__lt=due_date)
        else:
            priors = rt.consuming_commitments().filter(due_date__lt=due_date)
        if not rt.substitutable:
            sked_qty = sum(sr.quantity for sr in sked_rcts if sr.order_item == self.order_item)
        else:
            sked_qty = sum(sr.quantity for sr in sked_rcts)
        sked_qty = sked_qty - sum(p.quantity for p in priors)
        avail = oh_qty + sked_qty
        remainder = self.quantity - avail
        if remainder < 0:
            remainder = Decimal("0")
        if self.event_type.resource_effect == "-":
            return remainder
        else:
            if not remainder:
                return Decimal("0")
            elif self.event_type.resource_effect == "=":
                return Decimal("1")
            else:
                return remainder

    def needs_production_process(self):
        # I know > 0 is unnecessary, just being explicit
        if self.net_for_order() > 0:
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

    def output_resources(self):
        answer = None
        if self.event_type.relationship == "out":
            answer = [event.resource for event in self.fulfilling_events()]
        return answer

    def output_resource(self):
        # todo: this is a hack, cd be several resources
        answer = None
        if self.event_type.relationship == "out":
            events = self.fulfilling_events()
            if events:
                event = events[0]
                answer = event.resource
        return answer

    def is_shipment(self):
        if self.order:
            if self.order.order_type == "customer":
                exchange = self.order.exchange()
                if exchange:
                    if exchange.use_case.identifier == "demand_xfer":
                        if self.event_type.name == "Give":
                            return True
        return False

    def generate_producing_process(self, user, visited, inheritance=None, explode=False):

        """ This method is usually used in recipe explosions.

            inheritance is optional, can be positional or keyword arg. It means
            the recipe in use was inherited from a parent.
            explode is also optional. If used by a caller, and inheritance is not used,
            explode must be a keyword arg.
        """
        # import pdb; pdb.set_trace()
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
        process = None
        if qty_required:
            # pr changed
            # import pdb; pdb.set_trace()
            ptrt, inheritance = rt.main_producing_process_type_relationship(stage=self.stage, state=self.state)
            if ptrt:
                resource_type = self.resource_type
                if self.is_shipment():
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
                    # Todo: apply selected_context_agent here?
                    # only if inheritance?
                    context_agent=pt.context_agent,
                    url=pt.url,
                    end_date=self.due_date,
                    start_date=start_date,
                    created_by=user,
                )
                process.save()
                producing_commitment.process = process
                producing_commitment.context_agent = process.context_agent
                producing_commitment.to_agent = self.context_agent
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

    def possible_work_users(self):
        srcs = self.resource_type.work_agents()
        members = self.context_agent.all_members_list()
        agents = [agent for agent in srcs if agent in members]
        users = [a.user() for a in agents if a.user()]
        return [u.user for u in users]

    def workers(self):
        answer = []
        if self.event_type.relationship == "work":
            answer = [evt.from_agent for evt in self.fulfilling_events() if evt.from_agent]
            if self.from_agent:
                answer.append(self.from_agent)
        return list(set(answer))

    def reschedule_forward(self, delta_days, user):
        # import pdb; pdb.set_trace()
        self.due_date = self.due_date + datetime.timedelta(days=delta_days)
        self.changed_by = user
        self.save()
        order = self.order
        if order:
            order.reschedule_forward(delta_days, user)
        # find related shipment commitments
        else:
            demand = self.independent_demand
            oi = self.order_item
            if oi != self:
                if oi.resource_type == self.resource_type:
                    if oi.stage == self.stage:
                        oi.order.reschedule_forward(delta_days, user)

    def reschedule_forward_from_source(self, lead_time, user):
        lag = datetime.date.today() - self.due_date
        delta_days = lead_time + lag.days + 1
        # todo: next line may need to be removed
        # if process.reschedule_connections is revived
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
        # todo: this shd just be a filter, but need to test the change, so do later
        return [ct for ct in producers if ct.order_item == self.order_item]

    def active_producing_commitments(self):
        if self.stage:
            return self.resource_type.active_producing_commitments().filter(
                stage=self.stage)
        else:
            return self.resource_type.active_producing_commitments()

    def scheduled_receipts(self):
        # import pdb; pdb.set_trace()
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
        # import pdb; pdb.set_trace()
        processes = []
        self.process.all_previous_processes(processes, [], 0)
        return processes

    def find_order_item(self):
        # this is a temporary method for data migration after the flows branch is deployed
        answer = None
        if self.independent_demand:
            ois = self.independent_demand.order_items()
            if ois:
                if ois.count() == 1:
                    return ois[0]
                else:
                    return ois

    def unique_processes_for_order_item(self, visited):
        unique_processes = []
        all_processes = self.all_processes_in_my_order_item()
        for process in all_processes:
            if process not in visited:
                visited.add(process)
                unique_processes.append(process)
        return unique_processes

    def all_processes_in_my_order_item(self):
        ordered_processes = []
        order_item = self.order_item
        if order_item:
            order = self.independent_demand
            if order:
                processes = order.all_processes()
                for p in processes:
                    if p.order_item() == order_item:
                        ordered_processes.append(p)
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
        # import pdb; pdb.set_trace()
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
        # import pdb; pdb.set_trace()
        if self.is_workflow_order_item():
            processes = self.process_chain()
            for process in processes:
                # process.context_agent = project
                # process.save()
                process.change_context_agent(context_agent=project)
        return self

    def adjust_workflow_commitments_process_added(self, process, user):  # process added to the end of the order item
        # import pdb; pdb.set_trace()
        last_process = self.last_process_in_my_order_item()
        process.add_stream_commitments(last_process=last_process, user=user)
        last_commitment = last_process.main_outgoing_commitment()
        last_commitment.remove_order()
        return self

    def adjust_workflow_commitments_process_inserted(self, process, next_process, user):
        # import pdb; pdb.set_trace()
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
        # import pdb; pdb.set_trace()
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
                last_commitment.order_item = last_commitment
                last_commitment.save()
                # change the order item in dependent commitments
                # before deleting the last process
                if self.order_item == self:
                    dependent_commitments = Commitment.objects.filter(order_item=self)
                    for dc in dependent_commitments:
                        dc.order_item = last_commitment
                        dc.save()
        else:
            next_process = all_procs[process_index + 1]
            next_commitment = next_process.to_be_changed_requirements()[0]
        if last_process and next_commitment:
            next_commitment.update_stage(last_process.process_type)
        return None

    def compute_income_fractions(self, value_equation):
        """Returns a list of contribution events for an order_item,

        where each event has event.share and event.fraction.
        event.share is that event's share based on its
        proportional contribution to the order_item's resource value.
        event.fraction is that event's fraction of the total shares.

        Commitment (order_item) method.

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
                # does not handle different resources per order_item yet.
                msg = " ".join([self.__str__(), "has different resources, not handled yet."])
                assert False, msg
        if resource:
            shares = self.compute_income_fractions_for_resource(value_equation, resource)
        else:
            shares = self.compute_income_fractions_for_process(value_equation)
        if shares:
            total = sum(s.share for s in shares)
        if total:
            for s in shares:
                s.fraction = s.share / total
        # import pdb; pdb.set_trace()
        # print "total shares:", total
        return shares

    def compute_income_fractions_for_resource(self, value_equation, resource):
        # print "*** rollup up resource value"
        visited = set()
        path = []
        depth = 0
        # value_per_unit = resource.roll_up_value(path, depth, visited, value_equation)
        # print "resource value_per_unit:", value_per_unit
        # value = self.quantity * value_per_unit
        visited = set()
        # print "*** computing income shares"
        shares = []
        # import pdb; pdb.set_trace()
        resource.compute_income_shares(value_equation, self.quantity, shares, visited)
        return shares

    def compute_income_fractions_for_process(self, value_equation):
        # Commitment (order_item) method
        shares = []
        visited = set()
        path = []
        depth = 0
        # todo: handle shipment commitments with no process
        p = self.process
        if p:
            # print "*** rollup up process value"
            # value = p.roll_up_value(path, depth, visited, value_equation)
            # print "processvalue:", value
            visited = set()
            # print "*** computing income shares"
            # import pdb; pdb.set_trace()
            p.compute_income_shares(value_equation, self, self.quantity, shares, visited)
        else:
            production_commitments = self.get_production_commitments_for_shipment()
            if production_commitments:
                # todo: later, work out how to handle multiple production commitments
                pc = production_commitments[0]
                p = pc.process
                if p:
                    visited = set()
                    p.compute_income_shares(value_equation, self, self.quantity, shares, visited)

        return shares

    def get_production_commitments_for_shipment(self):
        production_commitments = []
        if self.event_type.name == "Shipment":
            production_commitments = Commitment.objects.filter(
                order_item=self,
                event_type__relationship="out",
                resource_type=self.resource_type)
        return production_commitments


# todo: not used.
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
    initiating_commitment = models.ForeignKey("Commitment",
                                              related_name="initiated_commitments",
                                              verbose_name=_('initiating commitment'))
    reciprocal_commitment = models.ForeignKey("Commitment",
                                              related_name="reciprocal_commitments",
                                              verbose_name=_('reciprocal commitment'))
    reciprocity_date = models.DateField(_('reciprocity date'), default=datetime.date.today)

    class Meta:
        ordering = ('reciprocity_date',)

    def __str__(self):
        return ' '.join([
            'inititating commmitment:',
            self.initiating_commmitment.__str__(),
            'reciprocal commmitment:',
            self.reciprocal_commitment.__str__(),
            self.reciprocity_date.strftime('%Y-%m-%d'),
        ])

    def clean(self):
        # import pdb; pdb.set_trace()
        if self.initiating_commitment.from_agent.id != self.reciprocal_commitment.to_agent.id:
            raise ValidationError('Initiating commitment from_agent must be the reciprocal commitment to_agent.')
        if self.initiating_commitment.to_agent.id != self.reciprocal_commitment.from_agent.id:
            raise ValidationError('Initiating commitment to_agent must be the reciprocal commitment from_agent.')


def _all_purchased_resource_types():
    uc = UseCase.objects.get(name="Purchasing")
    pats = ProcessPattern.objects.usecase_patterns(uc)
    # todo exchange redesign fallout
    # et = EventType.objects.get(name="Receipt")
    et = types_models.EventType.objects.get(name="Receive")
    rts = []
    for pat in pats:
        rts.extend(pat.get_resource_types(et))
    return rts
