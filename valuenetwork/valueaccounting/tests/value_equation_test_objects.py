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
        
        if not hours_unit:
            self.hours_unit = Unit(
                unit_type="time",
                abbrev="Hr",
                name="hour",
            )
            self.hours_unit.save()
            
        agent_type = AgentType(
            name="Active",
            )
        agent_type.save()
            
        ca = EconomicAgent(
            name="context",
            nick="context",
            agent_type=agent_type,
            is_context=True,
            )
        ca.save()
        
        urt = EconomicResourceType(
            name="usable type",
            unit_of_use=self.hours_unit,
            unit=self.unit,
            )
        urt.save()

        if not usable:
            self.usable = EconomicResource(
                resource_type=urt,
                identifier="usable",
                value_per_unit_of_use=Decimal("10"),
                )
            self.usable.save()

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
                
        parent_pt = self.parent.main_producing_process_type()
        parent_pt.context_agent = ca
        parent_pt.save()
        
        child_pt = self.child.main_producing_process_type()
        child_pt.context_agent = ca
        child_pt.save()
        
        usable_input = ProcessTypeResourceType(
            process_type=parent_pt,
            resource_type=urt,
            event_type=self.use_event_type,
            quantity=Decimal("1"),
            unit_of_quantity=self.hours_unit,
        )
        usable_input.save()
        
        if not contribution_event_type:
            try:
                et = EventType.objects.get(name="Receive")
                self.contribution_event_type = et
            except EventType.DoesNotExist:
                self.contribution_event_type = EventType(
                name="Receive",
                label="receives",
                relationship="receive",
                resource_effect="+",
                )
                self.contribution_event_type.save()
                
        try:
            uc = UseCase.objects.get(name="Incoming Exchange")
        except UseCase.DoesNotExist:
            uc = UseCase(
                name="Incoming Exchange",
                identifier="supply_xfer",
                )
            uc.save()
            
        xt = ExchangeType(
            name="Material Contribution",
            use_case=uc,
            )
        xt.save()
        
        tt = TransferType(
            name="Material Contribution",
            exchange_type=xt,
            is_contribution=True,
            can_create_resource=True,
            receive_agent_is_context=True,
            )
        tt.save()
        
        ex = Exchange(
            use_case=uc,
            exchange_type=xt,
            context_agent=ca,
            start_date=datetime.date.today(),
            )
        ex.save()
        
        xfer = Transfer(
            transfer_type=tt,
            exchange=ex,
            context_agent=ca,
            transfer_date=datetime.date.today(),
            )
        xfer.save()
        
        event = EconomicEvent(
            event_type=self.contribution_event_type,
            from_agent=self.contributor,
            to_agent=ca,
            event_date=datetime.date.today(),
            resource_type=urt,
            resource=self.usable,
            exchange=ex,
            transfer=xfer,
            context_agent=ca,
            quantity=Decimal("1.0"),
            unit_of_quantity=self.unit,
            value=Decimal("100"),
            is_contribution=True,
            )
        event.save()
        
        self.value_equation = ValueEquation(
            name="ve1",
            context_agent=ca,
            )
        self.value_equation.save()
        
        bucket = ValueEquationBucket(
            name="bucket0",
            value_equation=self.value_equation,
            filter_method="process",
            percentage=Decimal("50"),
            )
        bucket.save()
        
        rule = ValueEquationBucketRule(
            value_equation_bucket=bucket,
            event_type=self.contribution_event_type,
            division_rule="percentage",
            claim_rule_type="debt-like",
            claim_creation_equation="value",
            )
        rule.save()
        
        bucket = ValueEquationBucket(
            name="bucket1",
            sequence=1,
            value_equation=self.value_equation,
            filter_method="process",
            percentage=Decimal("50"),
            )
        bucket.save()
        
        rule = ValueEquationBucketRule(
            value_equation_bucket=bucket,
            event_type=self.work_event_type,
            division_rule="percentage",
            claim_rule_type="debt-like",
            claim_creation_equation="quantity * 25",
            )
        rule.save()
        
            
        # need to get work and use events connected to processes
        # do here or in test_value_equations?
        
                
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