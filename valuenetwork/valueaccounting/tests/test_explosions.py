import datetime
from decimal import *

from django.test import TestCase
from django.test import Client

from valuenetwork.valueaccounting.models import *
from valuenetwork.valueaccounting.views import *
from valuenetwork.valueaccounting.utils import *
from .objects_for_testing import *

class ExplosionTest(TestCase):

    """Testing dependent demand explosion
    """

    def setUp(self):

        self.user = User.objects.create_user('alice', 'alice@whatever.com', 'password')

        recipe = Recipe()
        self.parent = recipe.parent
        self.child = recipe.child
        self.grandchild = recipe.grandchild
        self.unit = recipe.unit
        self.consumption_event_type = recipe.consumption_event_type

        self.order = Order(
            due_date=datetime.date.today(),            
        )
        self.order.save()

        self.order.add_commitment(
            resource_type=self.parent,
            event_type=recipe.production_event_type,
            quantity=Decimal("4"),
            unit=self.unit,            
        )

        self.prior_commitment = Commitment(
            resource_type=self.child,
            due_date=self.order.due_date - datetime.timedelta(weeks=4),
            quantity=Decimal(2),
            event_type=self.consumption_event_type,
            unit_of_quantity=self.unit,
        )
        self.prior_commitment.save()

        self.resource = EconomicResource(
            resource_type=self.child,
            quantity=Decimal(5),
            unit_of_quantity=self.unit,
        )
        self.resource.save()

    def test_order_commitment(self):
        cts = self.order.order_items()
        ct = cts[0]
        self.assertEqual(cts.count(), 1)
        self.assertEqual(ct.resource_type, self.parent)

    def test_explosion(self):
        """Explode dependent demands from order item

            Including netting out inventory:
            Child input will meet onhand inventory of 5
            - prior demand of 2 = 3 still available
            which reduces the child input demand from 8 to 5.
            Which also reduces the grandchild demand from 24 to 15.

        """
            
        cts = self.order.order_items()
        commitment = cts[0]
        #import pdb; pdb.set_trace()
        process = commitment.generate_producing_process(self.user, explode=True)
        child_input = process.incoming_commitments()[0]
        self.assertEqual(child_input.quantity, Decimal("8"))
        rt = child_input.resource_type
        child_output=rt.producing_commitments()[0]
        self.assertEqual(child_output.quantity, Decimal("5"))
        child_process=child_output.process
        grandchild_input = child_process.incoming_commitments()[0]
        self.assertEqual(grandchild_input.quantity, Decimal("15"))

    def test_cycle(self):
        """ cycles occur when an explosion repeats itself:

            when an output resource type re-appears as a input
            later in the explosion.  
            In this case, the explosion must not go into 
            an infinite loop.  
            As of now, it just stops exploding.
            Other behaviors may be necessary in the future.

        """
        
        child_pt = self.child.main_producing_process_type()
        cyclic_input = ProcessTypeResourceType(
            process_type=child_pt,
            resource_type=self.parent,
            event_type=self.consumption_event_type,
            quantity=Decimal("1"),
            unit_of_quantity=self.unit,
        )
        cyclic_input.save()
        cts = self.order.order_items()
        commitment = cts[0]
        process = commitment.generate_producing_process(self.user, explode=True)
        child_input = process.incoming_commitments()[0]
        self.assertEqual(child_input.quantity, Decimal("8"))
        rt = child_input.resource_type
        child_output=rt.producing_commitments()[0]
        self.assertEqual(child_output.quantity, Decimal("5"))
        child_process=child_output.process
        grandchild_input = child_process.incoming_commitments()[0]
        self.assertEqual(grandchild_input.quantity, Decimal("15"))
        cyclic_input_commitment = child_process.incoming_commitments()[1]
        self.assertEqual(cyclic_input_commitment.quantity, Decimal("5"))
        crt = cyclic_input_commitment.resource_type
        self.assertEqual(crt.producing_commitments().count(), 1)

        
        
        
        
        
        
            
        
        

