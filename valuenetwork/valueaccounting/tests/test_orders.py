import datetime
from decimal import *

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import Client

from webtest import AppError, TestApp

from django_webtest import WebTest

#WebTest doc: http://webtest.pythonpaste.org/en/latest/index.html

from valuenetwork.valueaccounting.models import *
from valuenetwork.valueaccounting.views import *
from valuenetwork.valueaccounting.utils import *
from valuenetwork.valueaccounting.tests.objects_for_testing import *

class OrderTest(WebTest):

    """Testing customer orders
    """

    def setUp(self):
        
        self.user = User.objects.create_user('alice', 'alice@whatever.com', 'password')
        
        facets = Facets()
        self.electronic_pattern = facets.electronic_pattern
        self.full_pattern = facets.full_pattern
        electronic_domain = facets.domain.values.get(value="Electronical")
        source_us = facets.source.values.get(value="Us")
        #
        atype = AgentType(
            name='Network', 
            party_type='network', 
            is_context=True)
        atype.save()
        self.project = EconomicAgent(
            name="Test Project",
            nick="TP",
            agent_type=atype)
        self.project.save()
        recipe = Recipe()
        self.parent = recipe.parent
        self.child = recipe.child
        self.grandchild = recipe.grandchild
        
        self.wf_recipe = WorkFlowRecipe()
        self.changeable = self.wf_recipe.changeable
        self.another_changeable = self.wf_recipe.another_changeable

        sellable = Facet(
            name="Sellable",
        )
        sellable.save()

        sellable_sellable = FacetValue(
            facet=sellable,
            value="sellable"
        )
        sellable_sellable.save()

        order_pattern = ProcessPattern(
            name="Order pattern",
        )
        order_pattern.save()

        use_case = UseCase.objects.get(identifier="cust_orders")

        puc = PatternUseCase(
            pattern=order_pattern,
            use_case=use_case,
        )
        puc.save()

        event_type_sale = EventType(
            name="Sale",
            label="sells",
            relationship="output",
            related_to="agent",
            resource_effect="=",
        )
        event_type_sale.save()  

        pfv = PatternFacetValue(
            pattern=order_pattern,
            facet_value=sellable_sellable,
            event_type=event_type_sale,
        )
        pfv.save()
        
        rtfv = ResourceTypeFacetValue(
            resource_type=self.parent,
            facet_value=sellable_sellable,
        )
        rtfv.save()
        
        rtfv = ResourceTypeFacetValue(
            resource_type=self.changeable,
            facet_value=sellable_sellable,
        )
        rtfv.save()
        
        rtfv = ResourceTypeFacetValue(
            resource_type=self.another_changeable,
            facet_value=sellable_sellable,
        )
        rtfv.save()
        
    def test_create_order(self):
        """Test create_order view

            and subsequent dependent demand explosion
            
        """
       
        response = self.app.get('/accounting/create-order/' , user='alice')
        form = response.form
        #import pdb; pdb.set_trace()
        due_date = datetime.date.today().strftime('%Y-%m-%d')
        form["due_date"] = due_date
        form["RT-6-quantity"] = 3
        response = form.submit("submit1").follow()
        process = self.parent.producing_commitments()[0].process
        incoming = process.incoming_commitments()
        child_input = incoming.filter(resource_type=self.child)[0]
        self.assertEqual(child_input.quantity, Decimal("6"))
        rt = child_input.resource_type
        child_output=rt.producing_commitments()[0]
        child_process=child_output.process
        grandchild_input = child_process.incoming_commitments()[0]
        self.assertEqual(grandchild_input.quantity, Decimal("18"))

        
    def test_create_workflow_order(self):
        """Test create_order for a workflow item

            and subsequent dependent demand explosion
            
        """
       
        response = self.app.get('/accounting/create-order/' , user='alice')
        form = response.form
        #import pdb; pdb.set_trace()
        due_date = datetime.date.today().strftime('%Y-%m-%d')
        form["due_date"] = due_date
        form["RT-9-quantity"] = 2000
        response = form.submit("submit1").follow()
        #import pdb; pdb.set_trace()
        pcs = self.changeable.producing_commitments()
        count = pcs.count()
        self.assertEqual(count, 2)
        first_pc = pcs[0]
        self.assertEqual(first_pc.quantity, Decimal("2000"))
        last_pc = pcs[count - 1]
        #import pdb; pdb.set_trace()
        self.assertEqual(first_pc.order_item, last_pc)
        order = last_pc.order
        processes = order.all_processes()
        self.assertEqual(len(processes), 2)
        first_process = processes[0]
        last_process = processes[count - 1]
        nexts = first_process.next_processes()
        prevs = last_process.previous_processes()
        self.assertTrue(first_process in prevs)
        self.assertTrue(last_process in nexts)
        
           
    def test_two_workflow_item_order(self):
        """Test create_order for two workflow items

            and subsequent dependent demand explosion
            
        """
       
        response = self.app.get('/accounting/create-order/' , user='alice')
        form = response.form
        #import pdb; pdb.set_trace()
        due_date = datetime.date.today().strftime('%Y-%m-%d')
        form["due_date"] = due_date
        form["RT-9-quantity"] = 2000
        form["RT-10-quantity"] = 4000
        response = form.submit("submit1").follow()
        #import pdb; pdb.set_trace()
        
        pcs = self.changeable.producing_commitments()
        count = pcs.count()
        self.assertEqual(count, 2)
        first_pc = pcs[0]
        self.assertEqual(first_pc.quantity, Decimal("2000"))
        last_pc = pcs[count - 1]
        #import pdb; pdb.set_trace()
        self.assertEqual(first_pc.order_item, last_pc)
        
        first_process = first_pc.process
        last_process = last_pc.process
        nexts = first_process.next_processes()
        prevs = last_process.previous_processes()
        self.assertTrue(first_process in prevs)
        self.assertTrue(last_process in nexts)
        
        pcs = self.another_changeable.producing_commitments()
        count = pcs.count()
        self.assertEqual(count, 2)
        first_pc = pcs[0]
        self.assertEqual(first_pc.quantity, Decimal("4000"))
        last_pc = pcs[count - 1]
        #import pdb; pdb.set_trace()
        self.assertEqual(first_pc.order_item, last_pc)
        first_process = first_pc.process
        last_process = last_pc.process
        nexts = first_process.next_processes()
        prevs = last_process.previous_processes()
        self.assertTrue(first_process in prevs)
        self.assertTrue(last_process in nexts)
        
        order = last_pc.order
        processes = order.all_processes()
        self.assertEqual(len(processes), 4)
        
    def test_two_order_items_with_same_resource_type(self):
        due_date = datetime.date.today()
        order = Order(
            name="test",
            due_date=due_date,
        )
        order.save()
        unit = self.wf_recipe.unit
        et = self.wf_recipe.change_event_type
        stage = self.changeable.staged_process_type_sequence()[-1]
        commitment1 = order.add_commitment(
            resource_type=self.changeable,
            quantity=Decimal("2000"),
            event_type=et,
            unit=unit,
            description="Test",
            stage=stage,
        )
        commitment1.generate_producing_process(self.user, [], explode=True)
        due = due_date + datetime.timedelta(days=10)
        commitment2 = order.add_commitment(
            resource_type=self.changeable,
            quantity=Decimal("4000"),
            event_type=et,
            unit=unit,
            description="Test",
            stage=stage,
            due=due,
        )
        commitment2.generate_producing_process(self.user, [], explode=True)

        process1 = commitment1.process
        process2 = commitment2.process
        processes = order.all_processes()
        self.assertEqual(len(processes), 4)
        self.assertEqual(len(process1.previous_processes()), 1)
        self.assertEqual(len(process2.previous_processes()), 1)
        chain = commitment1.process_chain()
        self.assertEqual(len(chain), 2)
        chain = commitment2.process_chain()
        self.assertEqual(len(chain), 2)
        #import pdb; pdb.set_trace()
        
    def test_create_order_item(self):
        due_date = datetime.date.today()
        order = Order(
            name="test",
            due_date=due_date,
        )
        order.save()
        oi = order.create_order_item(
            resource_type=self.parent,
            quantity=Decimal("1.0"),
            user=self.user,
        )
        #import pdb; pdb.set_trace()
        #todo: needs assertions
            
            