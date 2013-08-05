import datetime
from decimal import *

from django.test import TestCase
from django.test import Client

from valuenetwork.valueaccounting.models import *
from valuenetwork.valueaccounting.views import *
from valuenetwork.valueaccounting.utils import *

class Test(TestCase):

    """Testing dependent demand explosion
    """

    def setUp(self):

        self.user = User.objects.create_user('alice', 'alice@whatever.com', 'password')

        self.parent = EconomicResourceType(
            name="parent",
        )
        self.parent.save()

        child = EconomicResourceType(
            name="child",
        )
        child.save()

        grandchild = EconomicResourceType(
            name="grandchild",
        )
        grandchild.save()

        parent_pt = ProcessType(
            name="make parent",
        )
        parent_pt.save()

        child_pt = ProcessType(
            name="make child",
        )
        child_pt.save()

        production_event_type = EventType(
            name="production",
            label="produces",
            relationship="out",
            resource_effect="+",
        )
        production_event_type.save()

        consumption_event_type = EventType(
            name="consumption",
            label="consumes",
            relationship="in",
            resource_effect="-",
        )
        consumption_event_type.save()

        each = Unit(
            unit_type="quantity",
            abbrev="EA",
            name="each",
        )
        each.save()
        
        parent_output = ProcessTypeResourceType(
            process_type=parent_pt,
            resource_type=self.parent,
            event_type=production_event_type,
            quantity=Decimal("1"),
            unit_of_quantity=each,
        )
        parent_output.save()

        child_input = ProcessTypeResourceType(
            process_type=parent_pt,
            resource_type=child,
            event_type=consumption_event_type,
            quantity=Decimal("2"),
            unit_of_quantity=each,
        )
        child_input.save()

        child_output = ProcessTypeResourceType(
            process_type=child_pt,
            resource_type=child,
            event_type=production_event_type,
            quantity=Decimal("1"),
            unit_of_quantity=each,
        )
        child_output.save()

        grandchild_input = ProcessTypeResourceType(
            process_type=child_pt,
            resource_type=grandchild,
            event_type=consumption_event_type,
            quantity=Decimal("3"),
            unit_of_quantity=each,
        )
        grandchild_input.save()

        self.order = Order(
            due_date=datetime.date.today(),            
        )
        self.order.save()

        self.order.add_commitment(
            resource_type=self.parent,
            event_type=production_event_type,
            quantity=Decimal("4"),
            unit=each,            
        )

        self.prior_commitment = Commitment(
            resource_type=child,
            due_date=self.order.due_date - datetime.timedelta(weeks=4),
            quantity=Decimal(2),
            event_type=consumption_event_type,
            unit_of_quantity=each,
        )
        self.prior_commitment.save()

        self.resource = EconomicResource(
            resource_type=child,
            quantity=Decimal(5),
            unit_of_quantity=each,
        )
        self.resource.save()

    def test_order_commitment(self):
        cts = self.order.order_items()
        ct = cts[0]
        self.assertEqual(cts.count(), 1)
        self.assertEqual(ct.resource_type, self.parent)

    def test_explosion(self):
        """Explode dependent demands from order item

            Child input will meet onhand inventory of 5
            reduced by prior demand = 3
            which reduced the child input demand from 8 to 5.
            Which also reduces the grandchild demand from 24 to 15.

        """
            
        cts = self.order.order_items()
        commitment = cts[0]
        process = commitment.generate_producing_process(self.user)
        if process:
            recursively_explode_demands(process, self.order, self.user)
        child_input = process.input_commitments()[0]
        self.assertEqual(child_input.quantity, Decimal("8"))
        rt = child_input.resource_type
        child_output=rt.producing_commitments()[0]
        self.assertEqual(child_output.quantity, Decimal("5"))
        child_process=child_output.process
        grandchild_input = child_process.input_commitments()[0]
        self.assertEqual(grandchild_input.quantity, Decimal("15"))
        
        
        
        
        
        
        
            
        
        

