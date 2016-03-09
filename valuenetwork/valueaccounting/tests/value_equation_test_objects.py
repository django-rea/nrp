import datetime
from decimal import *

from django.test import TestCase
from django.test import Client

from valuenetwork.valueaccounting.models import *

from valuenetwork.valueaccounting.tests.objects_for_testing import *

"""
Hi pri:
Resource contribution behind use event
needs:
output resource
process
input use event
resource used with value_per_unit_of_use
resource contribution (of resource used?)

"""

class ValueEquationRecipe(Recipe):
    def __init__(self, 
        usable=None, 
        worker=None, 
        contributor=None,
        use_event_type=None,
        work_event_type=None,
        contribution_event_type=None,
        hours_unit=None,
    ):
        Recipe.__init__(
            self,
            parent=None, 
            child=None, 
            grandchild=None,
            unit=None,
            production_event_type=None,
            consumption_event_type=None,
            )
        self.usable = usable
        self.worker = worker
        self.contributor = contributor
        self.use_event_type = use_event_type
        self.work_event_type = work_event_type
        self.contribution_event_type = contribution_event_type
        self.hours_unit = hours_unit

        if not usable:
            self.usable = EconomicResourceType(
                name="usable",
                value_per_unit_of_use=Decimal("10"),
                )
            self.usable.save()

        agent_type = AgentType(
            name="Active",
            )
        agent_type.save()

        if not worker:
            self.worker = EconomicAgent(
            name="worker",
            nick="worker",
            agent_type=agent_type,
            )
            self.worker.save()

        if not contributor:
            self.contributor = EconomicAgent(
            name="contributor",
            nick="contributor",
            agent_type=agent_type,
            )
            self.contributor.save()

        if not use_event_type:
            try:
                et = EventType.objects.get(name="Resource use")
                self.use_event_type = et
            except EventType.DoesNotExist:
                self.use_event_type = EventType(
                name="Resource use",
                label="uses",
                relationship="use",
                resource_effect="=",
                )
                self.use_event_type.save()

        if not work_event_type:
            try:
                et = EventType.objects.get(name="Time Contribution")
                self.work_event_type = et
            except EventType.DoesNotExist:
                self.work_event_type = EventType(
                name="Time Contribution",
                label="work",
                relationship="work",
                resource_effect="=",
                )
                self.work_event_type.save()
                
        if not contribution_event_type:
            try:
                et = EventType.objects.get(name="Resource Contribution")
                self.contribution_event_type = et
            except EventType.DoesNotExist:
                self.contribution_event_type = EventType(
                name="Resource Contribution",
                label="resource",
                relationship="resource",
                resource_effect="+",
                )
                self.contribution_event_type.save()
                
        if not hours_unit:
            self.hours_unit = Unit(
                unit_type="time",
                abbrev="Hr",
                name="hour",
            )
            self.unit.save()
                
        parent_pt = self.parent.main_producing_process_type()
        usable_input = ProcessTypeResourceType(
            process_type=parent_pt,
            resource_type=self.usable,
            event_type=self.use_event_type,
            quantity=Decimal("1"),
            unit_of_quantity=self.hours_unit,
        )
        usable_input.save()
                
"""                
class Agents(object):
    def __init__(self, 
    

class ResourceTypes(object):
    def __init__(self, 
    
    
class Resources(object):
    def __init__(self, 
    

class EventTypes(object):
    def __init__(self, 
    
    
class Processes(object):
    def __init__(self, 
    
    
class Events(object):
    def __init__(self, 
    
    
    
class ContributionBase1(object):
    def __init__(self, 
    
    
class ContributionBase2(object):
    def __init__(self, 
    
    
class SaleBase1(object):
    def __init__(self, 
    
    
class SaleBase2(object):
    def __init__(self, 
    
    
class DistributionBase1(object):
    def __init__(self, 
    
    
class DistributionBase3(object):
    def __init__(self, 
"""