from django.contrib import admin
from valuenetwork.valueaccounting.models import *
from valuenetwork.valueaccounting.actions import export_as_csv

admin.site.add_action(export_as_csv, 'export_selected objects')

admin.site.register(Unit)
admin.site.register(AgentType)
#admin.site.register(Stage)


class HelpAdmin(admin.ModelAdmin):
    list_display = ('page',)

admin.site.register(Help, HelpAdmin)


class FacetValueInline(admin.TabularInline):
    model = FacetValue
    

class FacetAdmin(admin.ModelAdmin):
    list_display = ('name', 'value_list')
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


class ResourceRelationshipAdmin(admin.ModelAdmin):
    list_display = ('name', 'inverse_name', 'related_to', 'direction', 'materiality', 'event_type', 'unit')
    list_filter = ['materiality', 'related_to', 'direction']
    list_editable = ['event_type',]

admin.site.register(ResourceRelationship, ResourceRelationshipAdmin)


class AgentUserInline(admin.TabularInline):
    model = AgentUser


class EconomicAgentAdmin(admin.ModelAdmin):
    list_display = ('nick', 'name', 'agent_type', 'url', 'address', 'email', 'created_date')
    list_filter = ['agent_type',]
    search_fields = ['name', 'address']
    inlines = [ AgentUserInline, ]
    
admin.site.register(EconomicAgent, EconomicAgentAdmin)

class ResourceTypeFacetInline(admin.TabularInline):
    model = ResourceTypeFacetValue

class EconomicResourceTypeAdmin(admin.ModelAdmin):
    list_display = ('label', 'name', 'category', 'rate', 'unit', 'unit_of_use', 'description', 'facet_list')
    list_filter = ['facets__facet_value']
    search_fields = ['name',]
    list_editable = ['unit', 'unit_of_use']
    inlines = [ ResourceTypeFacetInline, ]
    
admin.site.register(EconomicResourceType, EconomicResourceTypeAdmin)


class AgentResourceTypeAdmin(admin.ModelAdmin):
    list_display = ('agent', 'resource_type', 'score', 'event_type', 'relationship')
    list_filter = ['event_type', 'agent', 'resource_type']
    
admin.site.register(AgentResourceType, AgentResourceTypeAdmin)


class ProcessTypeResourceTypeAdmin(admin.ModelAdmin):
    list_display = ('process_type', 'resource_type', 'event_type', 'unit_of_quantity')
    list_filter = ['event_type', 'process_type', 'resource_type']
    search_fields = ['process_type__name','resource_type__name',]
    
admin.site.register(ProcessTypeResourceType, ProcessTypeResourceTypeAdmin)


class ProcessTypeResourceTypeInline(admin.TabularInline):
    model = ProcessTypeResourceType


class ProcessTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'project' )
    list_filter = ['project',]
    search_fields = ['name',]
    inlines = [ ProcessTypeResourceTypeInline, ]

admin.site.register(ProcessType, ProcessTypeAdmin)


class EventTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'label', 'inverse_label', 'related_to', 'relationship', 'resource_effect', 'unit_type' )
    list_filter = ['resource_effect', 'related_to', 'relationship',]
    list_editable = ['label', 'inverse_label', 'related_to', 'relationship']

admin.site.register(EventType, EventTypeAdmin)


class EconomicResourceAdmin(admin.ModelAdmin):
    list_display = ('id', 'identifier', 'resource_type', 'quantity', 'unit_of_quantity', 'quality', 'notes', 'owner', 'custodian')
    list_filter = ['resource_type', 'author', 'owner']
    search_fields = ['identifier', 'resource_type__name']
    date_hierarchy = 'created_date'
    
admin.site.register(EconomicResource, EconomicResourceAdmin)


class CommitmentInline(admin.TabularInline):
    model = Commitment


class OrderItemInline(admin.TabularInline):
    model = Commitment
    fk_name = 'order'
    fields = ('event_type', 'due_date', 'resource_type', 'quantity', 'unit_of_quantity', 'process')


class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'provider', 'receiver', 'description','due_date' )
    inlines = [ OrderItemInline, ]

admin.site.register(Order, OrderAdmin)


class ProcessAdmin(admin.ModelAdmin):
    date_hierarchy = 'start_date'
    list_display = ('name', 'start_date', 'end_date', 'finished', 'process_type', 'project', 'owner', 'managed_by')
    list_filter = ['process_type', 'finished', 'owner', 'managed_by']
    search_fields = ['name', 'process_type__name', 'owner__name', 'managed_by__name']
    inlines = [ CommitmentInline, ]
    
admin.site.register(Process, ProcessAdmin)

class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent')
    list_filter = ['parent',]
    search_fields = ['name',]
    
admin.site.register(Project, ProjectAdmin)


class CommitmentAdmin(admin.ModelAdmin):
    date_hierarchy = 'due_date'
    list_display = ('resource_type', 'quantity', 'unit_of_quantity', 'event_type', 'due_date', 'finished', 'from_agent', 'process', 'project', 'order', 'independent_demand',  
        'description')
    list_filter = ['independent_demand', 'event_type', 'resource_type', 'from_agent', 'project']
    search_fields = ['event_type__name', 'from_agent__name', 'to_agent__name', 'resource_type__name']
    
admin.site.register(Commitment, CommitmentAdmin)


class EconomicEventAdmin(admin.ModelAdmin):
    date_hierarchy = 'event_date'
    list_display = ('event_type', 'event_date', 'from_agent', 'project', 
        'resource_type', 'quantity', 'unit_of_quantity', 'description', 'url', 'quality')
    list_filter = ['event_type', 'project', 'resource_type', 'from_agent', ]
    search_fields = ['event_type__name', 'from_agent__name', 'to_agent__name', 'resource_type__name']
    list_editable = ['event_date',]
    
admin.site.register(EconomicEvent, EconomicEventAdmin)


class CompensationAdmin(admin.ModelAdmin):
    list_display = ('initiating_event', 'compensating_event', 'compensation_date', 'compensating_value')
    search_fields = ['initiating_event__from_agent__name', 'initiating_event__to_agent__name']
    
admin.site.register(Compensation, CompensationAdmin)


