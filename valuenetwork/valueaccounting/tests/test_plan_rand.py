import datetime
from decimal import *

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import Client

from webtest import AppError, TestApp

from django_webtest import WebTest

from valuenetwork.valueaccounting.models import *
from valuenetwork.valueaccounting.views import *
from valuenetwork.valueaccounting.utils import *
from .objects_for_testing import *

class PlanRandTest(WebTest):

    """Testing planning R&D work
    """

    def setUp(self):

        facets = Facets()
        self.electronic_pattern = facets.electronic_pattern
        electronic_domain = facets.domain.values.get(value="Electronical")
        self.project = Project(name="Test Project")
        self.project.save()
        recipe = Recipe()
        self.parent = recipe.parent
        rtfv = ResourceTypeFacetValue(
            resource_type=self.parent,
            facet_value=electronic_domain,
        )
        rtfv.save()


    def test_process_selections(self):
        """Test process_selections view

            and subsequent dependent demand explosion
            
        """
        response = self.app.get('/accounting/process-selections/1/' , user='alice')
        form = response.form
        patterns = form["pattern"].options
        projects = form["project"].options
        self.assertEqual(len(patterns), 4)
        self.assertEqual(len(projects), 1)
        form["pattern"] = unicode(self.electronic_pattern.id)
        form["project"] = unicode(self.project.id)
        response = form.submit("get-related")
        form = response.form
        form["produces~parent"].checked = True
        response = form.submit("create-process")
        process = self.parent.producing_commitments()[0].process
        child_input = process.incoming_commitments()[0]
        self.assertEqual(child_input.quantity, Decimal("2"))
        rt = child_input.resource_type
        child_output=rt.producing_commitments()[0]
        self.assertEqual(child_output.quantity, Decimal("2"))
        child_process=child_output.process
        grandchild_input = child_process.incoming_commitments()[0]
        self.assertEqual(grandchild_input.quantity, Decimal("6"))
        #import pdb; pdb.set_trace()

    def test_complete_recipe(self):
        """todo"""
        pass
        
        
        
