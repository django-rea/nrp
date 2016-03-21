import datetime
from decimal import *

from django.test import TestCase
from django.test import Client

from valuenetwork.valueaccounting.models import *
from valuenetwork.valueaccounting.views import *
from valuenetwork.valueaccounting.utils import *
#from valuenetwork.valueaccounting.tests.objects_for_testing import *
from valuenetwork.valueaccounting.tests.value_equation_test_objects import *

class ValueEquationTest(TestCase):

    """Testing Value Equations
    """

    def setUp(self):

        self.user = User.objects.create_user('alice', 'alice@whatever.com', 'password')

        self.recipe = ValueEquationRecipe()
        recipe = self.recipe
        self.parent = recipe.parent
        self.child = recipe.child
        self.grandchild = recipe.grandchild
        self.unit = recipe.unit
        self.consumption_event_type = recipe.consumption_event_type
        context_agent=self.recipe.value_equation.context_agent

        self.order = Order(
            due_date=datetime.date.today(),            
        )
        self.order.save()

        self.order.add_commitment(
            resource_type=self.parent,
            context_agent=context_agent,
            event_type=recipe.production_event_type,
            quantity=Decimal("1"),
            description="Test",
            unit=self.unit,            
        )
        
        cts = self.order.order_items()
        self.order_item = cts[0]
        commitment = self.order_item
        #import pdb; pdb.set_trace()
        visited = []
        process = commitment.generate_producing_process(self.user, visited, explode=True)
        
        #need production event
        
        pet = self.recipe.production_event_type
        
        pevent = EconomicEvent(
            event_type=pet,
            resource_type=self.parent,
            from_agent=self.recipe.worker,
            to_agent=context_agent,
            process=process,
            context_agent=context_agent,
            quantity=Decimal("1"),
            unit_of_quantity=self.parent.unit,
            commitment=self.order_item,
            value=Decimal("50"),
            event_date=datetime.date.today(),
            )
        pevent.save()
        
        uet = self.recipe.use_event_type
        usable = self.recipe.usable
        
        uevent = EconomicEvent(
            event_type=uet,
            resource_type=usable.resource_type,
            resource=usable,
            from_agent=self.recipe.worker,
            to_agent=context_agent,
            process=process,
            context_agent=context_agent,
            quantity=Decimal("1"),
            unit_of_quantity=usable.resource_type.unit_of_use,
            #commitment=?,
            event_date=datetime.date.today(),
            )
        uevent.save()
        
        child_input = process.incoming_commitments()[0]
        child_output=child_input.associated_producing_commitments()[0]
        child_process=child_output.process
        grandchild_input = child_process.incoming_commitments()[0]
        used_commitment = process.used_input_requirements()[0]
        use_event = EconomicEvent(
            event_type=used_commitment.event_type,
            resource_type=used_commitment.resource_type,
            resource=self.recipe.usable,
            from_agent=self.recipe.worker,
            to_agent=context_agent,
            context_agent=context_agent,
            quantity=Decimal("1"),
            unit_of_quantity=used_commitment.unit_of_quantity,
            commitment=used_commitment,
            event_date=datetime.date.today(),
            )
        use_event.save()
        
        child_resource = EconomicResource(
            resource_type=child_input.resource_type,
            identifier="child1",
            quantity=Decimal("1"),
            )
        child_resource.save()
        
        consumption_event = EconomicEvent(
            event_type=child_input.event_type,
            resource_type=child_input.resource_type,
            process=child_input.process,
            resource=child_resource,
            from_agent=self.recipe.worker,
            to_agent=context_agent,
            context_agent=context_agent,
            quantity=Decimal("1"),
            unit_of_quantity=child_input.unit_of_quantity,
            commitment=child_input,
            event_date=datetime.date.today(),
            )
        consumption_event.save()
        
        production_event = EconomicEvent(
            event_type=child_output.event_type,
            resource_type=child_output.resource_type,
            process=child_output.process,
            resource=child_resource,
            from_agent=self.recipe.worker,
            to_agent=context_agent,
            context_agent=context_agent,
            quantity=Decimal("1"),
            unit_of_quantity=child_input.unit_of_quantity,
            commitment=child_output,
            event_date=datetime.date.today(),
            )
        production_event.save()
        
        work_rt = EconomicResourceType(
            name="Work Resource Type",
        )
        work_rt.save()
        
        work_event = EconomicEvent(
            event_type=self.recipe.work_event_type,
            resource_type=work_rt,
            process=child_process,
            from_agent=self.recipe.worker,
            to_agent=context_agent,
            context_agent=context_agent,
            quantity=Decimal("1"),
            unit_of_quantity=self.recipe.hours_unit,
            event_date=datetime.date.today(),
            is_contribution=True,
            )
        work_event.save()
        
        event = EconomicEvent(
            event_type=self.consumption_event_type,
            from_agent=self.recipe.contributor,
            to_agent=context_agent,
            event_date=datetime.date.today(),
            process=child_process,
            resource_type=self.recipe.consumable_rt,
            resource=self.recipe.consumable,
            context_agent=context_agent,
            quantity=Decimal("1.0"),
            unit_of_quantity=self.unit,
            )
        event.save()

        
    def test_setup(self):
        
        parent = self.recipe.parent
        parent_pt = parent.main_producing_process_type()
        #import pdb; pdb.set_trace()
        cts = self.order.order_items()
        commitment = cts[0]
        process = commitment.process
        child_input = process.incoming_commitments()[0]
        child_output=child_input.associated_producing_commitments()[0]
        child_process=child_output.process
        grandchild_input = child_process.incoming_commitments()[0]
        used = self.recipe.parent.main_producing_process_type().used_resource_type_relationships()[0]
        used_commitment = process.used_input_requirements()[0]
        self.assertEqual(used_commitment.resource_type, self.recipe.usable.resource_type)
        consumable = self.recipe.consumable
        import pdb; pdb.set_trace()
        
    def test_contribution_shares(self):
        ve = self.recipe.value_equation
        #import pdb; pdb.set_trace()
        shares = self.order_item.compute_income_fractions_for_process(ve)
        #import pdb; pdb.set_trace()
        resource_contributions = [share for share in shares if share.event_type.name=="Receive"]
        self.assertEqual(len(resource_contributions), 1)
        resource_contributions = resource_contributions[0]
        self.assertEqual(resource_contributions.share, Decimal("10.0"))
        work_contributions = [share for share in shares if share.event_type.name=="Time Contribution"]
        work_contributions = work_contributions[0]
        self.assertEqual(work_contributions.share, Decimal("25.0"))
        resource_productions = [share for share in shares if share.event_type.name=="Resource Production"]
        resource_production = resource_productions[0]
        self.assertEqual(resource_production.share, Decimal("50.0"))
        payment_for_consumable = [share for share in shares if share.event_type.name=="Give"][0]
        self.assertEqual(payment_for_consumable.share, Decimal("50.0"))
        
        
