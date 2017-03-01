from __future__ import print_function

from operator import attrgetter

from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import python_2_unicode_compatible

from django_rea.valueaccounting.models.resource import EconomicResource


@python_2_unicode_compatible
class Facet(models.Model):
    name = models.CharField(_('name'), max_length=32, unique=True)
    description = models.TextField(_('description'), blank=True, null=True)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name

    def value_list(self):
        return ", ".join([fv.value for fv in self.values.all()])


@python_2_unicode_compatible
class FacetValue(models.Model):
    facet = models.ForeignKey(Facet,
                              verbose_name=_('facet'), related_name='values')
    value = models.CharField(_('value'), max_length=32)
    description = models.TextField(_('description'), blank=True, null=True)

    class Meta:
        unique_together = ('facet', 'value')
        ordering = ('facet', 'value')

    def __str__(self):
        return ": ".join([self.facet.name, self.value])


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


@python_2_unicode_compatible
class PatternFacetValue(models.Model):
    pattern = models.ForeignKey("ProcessPattern",
                                verbose_name=_('pattern'), related_name='facets')
    facet_value = models.ForeignKey(FacetValue,
                                    verbose_name=_('facet value'), related_name='patterns')
    event_type = models.ForeignKey("EventType",
                                   verbose_name=_('event type'), related_name='patterns',
                                   help_text=_('consumed means gone, used means re-usable'))

    class Meta:
        unique_together = ('pattern', 'facet_value', 'event_type')
        ordering = ('pattern', 'event_type', 'facet_value')

    def __str__(self):
        return ": ".join([self.pattern.name, self.facet_value.facet.name, self.facet_value.value])


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
        from django_rea.valueaccounting.models.recipe import EconomicResourceType
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
        from django_rea.valueaccounting.models.recipe import EconomicResourceType
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
        from django_rea.valueaccounting.models.recipe import EconomicResourceType
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
        from django_rea.valueaccounting.models.recipe import EconomicResourceType
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
        from django_rea.valueaccounting.models.recipe import EconomicResourceType
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
        from django_rea.valueaccounting.models.recipe import EconomicResourceType
        rts = [rt for rt in self.consumable_resource_types() if rt.onhand()]
        rt_ids = [rt.id for rt in rts]
        return EconomicResourceType.objects.filter(id__in=rt_ids)

    def usable_resource_types(self):
        return self.resource_types_for_relationship("use")

    def usables_with_resources(self):
        from django_rea.valueaccounting.models.recipe import EconomicResourceType
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
        from django_rea.valueaccounting.models.recipe import EventType
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
class TransferTypeFacetValue(models.Model):
    transfer_type = models.ForeignKey("TransferType",
                                      verbose_name=_('transfer type'), related_name='facet_values')
    facet_value = models.ForeignKey("FacetValue",
                                    verbose_name=_('facet value'), related_name='transfer_types')

    class Meta:
        unique_together = ('transfer_type', 'facet_value')
        ordering = ('transfer_type', 'facet_value')

    def __str__(self):
        return ": ".join([self.transfer_type.name, self.facet_value.facet.name, self.facet_value.value])


class UseCaseManager(models.Manager):
    def get_by_natural_key(self, identifier):
        # import pdb; pdb.set_trace()
        return self.get(identifier=identifier)

    def exchange_use_cases(self):
        return UseCase.objects.filter(
            Q(identifier="supply_xfer") | Q(identifier="demand_xfer") | Q(identifier="intrnl_xfer"))


@python_2_unicode_compatible
class UseCaseEventType(models.Model):
    use_case = models.ForeignKey("UseCase",
                                 verbose_name=_('use case'), related_name='event_types')
    event_type = models.ForeignKey("EventType",
                                   verbose_name=_('event type'), related_name='use_cases')

    def __str__(self):
        return ": ".join([self.use_case.name, self.event_type.name])

    @classmethod
    def create(cls, use_case_identifier, event_type_name):
        """
        Creates a new UseCaseEventType, updates an existing one, or does nothing.
        This is intended to be used as a post_syncdb manangement step.
        """
        from django_rea.valueaccounting.models.recipe import EventType
        try:
            use_case = UseCase.objects.get(identifier=use_case_identifier)
            event_type = EventType.objects.get(name=event_type_name)
            ucet = cls._default_manager.get(use_case=use_case, event_type=event_type)
        except cls.DoesNotExist:
            cls(use_case=use_case, event_type=event_type).save()
            # import pdb; pdb.set_trace()
            print("Created %s UseCaseEventType" % (use_case_identifier + " " + event_type_name))


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
        from django_rea.valueaccounting.models.recipe import EventType
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
