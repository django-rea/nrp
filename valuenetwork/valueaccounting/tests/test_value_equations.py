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
        #import pdb; pdb.set_trace()
        
    def test_setup(self):
        
        parent = self.recipe.parent
        parent_pt = parent.main_producing_process_type()
        import pdb; pdb.set_trace()
