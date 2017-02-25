from django.contrib import admin
from django_rea.valueaccounting.models import *
from django_rea.valueaccounting.actions import export_as_csv

admin.site.add_action(export_as_csv, 'export_selected objects')

admin.site.register(Unit)
admin.site.register(AgentType)
#admin.site.register(CachedEventSummary)
admin.site.register(UseCase)
admin.site.register(AccountingReference)
admin.site.register(AgentResourceRoleType)
admin.site.register(AgentResourceRole)
admin.site.register(Location)
admin.site.register(UseCaseEventType)
admin.site.register(HomePageLayout)


class HelpAdmin(admin.ModelAdmin):
    list_display = ('page',)

admin.site.register(Help, HelpAdmin)

class ResourceTypeSpecialPriceAdmin(admin.ModelAdmin):
    list_display = ('resource_type', 'identifier', 'description', 'price_per_unit')
    
admin.site.register(ResourceTypeSpecialPrice, ResourceTypeSpecialPriceAdmin)

class ResourceClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'description',)
    
admin.site.register(ResourceClass, ResourceClassAdmin)

class ValueEquationBucketInline(admin.TabularInline):
    model = ValueEquationBucket
    fk_name = 'value_equation'
    fields = ('sequence', 'name', 'percentage', 'distribution_agent', 'filter_method')

class ValueEquationAdmin(admin.ModelAdmin):
    list_display = ('name', 'context_agent', 'description', 'percentage_behavior', 'live')
    inlines = [ ValueEquationBucketInline, ]

admin.site.register(ValueEquation, ValueEquationAdmin)

class ValueEquationBucketRuleInline(admin.TabularInline):
    model = ValueEquationBucketRule
    fk_name = 'value_equation_bucket'
    fields = ('event_type', 'filter_rule', 'division_rule', 'claim_rule_type', 'claim_creation_equation')
        
class ValueEquationBucketAdmin(admin.ModelAdmin):
    list_display = ('value_equation', 'sequence', 'name', 'percentage' )
    inlines = [ ValueEquationBucketRuleInline, ]

admin.site.register(ValueEquationBucket, ValueEquationBucketAdmin)

class DistributionValueEquationAdmin(admin.ModelAdmin):
    list_display = ('distribution_date', 'exchange', 'value_equation_link')

admin.site.register(DistributionValueEquation, DistributionValueEquationAdmin)
    
class ClaimEventInline(admin.TabularInline):
    model = ClaimEvent
    fk_name = 'claim'
    fields = ('event', 'claim_event_date', 'value', 'unit_of_value', 'event_effect')
  
class ClaimAdmin(admin.ModelAdmin):
    date_hierarchy = 'claim_date'
    list_display = ('claim_date', 'has_agent', 'against_agent', 'value_equation_bucket_rule', 'context_agent', 'original_value', 'value', 'unit_of_value', 'claim_creation_equation')
    inlines = [ ClaimEventInline, ]

admin.site.register(Claim, ClaimAdmin)
  
class ClaimEventAdmin(admin.ModelAdmin):
    date_hierarchy = 'claim_event_date'
    list_display = ('claim_event_date', 'event', 'claim', 'value', 'unit_of_value', 'event_effect')

admin.site.register(ClaimEvent, ClaimEventAdmin)

class TransferEconomicEventInline(admin.TabularInline):
    model = EconomicEvent
    fk_name = 'transfer'
    fields = ('event_type', 'event_date', 'resource_type', 'exchange_stage', 'quantity', 'unit_of_quantity', 'value', 'unit_of_value', 'from_agent', 'to_agent')
 
class TransferAdmin(admin.ModelAdmin):
    date_hierarchy = 'transfer_date'
    list_display = ('id', 'transfer_date', 'transfer_type', 'name', 'context_agent')
    list_filter = ['transfer_type']
    inlines = [ TransferEconomicEventInline ]

admin.site.register(Transfer, TransferAdmin)

class TransferInline(admin.TabularInline):
    model = Transfer
    fk_name = 'exchange'
    fields = ('name', 'transfer_type', 'transfer_date')
    
class TransferTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'sequence', 'exchange_type', )
    list_filter = ['exchange_type']

admin.site.register(TransferType, TransferTypeAdmin)

    
class EconomicEventInline(admin.TabularInline):
    model = EconomicEvent
    fk_name = 'exchange'
    fields = ('event_type', 'event_date', 'resource_type', 'exchange_stage', 'quantity', 'unit_of_quantity', 'value', 'unit_of_value', 'from_agent', 'to_agent')
   
class ExchangeAdmin(admin.ModelAdmin):
    date_hierarchy = 'start_date'
    list_display = ('id', 'start_date', 'use_case', 'name', 'context_agent', 'exchange_type')
    list_filter = ['use_case', 'exchange_type']
    inlines = [ TransferInline, EconomicEventInline ]

admin.site.register(Exchange, ExchangeAdmin)

class DistEconomicEventInline(admin.TabularInline):
    model = EconomicEvent
    fk_name = 'distribution'
    fields = ('event_type', 'event_date', 'resource_type', 'exchange_stage', 'quantity', 'unit_of_quantity', 'value', 'unit_of_value', 'from_agent', 'to_agent')
 
class DistributionAdmin(admin.ModelAdmin):
    date_hierarchy = 'distribution_date'
    list_display = ('id', 'distribution_date', 'name', 'context_agent', 'value_equation')
    inlines = [ DistEconomicEventInline ]

admin.site.register(Distribution, DistributionAdmin)

class IncomeEventDistributionAdmin(admin.ModelAdmin):
    date_hierarchy = 'distribution_date'
    list_display = ('distribution_date', 'distribution', 'income_event', 'quantity', 'unit_of_quantity')
    
admin.site.register(IncomeEventDistribution, IncomeEventDistributionAdmin)
    
class AgentAssociationTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'label', 'inverse_label', 'description', 'association_behavior')
    list_filter = ['association_behavior',]

admin.site.register(AgentAssociationType, AgentAssociationTypeAdmin)


class FacetValueInline(admin.TabularInline):
    model = FacetValue
    

class FacetAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'value_list')
    inlines = [ FacetValueInline, ]

admin.site.register(Facet, FacetAdmin)


class PatternFacetInline(admin.TabularInline):
    model = PatternFacetValue
    fields = ('event_type', 'facet_value')


class PatternUseCaseInline(admin.TabularInline):
    model = PatternUseCase
    extra = 1
    

class ProcessPatternAdmin(admin.ModelAdmin):
    list_display = ('name', 'use_case_list')
    inlines = [ PatternFacetInline, PatternUseCaseInline]

admin.site.register(ProcessPattern, ProcessPatternAdmin)


class AgentUserInline(admin.TabularInline):
    model = AgentUser


class EconomicAgentAdmin(admin.ModelAdmin):
    list_display = ('nick', 'name', 'agent_type', 'url', 'address', 'email', 'slug', 'created_date')
    list_filter = ['agent_type',]
    search_fields = ['name', 'address']
    inlines = [ AgentUserInline, ]
    
admin.site.register(EconomicAgent, EconomicAgentAdmin)

class AgentAssociationAdmin(admin.ModelAdmin):
    list_display = ('representation', 'association_type', 'state', 'is_associate', 'has_associate')
    list_filter = ['association_type', 'state', 'is_associate', 'has_associate']
    
admin.site.register(AgentAssociation, AgentAssociationAdmin)

class ResourceTypeFacetInline(admin.TabularInline):
    model = ResourceTypeFacetValue

class EconomicResourceTypeAdmin(admin.ModelAdmin):
    list_display = ('label', 'name', 'resource_class', 'unit', 'unit_of_use', 'description', 'substitutable', 'facet_list')
    list_filter = ['facets__facet_value']
    search_fields = ['name',]
    list_editable = ['unit', 'unit_of_use', 'substitutable', 'resource_class',]
    inlines = [ ResourceTypeFacetInline, ]
    
admin.site.register(EconomicResourceType, EconomicResourceTypeAdmin)


class AgentResourceTypeAdmin(admin.ModelAdmin):
    list_display = ('agent', 'resource_type', 'score', 'event_type')
    list_filter = ['event_type', 'agent', 'resource_type']
    
admin.site.register(AgentResourceType, AgentResourceTypeAdmin)


class ProcessTypeResourceTypeAdmin(admin.ModelAdmin):
    list_display = ('process_type', 'resource_type', 'event_type', 'quantity', 'unit_of_quantity')
    list_filter = ['event_type', 'process_type', 'resource_type']
    search_fields = ['process_type__name','resource_type__name',]
    
admin.site.register(ProcessTypeResourceType, ProcessTypeResourceTypeAdmin)


class ProcessTypeResourceTypeInline(admin.TabularInline):
    model = ProcessTypeResourceType
    fk_name = "process_type"


class ProcessTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'context_agent' )
    list_filter = ['context_agent',]
    search_fields = ['name',]
    inlines = [ ProcessTypeResourceTypeInline, ]

admin.site.register(ProcessType, ProcessTypeAdmin)


class TransferTypeInline(admin.TabularInline):
    model = TransferType
    fk_name = "exchange_type"

class ExchangeTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'use_case' )
    list_filter = ['use_case']
    search_fields = ['name',]
    inlines = [ TransferTypeInline, ]

admin.site.register(ExchangeType, ExchangeTypeAdmin)


class EventTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'label', 'inverse_label', 'related_to', 'relationship', 'resource_effect', 'unit_type' )
    list_filter = ['resource_effect', 'related_to', 'relationship',]
    list_editable = ['label', 'inverse_label', 'related_to', 'relationship']

admin.site.register(EventType, EventTypeAdmin)


class AgentRoleInline(admin.TabularInline):
    model = AgentResourceRole
    fk_name = 'resource'
    fields = ('role', 'agent')
    
class EconomicResourceAdmin(admin.ModelAdmin):
    list_display = ('id', 'identifier', 'resource_type', 'quantity', 'unit_of_quantity', 'quality', 'notes')
    list_filter = ['resource_type', 'author']
    search_fields = ['identifier', 'resource_type__name']
    date_hierarchy = 'created_date'
    inlines = [ AgentRoleInline, ]

admin.site.register(EconomicResource, EconomicResourceAdmin)


class CommitmentInline(admin.TabularInline):
    model = Commitment


class OrderItemInline(admin.TabularInline):
    model = Commitment
    verbose_name = "order item"
    verbose_name_plural = "order items"
    fk_name = 'order'
    fields = ('event_type', 'due_date', 'resource_type', 'quantity', 'unit_of_quantity', 'process')


class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'provider', 'receiver', 'description','due_date' )
    inlines = [ OrderItemInline, ]

admin.site.register(Order, OrderAdmin)


class EventInline(admin.TabularInline):
    model = EconomicEvent
    fk_name = 'process'
    fields = ('event_type', 'event_date', 'resource_type', 'resource', 'from_agent', 'to_agent', 'quantity', 'unit_of_quantity')

class ProcessAdmin(admin.ModelAdmin):
    date_hierarchy = 'start_date'
    list_display = ('name', 'start_date', 'end_date', 'finished', 'process_type', 'context_agent')
    list_filter = ['process_type', 'finished', 'context_agent']
    search_fields = ['name', 'process_type__name', 'context_agent__name']
    inlines = [ CommitmentInline, EventInline]
    
admin.site.register(Process, ProcessAdmin)


class CommitmentAdmin(admin.ModelAdmin):
    date_hierarchy = 'due_date'
    list_display = ('resource_type', 'quantity', 'unit_of_quantity', 'event_type', 'due_date', 'finished', 'from_agent', 'to_agent', 'process', 'exchange', 'context_agent', 'order', 'independent_demand',  
        'description')
    list_filter = ['independent_demand', 'event_type', 'resource_type', 'from_agent', 'context_agent']
    search_fields = ['event_type__name', 'from_agent__name', 'to_agent__name', 'resource_type__name']
    
admin.site.register(Commitment, CommitmentAdmin)

class ClaimEvent2Inline(admin.TabularInline):
    model = ClaimEvent
    fk_name = 'event'
    fields = ('claim', 'claim_event_date', 'value', 'unit_of_value', 'event_effect')
    
class EconomicEventAdmin(admin.ModelAdmin):
    date_hierarchy = 'event_date'
    list_display = ('event_type', 'event_date', 'from_agent', 'to_agent', 'context_agent', 'process', 'exchange',
        'resource_type', 'resource', 'quantity', 'unit_of_quantity', 'description', 'url', 'quality')
    list_filter = ['event_type', 'context_agent', 'resource_type', 'from_agent', ]
    search_fields = ['description', 'process__name', 'event_type__name', 'from_agent__name', 'to_agent__name', 
        'resource_type__name',]
    list_editable = ['event_date', 'context_agent']
    inlines = [ ClaimEvent2Inline, ]
    
admin.site.register(EconomicEvent, EconomicEventAdmin)


#class CompensationAdmin(admin.ModelAdmin):
#    list_display = ('initiating_event', 'compensating_event', 'compensation_date', 'compensating_value')
#    search_fields = ['initiating_event__from_agent__name', 'initiating_event__to_agent__name']
    
#admin.site.register(Compensation, CompensationAdmin)


