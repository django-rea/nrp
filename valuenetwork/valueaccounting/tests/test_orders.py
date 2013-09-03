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

        facets = Facets()
        self.electronic_pattern = facets.electronic_pattern
        self.full_pattern = facets.full_pattern
        electronic_domain = facets.domain.values.get(value="Electronical")
        source_us = facets.source.values.get(value="Us")
        self.project = Project(name="Test Project")
        self.project.save()
        recipe = Recipe()
        self.parent = recipe.parent
        self.child = recipe.child
        self.grandchild = recipe.grandchild

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

        puc = PatternUseCase(
            pattern=order_pattern,
            use_case="cust_orders",
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
        
    def test_create_order(self):
        """Test create_order view

            and subsequent dependent demand explosion
            
        """
       
        response = self.app.get('/accounting/create-order/' , user='alice')
        form = response.form
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

