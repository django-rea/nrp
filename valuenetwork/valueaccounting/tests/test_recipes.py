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

class RecipeTest(WebTest):

    """Testing recipes
    """

    def setUp(self):

        recipe = Recipe()
        self.parent = recipe.parent
        self.child = recipe.child
        self.grandchild = recipe.grandchild

        
    def test_view_recipe(self):
        """Test extended_bill view            
        """

        url = ('/%s/%s/' % ('accounting/xbomfg', self.parent.id))
        response = self.app.get(url , user='alice')
        nodes = response.context['nodes']
        node0 = nodes[0]
        assert node0.depth == 1
        node1 = nodes[1]
        assert node1.depth == 2
        assert node1.xbill_object() == self.child
        node2 = nodes[2]
        assert node2.depth == 3
        node3 = nodes[3]
        assert node3.depth == 4
        assert node3.xbill_object() == self.grandchild

