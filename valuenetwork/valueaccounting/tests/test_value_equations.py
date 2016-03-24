import datetime
from decimal import *

from django.test import TestCase
from django.test import Client

from valuenetwork.valueaccounting.models import *
from valuenetwork.valueaccounting.views import *
from valuenetwork.valueaccounting.utils import *
from django.utils import simplejson
from valuenetwork.valueaccounting.tests.value_equation_test_objects import *

"""
    Tests:
    
        Setup:
    
            One order
                for a parent resource
                    from a process with inputs:
                        uses a contributed resource
                        consumes a child resource
                        produced by another process with inputs:
                            some work
                            uses a resource
                                purchased with community contributions
                                with an added expense
                                
            One value equation
                with one bucket: filter_method: order
                    with 4 bucket rules:
                        EventType Work
                        EventType Resource Production
                        EventType Resource Contributionm
                        EventType Payment 
                            for contributors to used community funded resource
                            and to the expense for that purchase
                            
            Not tested:
                More value equations
                    different percentage_behaviors
                More buckets
                    different filter methods
                    direct to agent 
                More bucket rules
                    different division_rules
                    different claim rules
                    different claim_creation_equations
                More distribution runs with partly paid claims
                            
        test_setup:
            A convenience to see if value_equation_test_objects
            and those created in the setUp method below
            are correct.
            
        test_rollup:
            Tests the accumulated value of the parent resource.
            
        test_contribution_shares:
            Tests that the events selected by the ValueEquationBuckets
            got their proportional shares of any distribution
            according to their proportion of the value of the
            deliverablels that generated the income.
            
        test_distribution:
            Tests that the events actually got their distribution quantity
            according to their poportional shares of the accumulated value.

"""

def serialize_filter(orders):
    #import pdb; pdb.set_trace()
    json = {"method": "Order",}
    json["orders"] = [order.id for order in orders]
    
    string = simplejson.dumps(json)            
    return string

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
        
        #need produced resource
        
        self.parent_resource = EconomicResource(
            resource_type=self.parent,
            identifier="parent1",
            quantity=Decimal("1"),
            )
        self.parent_resource.save()
        
        pet = self.recipe.production_event_type
        
        pevent = EconomicEvent(
            event_type=pet,
            resource_type=self.parent,
            resource=self.parent_resource,
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
        
        uet = self.recipe.use_event_type
        community_resource = self.recipe.community_resource
        
        community_use_event = EconomicEvent(
            event_type=uet,
            resource_type=community_resource.resource_type,
            resource=community_resource,
            from_agent=self.recipe.worker,
            to_agent=context_agent,
            process=process,
            context_agent=context_agent,
            quantity=Decimal("1"),
            unit_of_quantity=community_resource.resource_type.unit_of_use,
            #commitment=?,
            event_date=datetime.date.today(),
            )
        community_use_event.save()
        
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
        #import pdb; pdb.set_trace()
        
    def test_rollup(self):
        parent_resource = self.parent_resource
        ve = self.recipe.value_equation
        visited = set()
        path = []
        depth = 0
        #import pdb; pdb.set_trace()
        value_per_unit = parent_resource.roll_up_value(path, depth, visited, ve)
        self.assertEqual(value_per_unit, Decimal("145.0"))

        #import pdb; pdb.set_trace()
        
    def test_contribution_shares(self):
        ve = self.recipe.value_equation
        #import pdb; pdb.set_trace()
        shares = self.order_item.compute_income_fractions_for_process(ve)
        #import pdb; pdb.set_trace()
        work_contribution = [share for share in shares if share.event_type.name=="Time Contribution"][0]
        self.assertEqual(work_contribution.share, Decimal("25.0"))
        resource_production = [share for share in shares if share.event_type.name=="Resource Production"][0]
        self.assertEqual(resource_production.share, Decimal("50.0"))
        
        named = [share for share in shares if share.transfer]
        financial_contribution1 = [share for share in named if share.transfer.name=="financial contribution 1"][0]
        self.assertEqual(financial_contribution1.share, Decimal("30.0"))
        financial_contribution2 = [share for share in named if share.transfer.name=="financial contribution 2"][0]
        self.assertEqual(financial_contribution2.share, Decimal("20.0"))
        resource_contribution = [share for share in named if share.transfer.name=="resource contribution"][0]
        self.assertEqual(resource_contribution.share, Decimal("10.0"))
        payment_for_consumable = [share for share in named if share.transfer.name=="consumable payment"][0]
        self.assertEqual(payment_for_consumable.share, Decimal("50.0"))
        payment_for_expense = [share for share in named if share.transfer.name=="expense payment"][0]
        self.assertEqual(payment_for_expense.share, Decimal("10.0"))
        
        #for share in shares:
        #    print share.from_agent, share.share
        
    def test_distribution(self):
        ve = self.recipe.value_equation
        order = self.order
        orders = [order,]
        buckets = ve.buckets.all()
        #amount_to_distribute = Decimal("1000")
        amount_to_distribute = Decimal("195")
        serialized_filter = serialize_filter(orders)
        serialized_filters = {}
        for bucket in buckets:
            serialized_filters[bucket.id] = serialized_filter
        agent_totals, details = ve.run_value_equation(amount_to_distribute=amount_to_distribute, serialized_filters=serialized_filters)
        for at in agent_totals:
            #print at.to_agent, at.quantity
            if at.to_agent.name == "worker":
                self.assertEqual(at.quantity, Decimal("75.0"))
            elif at.to_agent.name == "contributor":
                self.assertEqual(at.quantity, Decimal("70.0"))
            elif at.to_agent.name == "vacontributor1":
                self.assertEqual(at.quantity, Decimal("30.0"))
            elif at.to_agent.name == "vacontributor2":
                self.assertEqual(at.quantity, Decimal("20.0"))
                
        #import pdb; pdb.set_trace()
