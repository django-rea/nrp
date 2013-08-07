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
                relationship="in",
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


        

         
