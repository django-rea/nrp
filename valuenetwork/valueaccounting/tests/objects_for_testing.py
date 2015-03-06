import datetime
from decimal import *

from valuenetwork.valueaccounting.models import *

class Recipe(object):
    def __init__(self, 
        parent=None, 
        child=None, 
        grandchild=None,
        unit=None,
        production_event_type=None,
        consumption_event_type=None,
    ):
        self.parent = parent
        self.child = child
        self.grandchild = grandchild

        if not parent:
            self.parent = EconomicResourceType(
                name="parent",
            )
            self.parent.save()

        if not child:
            self.child = EconomicResourceType(
                name="child",
            )
            self.child.save()

        if not grandchild:
            self.grandchild = EconomicResourceType(
            name="grandchild",
            )
            self.grandchild.save()

        if not unit:
            self.unit = Unit(
                unit_type="quantity",
                abbrev="EA",
                name="each",
            )
            self.unit.save()

        if not production_event_type:
            try:
                et = EventType.objects.get(label="produces")
                self.production_event_type = et
            except EventType.DoesNotExist:
                self.production_event_type = EventType(
                    name="production",
                    label="produces",
                    relationship="out",
                    resource_effect="+",
                )
                self.production_event_type.save()

        if not consumption_event_type:
            try:
                et = EventType.objects.get(label="consumes")
                self.consumption_event_type = et
            except EventType.DoesNotExist:
                self.consumption_event_type = EventType(
                    name="consumption",
                    label="consumes",
                    relationship="consume",
                    resource_effect="-",
                )
                self.consumption_event_type.save()

        parent_pt = ProcessType(
            name="make parent",
            estimated_duration=7200,
        )
        parent_pt.save()

        child_pt = ProcessType(
            name="make child",
            estimated_duration=14400,
        )
        child_pt.save()
     
        parent_output = ProcessTypeResourceType(
            process_type=parent_pt,
            resource_type=self.parent,
            event_type=self.production_event_type,
            quantity=Decimal("1"),
            unit_of_quantity=self.unit,
        )
        parent_output.save()

        child_input = ProcessTypeResourceType(
            process_type=parent_pt,
            resource_type=self.child,
            event_type=self.consumption_event_type,
            quantity=Decimal("2"),
            unit_of_quantity=self.unit,
        )
        child_input.save()

        child_output = ProcessTypeResourceType(
            process_type=child_pt,
            resource_type=self.child,
            event_type=self.production_event_type,
            quantity=Decimal("1"),
            unit_of_quantity=self.unit,
        )
        child_output.save()

        grandchild_input = ProcessTypeResourceType(
            process_type=child_pt,
            resource_type=self.grandchild,
            event_type=self.consumption_event_type,
            quantity=Decimal("3"),
            unit_of_quantity=self.unit,
        )
        grandchild_input.save()

        agent_type = AgentType(
            name="Active",
        )
        agent_type.save()

        agent = EconomicAgent(
            name="Seller",
            nick="Seller",
            agent_type=agent_type,
        )
        agent.save()

        event_type_receive = EventType(
            name="supply",
            label="supplies",
            relationship="out",
            related_to="agent",
            resource_effect="=",
        )
        event_type_receive.save()

        source = AgentResourceType(
            agent=agent,
            resource_type=self.grandchild,
            event_type=event_type_receive,
            lead_time=20,
        )
        source.save()

        
class WorkFlowRecipe(object):
    def __init__(self, 
        changeable=None, 
        unit=None,
        create_event_type=None,
        to_be_event_type=None,
        change_event_type=None,
    ):
        self.changeable = changeable
        self.unit = unit
        self.create_event_type = create_event_type
        self.to_be_event_type = to_be_event_type
        self.change_event_type = change_event_type

        if not changeable:
            self.changeable = EconomicResourceType(
                name="changeable",
                substitutable=False,
            )
            self.changeable.save()
            
        self.another_changeable = EconomicResourceType(
            name="another changeable",
            substitutable=False,
        )
        self.another_changeable.save()

        if not unit:
            self.unit = Unit(
                unit_type="quantity",
                abbrev="Words",
                name="words",
            )
            self.unit.save()

        if not create_event_type:
            try:
                et = EventType.objects.get(name="Create Changeable")
                self.create_event_type = et
            except EventType.DoesNotExist:
                self.create_event_type = EventType(
                    name="Create Changeable",
                    label="creates changeable",
                    relationship="out",
                    resource_effect="+~",
                )
                self.create_event_type.save()
                
        if not to_be_event_type:
            try:
                et = EventType.objects.get(name="To Be Changed")
                self.to_be_event_type = et
            except EventType.DoesNotExist:
                self.to_be_event_type = EventType(
                    name="To Be Changed",
                    label="To Be Changed",
                    relationship="in",
                    resource_effect=">~",
                )
                self.to_be_event_type.save()

        if not change_event_type:
            try:
                et = EventType.objects.get(label="Change")
                self.change_event_type = et
            except EventType.DoesNotExist:
                self.change_event_type = EventType(
                    name="Change",
                    label="changes",
                    relationship="out",
                    resource_effect="~>",
                )
                self.change_event_type.save()

        self.change_pt = ProcessType(
            name="change",
            estimated_duration=7200,
        )
        self.change_pt.save()
        change_pt = self.change_pt

        create_pt = ProcessType(
            name="create",
            estimated_duration=14400,
        )
        create_pt.save()
     
        change_output = ProcessTypeResourceType(
            process_type=change_pt,
            stage=change_pt,
            resource_type=self.changeable,
            event_type=self.change_event_type,
            quantity=Decimal("1000"),
            unit_of_quantity=self.unit,
        )
        change_output.save()

        change_input = ProcessTypeResourceType(
            process_type=change_pt,
            resource_type=self.changeable,
            stage=create_pt,
            event_type=self.to_be_event_type,
            quantity=Decimal("1000"),
            unit_of_quantity=self.unit,
        )
        change_input.save()

        create_output = ProcessTypeResourceType(
            process_type=create_pt,
            stage=create_pt,
            resource_type=self.changeable,
            event_type=self.create_event_type,
            quantity=Decimal("1000"),
            unit_of_quantity=self.unit,
        )
        create_output.save()
        
        change_pt = ProcessType(
            name="change",
            estimated_duration=7200,
        )
        change_pt.save()

        create_pt = ProcessType(
            name="create",
            estimated_duration=14400,
        )
        create_pt.save()
     
        change_output = ProcessTypeResourceType(
            process_type=change_pt,
            stage=change_pt,
            resource_type=self.another_changeable,
            event_type=self.change_event_type,
            quantity=Decimal("3000"),
            unit_of_quantity=self.unit,
        )
        change_output.save()

        change_input = ProcessTypeResourceType(
            process_type=change_pt,
            resource_type=self.another_changeable,
            stage=create_pt,
            event_type=self.to_be_event_type,
            quantity=Decimal("3000"),
            unit_of_quantity=self.unit,
        )
        change_input.save()

        create_output = ProcessTypeResourceType(
            process_type=create_pt,
            stage=create_pt,
            resource_type=self.another_changeable,
            event_type=self.create_event_type,
            quantity=Decimal("3000"),
            unit_of_quantity=self.unit,
        )
        create_output.save()


class Facets(object):
    def __init__(self, 
        domain=None, 
        source=None, 
        optical_pattern=None,
        electronic_pattern=None,
        electroptical_pattern=None,
        twofacet_pattern=None,
        event_type=None,
        optical_product=None,
        electronic_product=None,
        twofacet_product=None,
        other_product=None,
        full_pattern=None,
        event_type_cite=None,
        event_type_use=None,
        event_type_consume=None,
        event_type_work=None,
    ):
        self.domain = domain
        self.source = source
        self.optical_pattern = optical_pattern
        self.electronic_pattern = electronic_pattern
        self.electroptical_pattern = electroptical_pattern
        self.twofacet_pattern = twofacet_pattern
        self.event_type = event_type
        self.optical_product = optical_product
        self.electronic_product = electronic_product
        self.twofacet_product = twofacet_product
        self.other_product = other_product
        self.full_pattern = full_pattern
        self.event_type_cite=event_type_cite
        self.event_type_use=event_type_use
        self.event_type_consume=event_type_consume
        self.event_type_work=event_type_work
        
        if not domain:
            self.domain = Facet(
                name="Domain",
            )
            self.domain.save()

        if not source:
            self.source = Facet(
                name="Source",
            )
            self.source.save()

        optical_domain = FacetValue(
            facet=self.domain,
            value="Optical"
        )
        optical_domain.save()

        electronic_domain = FacetValue(
            facet=self.domain,
            value="Electronical"
        )
        electronic_domain.save()

        work_domain = FacetValue(
            facet=self.domain,
            value="Work"
        )
        work_domain.save()

        source_us = FacetValue(
            facet=self.source,
            value="Us"
        )
        source_us.save()

        source_them = FacetValue(
            facet=self.source,
            value="Them"
        )
        source_them.save()

        use_case = UseCase.objects.get(identifier="rand")

        if not optical_pattern:
            self.optical_pattern = ProcessPattern(
                name="Optics",
            )
            self.optical_pattern.save()

        puc = PatternUseCase(
            pattern=self.optical_pattern,
            use_case=use_case,
        )
        puc.save()

        if not electronic_pattern:
            self.electronic_pattern = ProcessPattern(
                name="Electronics",
            )
            self.electronic_pattern.save()

        puc = PatternUseCase(
            pattern=self.electronic_pattern,
            use_case=use_case,
        )
        puc.save()

        if not electroptical_pattern:
            self.electroptical_pattern = ProcessPattern(
                name="electro optical",
            )
            self.electroptical_pattern.save()

        puc = PatternUseCase(
            pattern=self.electroptical_pattern,
            use_case=use_case,
        )
        puc.save()

        if not twofacet_pattern:
            self.twofacet_pattern = ProcessPattern(
                name="Two facets",
            )
            self.twofacet_pattern.save()

        puc = PatternUseCase(
            pattern=self.twofacet_pattern,
            use_case=use_case,
        )
        puc.save()

        if not full_pattern:
            self.full_pattern = ProcessPattern(
                name="Full pattern",
            )
            self.full_pattern.save()

        puc = PatternUseCase(
            pattern=self.full_pattern,
            use_case=use_case,
        )
        puc.save()

        if not event_type:
            try:
                et = EventType.objects.get(label="produces")
                self.event_type = et
            except EventType.DoesNotExist:
                self.event_type = EventType(
                    name="Production",
                    label="produces",
                    relationship="out",
                    resource_effect="+",
                )
                self.event_type.save()

        if not event_type_use:
            try:
                et = EventType.objects.get(label="uses")
                self.event_type_use = et
            except EventType.DoesNotExist:
                self.event_type_use = EventType(
                    name="Use",
                    label="uses",
                    relationship="use",
                    resource_effect="=",
                )
                self.event_type_use.save()

        if not event_type_cite:
            try:
                et = EventType.objects.get(label="cites")
                self.event_type_cite = et
            except EventType.DoesNotExist:
                self.event_type_cite = EventType(
                    name="Cite",
                    label="cites",
                    relationship="cite",
                    resource_effect="=",
                )
                self.event_type_cite.save()

        if not event_type_consume:
            try:
                et = EventType.objects.get(label="consumes")
                self.event_type_consume = et
            except EventType.DoesNotExist:
                self.event_type_consume = EventType(
                    name="Consume",
                    label="consumes",
                    relationship="consume",
                    resource_effect="-",
                )
                self.event_type_consume.save()

        if not event_type_work:
            try:
                et = EventType.objects.get(label="work")
                self.event_type_work = et
            except EventType.DoesNotExist:
                self.event_type_work = EventType(
                    name="Work",
                    label="work",
                    relationship="work",
                    resource_effect="=",
                )
                self.event_type_work.save()             
           
        pfv = PatternFacetValue(
            pattern=self.optical_pattern,
            facet_value=optical_domain,
            event_type=self.event_type,
        )
        pfv.save()

        pfv = PatternFacetValue(
            pattern=self.electronic_pattern,
            facet_value=electronic_domain,
            event_type=self.event_type,
        )
        pfv.save()

        pfv = PatternFacetValue(
            pattern=self.electroptical_pattern,
            facet_value=electronic_domain,
            event_type=self.event_type,
        )
        pfv.save()

        pfv = PatternFacetValue(
            pattern=self.electroptical_pattern,
            facet_value=optical_domain,
            event_type=self.event_type,
        )
        pfv.save()

        pfv = PatternFacetValue(
            pattern=self.twofacet_pattern,
            facet_value=electronic_domain,
            event_type=self.event_type,
        )
        pfv.save()

        pfv = PatternFacetValue(
            pattern=self.twofacet_pattern,
            facet_value=optical_domain,
            event_type=self.event_type,
        )
        pfv.save()

        pfv = PatternFacetValue(
            pattern=self.twofacet_pattern,
            facet_value=source_us,
            event_type=self.event_type,
        )
        pfv.save()

        pfv = PatternFacetValue(
            pattern=self.full_pattern,
            facet_value=electronic_domain,
            event_type=self.event_type,
        )
        pfv.save()

        pfv = PatternFacetValue(
            pattern=self.full_pattern,
            facet_value=optical_domain,
            event_type=self.event_type,
        )
        pfv.save()

        pfv = PatternFacetValue(
            pattern=self.full_pattern,
            facet_value=source_us,
            event_type=self.event_type,
        )
        pfv.save()

        pfv = PatternFacetValue(
            pattern=self.full_pattern,
            facet_value=electronic_domain,
            event_type=self.event_type_cite,
        )
        pfv.save()

        pfv = PatternFacetValue(
            pattern=self.full_pattern,
            facet_value=source_us,
            event_type=self.event_type_cite,
        )
        pfv.save()

        pfv = PatternFacetValue(
            pattern=self.full_pattern,
            facet_value=optical_domain,
            event_type=self.event_type_consume,
        )
        pfv.save()

        pfv = PatternFacetValue(
            pattern=self.full_pattern,
            facet_value=electronic_domain,
            event_type=self.event_type_use,
        )
        pfv.save()

        pfv = PatternFacetValue(
            pattern=self.full_pattern,
            facet_value=work_domain,
            event_type=self.event_type_work,
        )
        pfv.save()      

        if not optical_product:
            self.optical_product = EconomicResourceType(
                 name="Optical Resource Type",
            )
            self.optical_product.save()

        if not electronic_product:
            self.electronic_product = EconomicResourceType(
                 name="Electronic Resource Type",
            )
            self.electronic_product.save()

        if not twofacet_product:
            self.twofacet_product = EconomicResourceType(
                 name="Two facets Resource Type",
            )
            self.twofacet_product.save()

        if not other_product:
            self.other_product = EconomicResourceType(
                 name="Other Resource Type",
            )
            self.other_product.save()

        work_rt = EconomicResourceType(
            name="Work Resource Type",
        )
        work_rt.save()

        rtfv = ResourceTypeFacetValue(
            resource_type=work_rt,
            facet_value=work_domain,
        )
        rtfv.save()

        rtfv = ResourceTypeFacetValue(
            resource_type=self.optical_product,
            facet_value=optical_domain,
        )
        rtfv.save()

        rtfv = ResourceTypeFacetValue(
            resource_type=self.electronic_product,
            facet_value=electronic_domain,
        )
        rtfv.save()

        rtfv = ResourceTypeFacetValue(
            resource_type=self.twofacet_product,
            facet_value=electronic_domain,
        )
        rtfv.save()

        rtfv = ResourceTypeFacetValue(
            resource_type=self.twofacet_product,
            facet_value=source_us,
        )
        rtfv.save()
     
