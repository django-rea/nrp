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
        
        self.consumable_rt = EconomicResourceType(
            name="consumable type",
            unit=self.unit,
            )
        self.consumable_rt.save()
        
        self.community_rt = EconomicResourceType(
            name="community purchased type",
            unit_of_use=self.hours_unit,
            unit=self.unit,
            )
        self.community_rt.save()
        
        self.community_resource = EconomicResource(
            resource_type=self.community_rt,
            identifier="community resource",
            value_per_unit_of_use=Decimal("50"),
            )
        self.community_resource.save()
        
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
        
        self.community_input = ProcessTypeResourceType(
            process_type=child_pt,
            resource_type=self.community_rt,
            event_type=self.use_event_type,
            quantity=Decimal("1"),
            unit_of_quantity=self.hours_unit,
        )
        self.community_input.save()
        
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
            name="Resource Contribution",
            use_case=uc,
            )
        xt.save()
        
        tt = TransferType(
            name="Resource Contribution",
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
            name="resource contribution",
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
        
        self.consumable = EconomicResource(
            resource_type=self.consumable_rt,
            identifier="consumable",
            )
        self.consumable.save()
        
        consumable_input = ProcessTypeResourceType(
            process_type=child_pt,
            resource_type=self.consumable_rt,
            event_type=self.consumption_event_type,
            quantity=Decimal("1"),
            unit_of_quantity=self.unit,
        )
        consumable_input.save()
        
        xt = ExchangeType(
            name="Resource Purchase",
            use_case=uc,
            )
        xt.save()
        
        rtt = TransferType(
            name="Resource Receipt",
            exchange_type=xt,
            can_create_resource=True,
            receive_agent_is_context=True,
            )
        rtt.save()
        
        ptt = TransferType(
            name="Payment",
            exchange_type=xt,
            is_reciprocal=True,
            is_currency=True,
            receive_agent_is_context=False,
            )
        ptt.save()
        
        ex = Exchange(
            use_case=uc,
            exchange_type=xt,
            context_agent=ca,
            start_date=datetime.date.today(),
            )
        ex.save()
        
        receiving_xfer = Transfer(
            name="consumable receipt",
            transfer_type=rtt,
            exchange=ex,
            context_agent=ca,
            transfer_date=datetime.date.today(),
            )
        receiving_xfer.save()
        
        paying_xfer = Transfer(
            name="consumable payment",
            transfer_type=ptt,
            exchange=ex,
            context_agent=ca,
            transfer_date=datetime.date.today(),
            )
        paying_xfer.save()
        
        supplier = EconomicAgent(
            name="supplier",
            nick="supplier",
            agent_type=agent_type,
            is_context=True,
            )
        supplier.save()

        receiving_event = EconomicEvent(
            event_type=self.contribution_event_type,
            from_agent=supplier,
            to_agent=ca,
            event_date=datetime.date.today(),
            resource_type=self.consumable_rt,
            resource=self.consumable,
            exchange=ex,
            transfer=receiving_xfer,
            context_agent=ca,
            quantity=Decimal("2.0"),
            unit_of_quantity=self.unit,
            value=Decimal("100"),
            )
        receiving_event.save()
        
        money_unit = Unit(
                unit_type="value",
                abbrev="DOL",
                name="dollar",
        )
        money_unit.save()
        
        money_rt = EconomicResourceType(
            name="money",
            unit=money_unit
            )
        money_rt.save() 
        
        
        try:
            et = EventType.objects.get(name="Give")
            payment_event_type = et
        except EventType.DoesNotExist:
            payment_event_type = EventType(
            name="Give",
            label="gives",
            relationship="give",
            resource_effect="-",
            )
            payment_event_type.save()
        
        paying_event = EconomicEvent(
            event_type=payment_event_type,
            from_agent=self.contributor,
            to_agent=supplier,
            event_date=datetime.date.today(),
            resource_type=money_rt,
            exchange=ex,
            transfer=paying_xfer,
            context_agent=ca,
            quantity=Decimal("100.0"),
            unit_of_quantity=money_unit,
            value=Decimal("100"),
            is_contribution=True,
            )
        paying_event.save()
        
        community_ex = Exchange(
            use_case=uc,
            exchange_type=xt,
            context_agent=ca,
            start_date=datetime.date.today(),
            )
        community_ex.save()
        
        community_receiving_xfer = Transfer(
            transfer_type=rtt,
            exchange=community_ex,
            context_agent=ca,
            transfer_date=datetime.date.today(),
            )
        community_receiving_xfer.save()
        
        community_receiving_event = EconomicEvent(
            event_type=self.contribution_event_type,
            from_agent=supplier,
            to_agent=ca,
            event_date=datetime.date.today(),
            resource_type=self.community_rt,
            resource=self.community_resource,
            exchange=community_ex,
            transfer=community_receiving_xfer,
            context_agent=ca,
            quantity=Decimal("1.0"),
            unit_of_quantity=self.unit,
            value=Decimal("1000"),
            )
        community_receiving_event.save()
        
        community_paying_xfer = Transfer(
            name="community payment",
            transfer_type=ptt,
            exchange=community_ex,
            context_agent=ca,
            transfer_date=datetime.date.today(),
            )
        community_paying_xfer.save()
        
        
        virtual_rt = EconomicResourceType(
            name="virtual account",
            unit=money_unit
            )
        virtual_rt.save()
        
        virtual_account = EconomicResource(
            resource_type=virtual_rt,
            identifier="test account",
            )
        virtual_account.save()
        
        # contributors and
        #   contributions to virtual account
        va_contributor1 = EconomicAgent(
            name="va contributor1",
            nick="vacontributor1",
            agent_type=agent_type,
            )
        va_contributor1.save()
        
        va_contributor2 = EconomicAgent(
            name="va contributor2",
            nick="vacontributor2",
            agent_type=agent_type,
            )
        va_contributor2.save()

        #cash contributions into virtual account

        #TransferType(
        #Transfer(s
        #Contributions event (just a receive)
        
        try:
            iuc = UseCase.objects.get(name="Internal Exchange")
        except UseCase.DoesNotExist:
            iuc = UseCase(
                name="Internal Exchange",
                identifier="intrnl_xfer",
                )
            iuc.save()
        
        finxt = ExchangeType(
            name="Financial Contribution",
            use_case=iuc,
            )
        finxt.save()
        
        finex = Exchange(
            use_case=iuc,
            exchange_type=finxt,
            context_agent=ca,
            start_date=datetime.date.today(),
            )
        finex.save()
        
        fintt = TransferType(
            name="Financial Contribution",
            exchange_type=finxt,
            is_currency=True,
            receive_agent_is_context=True,
            )
        fintt.save()
        
        finxfer1 = Transfer(
            name="financial contribution 1",
            transfer_type=fintt,
            exchange=finex,
            context_agent=ca,
            transfer_date=datetime.date.today(),
            )
        finxfer1.save()
        
        finxfer2 = Transfer(
            name="financial contribution 2",
            transfer_type=fintt,
            exchange=finex,
            context_agent=ca,
            transfer_date=datetime.date.today(),
            )
        finxfer2.save()
        

        finevt1 = EconomicEvent(
            event_type=self.contribution_event_type,
            from_agent=va_contributor1,
            to_agent=ca,
            event_date=datetime.date.today(),
            # ???
            resource_type=money_rt,
            resource=virtual_account,
            exchange=finex,
            transfer=finxfer1,
            context_agent=ca,
            quantity=Decimal("600.0"),
            unit_of_quantity=money_unit,
            value=Decimal("600"),
            is_contribution=True,
            )
        finevt1.save()
        
        finevt2 = EconomicEvent(
            event_type=self.contribution_event_type,
            from_agent=va_contributor2,
            to_agent=ca,
            event_date=datetime.date.today(),
            # ???
            resource_type=money_rt,
            resource=virtual_account,
            exchange=finex,
            transfer=finxfer2,
            context_agent=ca,
            quantity=Decimal("400.0"),
            unit_of_quantity=money_unit,
            value=Decimal("400"),
            is_contribution=True,
            )
        finevt2.save()

        community_paying_event = EconomicEvent(
            event_type=payment_event_type,
            # ???
            from_agent=ca,
            to_agent=supplier,
            event_date=datetime.date.today(),
            resource_type=money_rt,
            resource=virtual_account,
            exchange=community_ex,
            transfer=community_paying_xfer,
            context_agent=ca,
            quantity=Decimal("1000.0"),
            unit_of_quantity=money_unit,
            value=Decimal("1000"),
            )
        community_paying_event.save()
        
        self.value_equation = ValueEquation(
            name="ve1",
            context_agent=ca,
            )
        self.value_equation.save()
        
        supplier2 = EconomicAgent(
            name="supplier2",
            nick="supplier2",
            agent_type=agent_type,
            is_context=True,
            )
        supplier.save()
        
        expense_rt = EconomicResourceType(
            name="expense type",
            unit=self.unit,
            )
        expense_rt.save()
        
        receiving_event2 = EconomicEvent(
            event_type=self.contribution_event_type,
            from_agent=supplier2,
            to_agent=ca,
            event_date=datetime.date.today(),
            resource_type=expense_rt,
            exchange=ex,
            transfer=receiving_xfer,
            context_agent=ca,
            quantity=Decimal("1.0"),
            unit_of_quantity=self.unit,
            value=Decimal("20"),
            )
        receiving_event2.save()
        
        expense_paying_xfer = Transfer(
            name="expense payment",
            transfer_type=ptt,
            exchange=ex,
            context_agent=ca,
            transfer_date=datetime.date.today(),
            )
        expense_paying_xfer.save()
        
        paying_event2 = EconomicEvent(
            event_type=payment_event_type,
            from_agent=self.contributor,
            to_agent=supplier2,
            event_date=datetime.date.today(),
            resource_type=money_rt,
            exchange=ex,
            transfer=expense_paying_xfer,
            context_agent=ca,
            quantity=Decimal("20.0"),
            unit_of_quantity=money_unit,
            value=Decimal("20"),
            is_contribution=True,
            )
        paying_event2.save()
        
        """
        bucket = ValueEquationBucket(
            name="bucket0",
            value_equation=self.value_equation,
            filter_method="order",
            percentage=Decimal("50"),
            )
        bucket.save()
        
        rule = ValueEquationBucketRule(
            value_equation_bucket=bucket,
            event_type=self.contribution_event_type,
            division_rule="percentage",
            claim_rule_type="debt-like",
            claim_creation_equation="value",
            filter_rule= "{}",
            )
        rule.save()
        """
        
        bucket = ValueEquationBucket(
            name="bucket1",
            sequence=1,
            value_equation=self.value_equation,
            filter_method="order",
            percentage=Decimal("100"),
            )
        bucket.save()
        
        rule = ValueEquationBucketRule(
            value_equation_bucket=bucket,
            event_type=self.contribution_event_type,
            division_rule="percentage",
            claim_rule_type="debt-like",
            claim_creation_equation="value",
            filter_rule= "{}",
            )
        rule.save()
        
        
        rule = ValueEquationBucketRule(
            value_equation_bucket=bucket,
            event_type=self.work_event_type,
            division_rule="percentage",
            claim_rule_type="debt-like",
            claim_creation_equation="quantity * 25",
            filter_rule= "{}",
            )
        rule.save()
        
        rule = ValueEquationBucketRule(
            value_equation_bucket=bucket,
            event_type=self.production_event_type,
            division_rule="percentage",
            claim_rule_type="debt-like",
            claim_creation_equation="value",
            filter_rule= "{}",
            )
        rule.save()
        
        rule = ValueEquationBucketRule(
            value_equation_bucket=bucket,
            event_type=payment_event_type,
            division_rule="percentage",
            claim_rule_type="debt-like",
            claim_creation_equation="value",
            filter_rule= "{}",
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