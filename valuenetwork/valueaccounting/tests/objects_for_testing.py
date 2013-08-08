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
            self.consumption_event_type = EventType(
                name="consumption",
                label="consumes",
                relationship="consume",
                resource_effect="-",
            )
            self.consumption_event_type.save()

        parent_pt = ProcessType(
            name="make parent",
        )
        parent_pt.save()

        child_pt = ProcessType(
            name="make child",
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

        use_case = "rand"

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
        

         
