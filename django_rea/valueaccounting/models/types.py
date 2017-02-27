from __future__ import print_function
from decimal import *
import datetime

from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import python_2_unicode_compatible

from easy_thumbnails.fields import ThumbnailerImageField

from ._utils import unique_slugify

from .core import EconomicResource

SIZE_CHOICES = (
    ('individual', _('individual')),
    ('org', _('organization')),
    ('network', _('network')),
    ('team', _('project')),
    ('community', _('community')),
)


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


@python_2_unicode_compatible
class CommitmentType(models.Model):
    process_type = models.ForeignKey("ProcessType",
                                     verbose_name=_('process type'), related_name='resource_types')
    resource_type = models.ForeignKey("EconomicResourceType",
                                      verbose_name=_('resource type'), related_name='process_types')
    event_type = models.ForeignKey("EventType",
                                   verbose_name=_('event type'), related_name='process_resource_types')
    stage = models.ForeignKey("ProcessType", related_name="commitmenttypes_at_stage",
                              verbose_name=_('stage'), blank=True, null=True)
    state = models.ForeignKey("ResourceState", related_name="commitmenttypes_at_state",
                              verbose_name=_('state'), blank=True, null=True)
    quantity = models.DecimalField(_('quantity'), max_digits=8, decimal_places=2, default=Decimal('0.00'))
    unit_of_quantity = models.ForeignKey("Unit", blank=True, null=True,
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

    def __str__(self):
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
        # import pdb; pdb.set_trace()
        if self.event_type.is_change_related():
            if self not in chain:
                chain.append(self)
                if self.event_type.relationship == "out":
                    next_in_chain = CommitmentType.objects.filter(
                        resource_type=self.resource_type,
                        stage=self.stage,
                        event_type__resource_effect=">~")
                if self.event_type.relationship == "in":
                    next_in_chain = CommitmentType.objects.filter(
                        resource_type=self.resource_type,
                        stage=self.process_type,
                        event_type__resource_effect="~>")
                if next_in_chain:
                    next_in_chain[0].follow_stage_chain(chain)

    def follow_stage_chain_beyond_workflow(self, chain):
        # import pdb; pdb.set_trace()
        chain.append(self)
        if self.event_type.is_change_related():
            if self.event_type.relationship == "out":
                next_in_chain = self.resource_type.wanting_process_type_relationships_for_stage(self.stage)
            if self.event_type.relationship == "in":
                next_in_chain = CommitmentType.objects.filter(
                    resource_type=self.resource_type,
                    stage=self.process_type,
                    event_type__resource_effect="~>")
            if next_in_chain:
                next_in_chain[0].follow_stage_chain_beyond_workflow(chain)

    def create_commitment_for_process(self, process, user, inheritance):
        # pr changed
        if self.event_type.relationship == "out":
            due_date = process.end_date
        else:
            due_date = process.start_date
        resource_type = self.resource_type
        # todo dhen: this is where species would be used
        if inheritance:
            if resource_type == inheritance.parent:
                resource_type = inheritance.substitute(resource_type)
        unit = self.resource_type.directional_unit(self.event_type.relationship)
        # import pdb; pdb.set_trace()
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
            # from_agent=from_agent,
            # to_agent=to_agent,
            created_by=user)
        commitment.save()
        return commitment

    def create_commitment(self, due_date, user):
        unit = self.resource_type.directional_unit(self.event_type.relationship)
        # import pdb; pdb.set_trace()
        commitment = Commitment(
            stage=self.stage,
            state=self.state,
            description=self.description,
            context_agent=self.process_type.context_agent,
            event_type=self.event_type,
            resource_type=self.resource_type,
            quantity=self.quantity,
            # todo exchange redesign fallout
            unit_of_quantity=unit,
            due_date=due_date,
            # from_agent=from_agent,
            # to_agent=to_agent,
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
            # return self.inverse_label()
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
            # if self.resource_type.category.name == 'option':
            #    return self
            # else:
            #    return self.resource_type
        else:
            return self.process_type

    def xbill_parents(self):
        return [self.resource_type, self]

    def node_id(self):
        # todo: where is this used? Did I break it with this change?
        # (adding stage and state)
        answer = "-".join(["ProcessResource", str(self.id)])
        if self.stage:
            answer = "-".join([answer, str(self.stage.id)])
        if self.state:
            answer = "-".join([answer, self.state.name])
        return answer

    def xbill_change_prefix(self):
        return "".join(["PTRT", str(self.id)])

    def xbill_change_form(self):
        from django_rea.valueaccounting.forms import ProcessTypeInputForm, ProcessTypeCitableForm, ProcessTypeWorkForm
        if self.event_type.relationship == "work":
            return ProcessTypeWorkForm(instance=self, process_type=self.process_type, prefix=self.xbill_change_prefix())
        elif self.event_type.relationship == "cite":
            return ProcessTypeCitableForm(instance=self, process_type=self.process_type,
                                          prefix=self.xbill_change_prefix())
        else:
            return ProcessTypeInputForm(instance=self, process_type=self.process_type,
                                        prefix=self.xbill_change_prefix())


INVENTORY_RULE_CHOICES = (
    ('yes', _('Keep inventory')),
    ('no', _('Not worth it')),
    ('never', _('Does not apply')),
)

BEHAVIOR_CHOICES = (
    ('work', _('Type of Work')),
    ('account', _('Virtual Account')),
    ('dig_curr', _('Digital Currency')),
    ('dig_acct', _('Digital Currency Address')),
    ('dig_wallet', _('Digital Currency Wallet')),
    ('other', _('Other')),
)


class EconomicResourceTypeManager(models.Manager):
    def membership_share(self):
        try:
            share = EconomicResourceType.objects.get(name="Membership Share")
        except EconomicResourceType.DoesNotExist:
            raise ValidationError("Membership Share does not exist by that name")
        return share

class RecipeInheritance(object):
    def __init__(self, parent, heir):
        self.parent = parent
        self.heir = heir

    def substitute(self, candidate):
        if candidate == self.parent:
            return self.heir
        else:
            return candidate


@python_2_unicode_compatible
class EconomicResourceType(models.Model):
    name = models.CharField(_('name'), max_length=128, unique=True)
    # version = models.CharField(_('version'), max_length=32, blank=True)
    parent = models.ForeignKey('self', blank=True, null=True,
                               verbose_name=_('parent'), related_name='children')
    resource_class = models.ForeignKey("ResourceClass", blank=True, null=True,
                                       verbose_name=_('resource class'), related_name='resource_types')
    unit = models.ForeignKey("Unit", blank=True, null=True,
                             verbose_name=_('unit'), related_name="resource_units",
                             help_text=_(
                                 'if this resource has different units of use and inventory, this is the unit of inventory'))
    unit_of_use = models.ForeignKey("Unit", blank=True, null=True,
                                    verbose_name=_('unit of use'), related_name="units_of_use",
                                    help_text=_(
                                        'if this resource has different units of use and inventory, this is the unit of use'))
    unit_of_value = models.ForeignKey("Unit", blank=True, null=True,
                                      limit_choices_to={'unit_type': 'value'},
                                      verbose_name=_('unit of value'), related_name="resource_type_value_units",
                                      editable=False)
    value_per_unit = models.DecimalField(_('value per unit'), max_digits=8, decimal_places=2,
                                         default=Decimal("0.00"), editable=False)
    value_per_unit_of_use = models.DecimalField(_('value per unit of use'), max_digits=8, decimal_places=2,
                                                default=Decimal("0.00"), editable=False)
    price_per_unit = models.DecimalField(_('price per unit'), max_digits=8, decimal_places=2,
                                         default=Decimal("0.00"))
    unit_of_price = models.ForeignKey("Unit", blank=True, null=True,
                                      limit_choices_to={'unit_type': 'value'},
                                      verbose_name=_('unit of price'), related_name="resource_type_price_units")
    substitutable = models.BooleanField(_('substitutable'), default=True,
                                        help_text=_(
                                            'Can any resource of this type be substituted for any other resource of this type?'))
    inventory_rule = models.CharField(_('inventory rule'), max_length=5,
                                      choices=INVENTORY_RULE_CHOICES, default='yes')
    behavior = models.CharField(_('behavior'), max_length=12,
                                choices=BEHAVIOR_CHOICES, default='other')
    photo = ThumbnailerImageField(_("photo"),
                                  upload_to='photos', blank=True, null=True)
    photo_url = models.CharField(_('photo url'), max_length=255, blank=True)
    url = models.CharField(_('url'), max_length=255, blank=True)
    description = models.TextField(_('description'), blank=True, null=True)
    accounting_reference = models.ForeignKey("AccountingReference", blank=True, null=True,
                                             verbose_name=_('accounting reference'), related_name="resource_types",
                                             help_text=_('optional reference to an external account'))
    created_by = models.ForeignKey(User, verbose_name=_('created by'),
                                   related_name='resource_types_created', blank=True, null=True, editable=False)
    changed_by = models.ForeignKey(User, verbose_name=_('changed by'),
                                   related_name='resource_types_changed', blank=True, null=True, editable=False)
    created_date = models.DateField(auto_now_add=True, blank=True, null=True, editable=False)
    changed_date = models.DateField(auto_now=True, blank=True, null=True, editable=False)
    slug = models.SlugField(_("Page name"), editable=False)

    objects = EconomicResourceTypeManager()

    class Meta:
        ordering = ('name',)
        verbose_name = _('resource type')

    def __str__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('resource_type', (),
                {'resource_type_id': str(self.id), })

    def label(self):
        return self.__str__()

    def save(self, *args, **kwargs):
        # unique_slugify(self, self.name)
        super(EconomicResourceType, self).save(*args, **kwargs)

    def is_virtual_account(self):
        if self.behavior == "account":
            return True
        else:
            return False

    def is_work(self):
        # import pdb; pdb.set_trace()
        if self.behavior == "work":
            return True
        else:
            return False

    def direct_children(self):
        return self.children.all()

    def with_all_children(self):
        answer = [self, ]
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

    def onhand_for_exchange_stage(self, stage):
        return EconomicResource.goods.filter(
            resource_type=self,
            exchange_stage=stage,
            quantity__gt=0)

    def commits_for_exchange_stage(self, stage):
        cfes = []
        commits = Commitment.objects.filter(
            exchange_stage=stage,
            resource_type=self,
            finished=False)
        for com in commits:
            if com.unfilled_quantity > 0:
                cfes.append(com)
        return cfes

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
        # pr changed
        # does not need order_item because net already skipped non-subs
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
        # pr changed
        # does not need order_item because net already skipped non-subs
        # import pdb; pdb.set_trace()
        due_date = commitment.due_date
        stage = commitment.stage
        sked_rcts = self.active_producing_commitments().filter(due_date__lte=due_date).exclude(id=commitment.id)
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
        # todo pr: this shd be replaced by own_recipes
        return self.process_types.filter(event_type__relationship='out')

    def manufacturing_producing_process_type_relationships(self):
        return self.process_types.filter(
            stage__isnull=True,
            event_type__relationship='out')

    def own_recipes(self):
        # todo pr: or shd that be own_producing_commitment_types?
        return self.process_types.filter(event_type__relationship='out')

    def own_or_parent_recipes(self):
        ptrs = self.own_recipes()
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
        # import pdb; pdb.set_trace()
        # pr changed
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
        # todo pr: shd this use own_or_parent_recipes?
        # staged_commitments = self.process_types.filter(stage__isnull=False)
        # pr changed
        ptrts, inheritance = self.own_or_parent_recipes()
        stages = [ct for ct in ptrts if ct.stage]
        if stages:
            return True
        else:
            return False

    def producing_process_types(self):
        # todo pr: shd this be own or own_or_parent_recipes?
        return [pt.process_type for pt in self.producing_process_type_relationships()]

    def main_producing_process_type(self, stage=None, state=None):
        # todo pr: shd this return inheritance, too?
        ptrt, inheritance = self.main_producing_process_type_relationship(stage, state)
        if ptrt:
            return ptrt.process_type
        else:
            return None

    def all_staged_commitment_types(self):
        # todo pr: shd this be own or own_or_parent_recipes?
        return self.process_types.filter(stage__isnull=False)

    def all_staged_process_types(self):
        cts = self.all_staged_commitment_types()
        pts = [ct.process_type for ct in cts]
        return list(set(pts))

    def all_stages(self):
        ids = [pt.id for pt in self.all_staged_process_types()]
        return ProcessType.objects.filter(id__in=ids)

    def staged_commitment_type_sequence(self):
        # ximport pdb; pdb.set_trace()
        # pr changed
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
                # bug: this code failed when it got more than one result
                # see https://github.com/valnet/valuenetwork/issues/403
                creation = self.process_types.get(
                    stage__isnull=False,
                    event_type=creation_et)
        except CommitmentType.DoesNotExist:
            try:
                if parent:
                    creation = parent.process_types.get(
                        stage__isnull=True)
                else:
                    creation = self.process_types.get(
                        stage__isnull=True)
            except CommitmentType.DoesNotExist:
                pass
        if creation:
            creation.follow_stage_chain(chain)
        return chain, inheritance

    def staged_commitment_type_sequence_beyond_workflow(self):
        # import pdb; pdb.set_trace()
        # pr changed
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
        except CommitmentType.DoesNotExist:
            try:
                if parent:
                    creation = parent.process_types.get(
                        stage__isnull=True)
                else:
                    creation = self.process_types.get(
                        stage__isnull=True)
            except CommitmentType.DoesNotExist:
                pass
        if creation:
            creation.follow_stage_chain_beyond_workflow(chain)
        return chain, inheritance

    def staged_process_type_sequence(self):
        # import pdb; pdb.set_trace()
        # pr changed
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
        # pr changed
        pts = []
        stages, inheritance = self.staged_commitment_type_sequence_beyond_workflow()
        for stage in stages:
            if stage.process_type not in pts:
                pts.append(stage.process_type)
        return pts, inheritance

    def recipe_needs_starting_resource(self):
        # todo pr: shd this pass inheritance on?
        # shd recipe_is_staged consider own_or_parent_recipes?
        # import pdb; pdb.set_trace()
        if not self.recipe_is_staged():
            return False
        seq, inheritance = self.staged_commitment_type_sequence()
        answer = False
        if seq:
            ct0 = seq[0]
            if ct0.event_type.name == 'To Be Changed':
                answer = True
        return answer

    def has_listable_recipe(self):
        # todo pr: shd this be own or own_or_parent_recipes?
        answer = False
        ctype, inheritance = self.own_or_parent_recipes()
        if ctype:
            answer = True
            if self.recipe_needs_starting_resource():
                answer = False
        return answer

    def can_be_parent(self):
        if self.own_recipes():
            # if self.recipe_is_staged():
            return True
        return False

    def generate_staged_work_order(self, order_name, start_date, user):
        # pr changed
        # import pdb; pdb.set_trace()
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
            # import pdb; pdb.set_trace()
            assert octs.count() == 1, 'generate_staged_work_order assumes one and only output'
            order_item = octs[0]
            order.due_date = last_process.end_date
            order.save()
        # Todo: apply selected_context_agent here
        for process in processes:
            for ct in process.commitments.all():
                ct.independent_demand = order
                ct.order_item = order_item
                ct.save()
        return order

    def generate_staged_order_item(self, order, start_date, user):
        # pr changed
        pts, inheritance = self.staged_process_type_sequence()
        # import pdb; pdb.set_trace()
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
            # import pdb; pdb.set_trace()
            assert octs.count() == 1, 'generate_staged_order_item assumes one and only one output'
            order_item = octs[0]
            if order.due_date < last_process.end_date:
                order.due_date = last_process.end_date
                order.save()
        # Todo: apply selected_context_agent here
        for process in processes:
            for ct in process.commitments.all():
                ct.independent_demand = order
                ct.order_item = order_item
                ct.save()
        return order

    def generate_staged_work_order_from_resource(self, resource, order_name, start_date, user):
        # pr changed
        # import pdb; pdb.set_trace()
        pts, inheritance = self.staged_process_type_sequence()
        # import pdb; pdb.set_trace()
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
            # pr changed
            if not resource.resource_type.substitutable:
                resource.independent_demand = order
                resource.order_item = order_item
                resource.save()
        # Todo: apply selected_context_agent here
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
        # import pdb; pdb.set_trace()
        # todo: does this still return false positives?
        # todo pr: cd this be shortcut but looking at recipes first?
        # todo pr: shd this be own or own_or_parent_recipes?
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

    # does not seem to be used
    def is_purchased(self):
        rts = all_purchased_resource_types()
        return self in rts

    def consuming_process_type_relationships(self):
        # todo pr: shd this be own or own_or_parent_recipes?
        return self.process_types.filter(event_type__resource_effect='-')

    def citing_process_type_relationships(self):
        # todo pr: shd this be own or own_or_parent_recipes?
        return self.process_types.filter(event_type__relationship='cite')

    def wanting_process_type_relationships(self):
        # todo pr: shd this be own or own_or_parent_recipes?
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
        # todo pr: shd this be own or own_or_parent_recipes?
        return self.process_types.exclude(event_type__relationship='out')

    def wanting_process_type_relationships_for_stage(self, stage):
        # todo pr: shd this be own or own_or_parent_recipes?
        return self.process_types.exclude(event_type__relationship='out').filter(stage=stage)

    def wanting_process_types(self):
        # todo pr: shd this be own or own_or_parent_recipes?
        return [pt.process_type for pt in self.wanting_process_type_relationships()]

    def consuming_process_types(self):
        # todo pr: shd this be own or own_or_parent_recipes?
        return [pt.process_type for pt in self.consuming_process_type_relationships()]

    def producing_agent_relationships(self):
        return self.agents.filter(event_type__relationship='out')

    def work_agent_relationships(self):
        return self.agents.filter(event_type__relationship='work')

    def consuming_agent_relationships(self):
        return self.agents.filter(event_type__relationship='in')

    def consuming_agents(self):
        return [art.agent for art in self.consuming_agent_relationships()]

    def producing_agents(self):
        return [art.agent for art in self.producing_agent_relationships()]

    def work_agents(self):
        return [art.agent for art in self.work_agent_relationships()]

    def producer_relationships(self):
        return self.agents.filter(event_type__relationship='out')

    def producers(self):
        arts = self.producer_relationships()
        return [art.agent for art in arts]

    # todo: failures do not have commitments. If and when they do, the next two methods must change.
    # flow todo: workflow items will have more than one of these
    def producing_commitments(self):
        return self.commitments.filter(
            Q(event_type__relationship='out') |
            Q(event_type__name='Receipt'))

    def active_producing_commitments(self):
        producing_commitments = self.producing_commitments()
        return producing_commitments.filter(process__finished=False)

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
        # answer.append(self)
        return answer

    def xbill_children(self):
        answer = []
        # todo pr: this shd be own_recipes
        answer.extend(self.manufacturing_producing_process_type_relationships())
        # answer.extend(self.producer_relationships())
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
        from django_rea.valueaccounting.utils import explode_xbill_children, xbill_dfs, annotate_tree_properties
        nodes = []
        exploded = []
        # import pdb; pdb.set_trace()
        for kid in self.xbill_children():
            explode_xbill_children(kid, nodes, exploded)
        nodes = list(set(nodes))
        # import pdb; pdb.set_trace()
        to_return = []
        visited = []
        for kid in self.xbill_children():
            to_return.extend(xbill_dfs(kid, nodes, visited, 1))
        # import pdb; pdb.set_trace()
        annotate_tree_properties(to_return)
        return to_return

    def change_form(self):
        # todo pr: self shd be excluded from parents
        from django_rea.valueaccounting.forms import EconomicResourceTypeChangeForm
        return EconomicResourceTypeChangeForm(instance=self)

    def resource_create_form(self, prefix):
        from django_rea.valueaccounting.forms import EconomicResourceForm
        init = {"unit_of_quantity": self.unit, }
        return EconomicResourceForm(prefix=prefix, initial=init)

    def process_create_prefix(self):
        return "".join(["PC", str(self.id)])

    def process_create_form(self):
        from django_rea.valueaccounting.forms import XbillProcessTypeForm
        init = {"name": " ".join(["Make", self.name])}
        return XbillProcessTypeForm(initial=init, prefix=self.process_create_prefix())
        # return XbillProcessTypeForm(prefix=self.process_create_prefix())

    def process_stream_create_form(self):
        from django_rea.valueaccounting.forms import RecipeProcessTypeForm
        # init = {"name": " ".join(["Make", self.name])}
        # return RecipeProcessTypeForm(initial=init, prefix=self.process_create_prefix())
        return RecipeProcessTypeForm(prefix=self.process_create_prefix())

    def source_create_prefix(self):
        return "".join(["SRC", str(self.id)])

    def source_create_form(self):
        from django_rea.valueaccounting.forms import AgentResourceTypeForm
        return AgentResourceTypeForm(prefix=self.source_create_prefix())

    def form_prefix(self):
        return "".join(["RT", str(self.id)])

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
        return ", ".join([facet.facet_value.__str__() for facet in self.facets.all()])

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
        # import pdb; pdb.set_trace()
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

    def uninventoried(self):
        if self.inventory_rule == "yes":
            return False
        else:
            return True


# todo exchange redesign fallout
# many of these are obsolete
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
    ('cash', _('cash input')),
    ('resource', _('resource contribution')),
    ('receivecash', _('cash receipt')),
    ('shipment', _('shipment')),
    ('distribute', _('distribution')),
    ('adjust', _('adjust')),
    # ('payexpense', _('expense payment')),
    ('disburse', _('disburses cash')),
)

RELATED_CHOICES = (
    ('process', _('process')),
    ('agent', _('agent')),  # not used logically as an event type, rather for agent - resource type relationships
    ('exchange', _('exchange')),
    ('distribution', _('distribution')),
)

RESOURCE_EFFECT_CHOICES = (
    ('+', _('increase')),
    ('-', _('decrease')),
    ('+-', _('adjust')),
    ('x', _('transfer')),  # means - for from_agent, + for to_agent
    ('=', _('no effect')),
    ('<', _('failure')),
    ('+~', _('create to change')),
    ('>~', _('to be changed')),
    ('~>', _('change')),
)

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


class EventTypeManager(models.Manager):
    def get_by_natural_key(self, name):
        return self.get(name=name)

    def used_for_value_equations(self):
        ets = EventType.objects.all()
        used_ids = [et.id for et in ets if et.used_for_value_equations()]
        return EventType.objects.filter(id__in=used_ids)

    # todo exchange redesign fallout
    # obsolete event type
    def cash_event_types(self):
        return EventType.objects.filter(relationship="cash")


@python_2_unicode_compatible
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

    def __str__(self):
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
                    print
                    "Updated %s EventType" % name
        except cls.DoesNotExist:
            cls(name=name, label=label, inverse_label=inverse_label, relationship=relationship,
                related_to=related_to, resource_effect=resource_effect, unit_type=unit_type).save()
            if verbosity > 1:
                print
                "Created %s EventType" % name

    def default_event_value_equation(self):
        # todo exchange redesign fallout
        # some of these are obsolete
        if self.used_for_value_equations():
            if self.relationship == "cite" or self.relationship == "pay" or self.name == "Cash Receipt":
                return "quantity"
            elif self.relationship == "resource" or self.relationship == "receive":
                return "value"
            elif self.relationship == "expense" or self.relationship == "cash":
                return "value"
            elif self.relationship == "use":
                return "quantity * valuePerUnitOfUse"
            else:
                return "quantity * valuePerUnit"
        return ""

    def used_for_value_equations(self):
        # todo exchange redesign fallout
        # some of these are obsolete
        bad_relationships = [
            "consume",
            "in",
            # "pay",
            # "receivecash",
            "shipment",
            "adjust",
            "distribute",
            "use",
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
        if "+" in self.resource_effect:
            # this is to rule out adjustments
            if not "-" in self.resource_effect:
                return True
        return False

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


class ExchangeTypeManager(models.Manager):
    # before deleting this, track down the connections
    def sale_exchange_types(self):
        return ExchangeType.objects.filter(use_case__identifier='sale')

    def internal_exchange_types(self):
        return ExchangeType.objects.filter(use_case__identifier='intrnl_xfer')

    def supply_exchange_types(self):
        return ExchangeType.objects.filter(use_case__identifier='supply_xfer')

    def demand_exchange_types(self):
        return ExchangeType.objects.filter(use_case__identifier='demand_xfer')

    def membership_share_exchange_type(self):
        try:
            xt = ExchangeType.objects.get(name='Membership Contribution')
        except ExchangeType.DoesNotExist:
            raise ValidationError("Membership Contribution does not exist by that name")
        return xt


@python_2_unicode_compatible
class ExchangeType(models.Model):
    name = models.CharField(_('name'), max_length=128)
    use_case = models.ForeignKey("UseCase",
                                 blank=True, null=True,
                                 verbose_name=_('use case'), related_name='exchange_types')
    description = models.TextField(_('description'), blank=True, null=True)
    created_by = models.ForeignKey(User, verbose_name=_('created by'),
                                   related_name='exchange_types_created', blank=True, null=True, editable=False)
    changed_by = models.ForeignKey(User, verbose_name=_('changed by'),
                                   related_name='exchange_types_changed', blank=True, null=True, editable=False)
    created_date = models.DateField(auto_now_add=True, blank=True, null=True, editable=False)
    changed_date = models.DateField(auto_now=True, blank=True, null=True, editable=False)
    slug = models.SlugField(_("Page name"), editable=False)

    objects = ExchangeTypeManager()

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        unique_slugify(self, self.name)
        super(ExchangeType, self).save(*args, **kwargs)

    def slots(self):
        return self.transfer_types.all()

    def is_deletable(self):
        answer = True
        if self.exchanges.all():
            answer = False
        return answer

    def transfer_types_non_reciprocal(self):
        return self.transfer_types.filter(is_reciprocal=False)

    def transfer_types_reciprocal(self):
        return self.transfer_types.filter(is_reciprocal=True)


class ProcessTypeManager(models.Manager):
    def workflow_process_types(self):
        pts = ProcessType.objects.all()
        workflow_pts = []
        for pt in pts:
            if pt.is_workflow_process_type():
                workflow_pts.append(pt)
        return workflow_pts


@python_2_unicode_compatible
class ProcessType(models.Model):
    name = models.CharField(_('name'), max_length=128)
    parent = models.ForeignKey('self', blank=True, null=True,
                               verbose_name=_('parent'), related_name='sub_process_types', editable=False)
    process_pattern = models.ForeignKey("ProcessPattern",
                                        blank=True, null=True,
                                        verbose_name=_('process pattern'), related_name='process_types')
    context_agent = models.ForeignKey("EconomicAgent",
                                      blank=True, null=True,
                                      limit_choices_to={"is_context": True, },
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

    def __str__(self):
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
        # pr changed
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
        # todo: delete next lines, makes awkward process.names?
        # process.name = " ".join([process.name, oc.resource_type.name])
        # process.save()
        return process

    def produced_resource_type_relationships(self):
        # todo pr: needs own_or_parent_recipes
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
        return self.resource_types.filter(Q(event_type__relationship='consume') | Q(event_type__relationship='use'))

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
        return self.resource_types.exclude(event_type__relationship='out').exclude(
            event_type__relationship='todo').exclude(event_type__name='To Be Changed')

    def all_input_resource_types(self):
        return [ptrt.resource_type for ptrt in self.all_input_resource_type_relationships()]

    def stream_resource_type_relationships(self):
        return self.resource_types.filter(Q(event_type__name='To Be Changed') | Q(event_type__name='Change') | Q(
            event_type__name='Create Changeable'))

    def input_stream_resource_type_relationship(self):
        return self.resource_types.filter(event_type__name='To Be Changed')

    def has_create_changeable_output(self):
        # import pdb; pdb.set_trace()
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
        from django_rea.valueaccounting.forms import XbillProcessTypeForm
        qty = Decimal("0.0")
        prtr = self.main_produced_resource_type_relationship()
        if prtr:
            qty = prtr.quantity
        init = {"quantity": qty, }
        return XbillProcessTypeForm(instance=self, initial=init, prefix=self.xbill_change_prefix())

    def recipe_change_form(self):
        from django_rea.valueaccounting.forms import RecipeProcessTypeChangeForm
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
        from django_rea.valueaccounting.forms import ProcessTypeInputForm
        return ProcessTypeInputForm(process_type=self, prefix=self.xbill_input_prefix())

    def xbill_consumable_form(self):
        # import pdb; pdb.set_trace()
        from django_rea.valueaccounting.forms import ProcessTypeConsumableForm
        return ProcessTypeConsumableForm(process_type=self, prefix=self.xbill_consumable_prefix())

    def xbill_usable_form(self):
        from django_rea.valueaccounting.forms import ProcessTypeUsableForm
        return ProcessTypeUsableForm(process_type=self, prefix=self.xbill_usable_prefix())

    def xbill_citable_form(self):
        # import pdb; pdb.set_trace()
        from django_rea.valueaccounting.forms import ProcessTypeCitableForm
        return ProcessTypeCitableForm(process_type=self, prefix=self.xbill_citable_prefix())

    def stream_recipe_citable_form(self):
        from django_rea.valueaccounting.forms import ProcessTypeCitableStreamRecipeForm
        return ProcessTypeCitableStreamRecipeForm(process_type=self, prefix=self.xbill_citable_prefix())

    def xbill_work_form(self):
        from django_rea.valueaccounting.forms import ProcessTypeWorkForm
        return ProcessTypeWorkForm(process_type=self, prefix=self.xbill_work_prefix())

    def xbill_input_rt_form(self):
        from django_rea.valueaccounting.forms import EconomicResourceTypeAjaxForm
        return EconomicResourceTypeAjaxForm(prefix=self.xbill_input_rt_prefix())

    def xbill_consumable_rt_form(self):
        from django_rea.valueaccounting.forms import EconomicResourceTypeAjaxForm
        return EconomicResourceTypeAjaxForm(prefix=self.xbill_consumable_rt_prefix())

    def xbill_usable_rt_form(self):
        from django_rea.valueaccounting.forms import EconomicResourceTypeAjaxForm
        return EconomicResourceTypeAjaxForm(prefix=self.xbill_usable_rt_prefix())

    def xbill_citable_rt_form(self):
        from django_rea.valueaccounting.forms import EconomicResourceTypeAjaxForm
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
        # import pdb; pdb.set_trace()
        from django_rea.valueaccounting.forms import RecipeProcessTypeForm
        rt = self.stream_resource_type()
        # init = {"name": " ".join(["Make", rt.name])}
        # return RecipeProcessTypeForm(initial=init, prefix=self.stream_process_type_create_prefix())
        return RecipeProcessTypeForm(prefix=self.stream_process_type_create_prefix())

    def stream_resource_type(self):
        # import pdb; pdb.set_trace()
        answer = None
        ptrts = self.resource_types.all()
        for ptrt in ptrts:
            if ptrt.is_change_related():
                answer = ptrt.resource_type
        return answer

    def create_facet_formset_filtered(self, pre, slot, data=None):
        from django.forms.models import formset_factory
        from django_rea.valueaccounting.forms import ResourceTypeFacetValueForm
        # import pdb; pdb.set_trace()
        RtfvFormSet = formset_factory(ResourceTypeFacetValueForm, extra=0)
        init = []
        if self.process_pattern == None:
            facets = Facet.objects.all()
        else:
            # facets = self.process_pattern.facets_by_relationship(slot)
            if slot == "consume":
                facets = self.process_pattern.consumable_facets()
            elif slot == "use":
                facets = self.process_pattern.usable_facets()
            elif slot == "cite":
                facets = self.process_pattern.citable_facets()
        for facet in facets:
            d = {"facet_id": facet.id, }
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


@python_2_unicode_compatible
class TransferType(models.Model):
    name = models.CharField(_('name'), max_length=128)
    sequence = models.IntegerField(_('sequence'), default=0)
    exchange_type = models.ForeignKey(ExchangeType,
                                      verbose_name=_('exchange type'), related_name='transfer_types')
    description = models.TextField(_('description'), blank=True, null=True)
    is_contribution = models.BooleanField(_('is contribution'), default=False)
    is_to_distribute = models.BooleanField(_('is to distribute'), default=False)
    is_reciprocal = models.BooleanField(_('is reciprocal'), default=False)
    can_create_resource = models.BooleanField(_('can create resource'), default=False)
    is_currency = models.BooleanField(_('is currency'), default=False)
    give_agent_is_context = models.BooleanField(_('give agent is context'), default=False)
    receive_agent_is_context = models.BooleanField(_('receive agent is context'), default=False)
    give_agent_association_type = models.ForeignKey(AgentAssociationType,
                                                    blank=True, null=True,
                                                    verbose_name=_('give agent association type'),
                                                    related_name='transfer_types_give')
    receive_agent_association_type = models.ForeignKey(AgentAssociationType,
                                                       blank=True, null=True,
                                                       verbose_name=_('receive agent association type'),
                                                       related_name='transfer_types_receive')
    created_by = models.ForeignKey(User, verbose_name=_('created by'),
                                   related_name='transfer_types_created', blank=True, null=True, editable=False)
    changed_by = models.ForeignKey(User, verbose_name=_('changed by'),
                                   related_name='transfer_types_changed', blank=True, null=True, editable=False)
    created_date = models.DateField(auto_now_add=True, blank=True, null=True, editable=False)
    changed_date = models.DateField(auto_now=True, blank=True, null=True, editable=False)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('sequence',)

    def is_deletable(self):
        if self.transfers.all():
            return False
        return True

    def facets(self):
        facets = [ttfv.facet_value.facet for ttfv in self.facet_values.all()]
        return list(set(facets))

    def get_resource_types(self):
        # import pdb; pdb.set_trace()
        tt_facet_values = self.facet_values.all()
        facet_values = [ttfv.facet_value for ttfv in tt_facet_values]
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

    def to_agents(self, context_agent):
        # import pdb; pdb.set_trace()
        if self.receive_agent_association_type:
            return context_agent.has_associates_self_or_inherited(self.receive_agent_association_type.identifier)
        else:
            return EconomicAgent.objects.all()

    def from_agents(self, context_agent):
        if self.give_agent_association_type:
            return context_agent.has_associates_self_or_inherited(self.give_agent_association_type.identifier)
        else:
            return EconomicAgent.objects.all()

    def form_prefix(self):
        return "-".join(["TT", str(self.id)])

    def change_form(self):
        from django_rea.valueaccounting.forms import TransferTypeForm
        prefix = self.form_prefix()
        return TransferTypeForm(instance=self, prefix=prefix)


class ResourceTypeSpecialPrice(models.Model):
    resource_type = models.ForeignKey("EconomicResourceType",
                                      verbose_name=_('resource type'), related_name='prices')
    identifier = models.CharField(_('identifier'), max_length=128)
    description = models.TextField(_('description'), blank=True, null=True)
    price_per_unit = models.DecimalField(_('price per unit'), max_digits=8, decimal_places=2,
                                         default=Decimal("0.00"))
    stage = models.ForeignKey(ProcessType, related_name="price_at_stage",
                              verbose_name=_('stage'), blank=True, null=True)


@python_2_unicode_compatible
class ResourceTypeList(models.Model):
    name = models.CharField(_('name'), max_length=128)
    description = models.TextField(_('description'), blank=True, null=True)
    context_agent = models.ForeignKey("EconomicAgent",
                                      blank=True, null=True,
                                      limit_choices_to={"is_context": True, },
                                      verbose_name=_('context agent'), related_name='lists')

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name

    def resource_types_string(self):
        return ", ".join([elem.resource_type.name for elem in self.list_elements.all()])

    def form_prefix(self):
        return "-".join(["RTL", str(self.id)])

    def change_form(self):
        from django_rea.valueaccounting.forms import ResourceTypeListForm
        prefix = self.form_prefix()
        rt_ids = [elem.resource_type.id for elem in self.resource_types.all()]
        init = {"resource_types": rt_ids, }
        return ResourceTypeListForm(instance=self, prefix=prefix, initial=init)

    def recipe_class(self):
        answer = "workflow"
        for elem in self.list_elements.all():
            if not elem.resource_type.recipe_is_staged():
                answer = "manufacturing"
        return answer


@python_2_unicode_compatible
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

    def __str__(self):
        return ": ".join([self.resource_type_list.name, self.resource_type.name])


class UseCaseEventType(models.Model):
    use_case = models.ForeignKey("UseCase",
        verbose_name=_('use case'), related_name='event_types')
    event_type = models.ForeignKey(EventType,
        verbose_name=_('event type'), related_name='use_cases')

    def __str__(self):
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
            print("Created %s UseCaseEventType" % (use_case_identifier + " " + event_type_name))
