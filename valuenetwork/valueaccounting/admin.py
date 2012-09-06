from django.contrib import admin
from valuenetwork.valueaccounting.models import *
from valuenetwork.valueaccounting.actions import export_as_csv

admin.site.add_action(export_as_csv, 'export_selected objects')

admin.site.register(Unit)
admin.site.register(ValueEquation)
admin.site.register(AgentType)
admin.site.register(ProcessType)
admin.site.register(EventType)
admin.site.register(Role)


class EconomicAgentAdmin(admin.ModelAdmin):
    list_display = ('name', 'agent_type', 'description', 'address')
    list_filter = ['agent_type',]
    search_fields = ['name', 'address']
    
admin.site.register(EconomicAgent, EconomicAgentAdmin)


class EconomicResourceTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent')
    list_filter = ['parent',]
    search_fields = ['name',]
    
admin.site.register(EconomicResourceType, EconomicResourceTypeAdmin)


class EconomicResourceAdmin(admin.ModelAdmin):
    list_display = ('identifier', 'resource_type', 'owner', 'custodian')
    list_filter = ['owner', 'custodian']
    search_fields = ['identifier', 'resource_type__name']
    
admin.site.register(EconomicResource, EconomicResourceAdmin)


class ProcessAdmin(admin.ModelAdmin):
    date_hierarchy = 'start_date'
    list_display = ('name', 'start_date', 'end_date', 'process_type', 'owner', 'managed_by')
    list_filter = ['process_type', 'owner', 'managed_by']
    search_fields = ['name', 'process_type__name', 'owner__name', 'managed_by__name']
    
admin.site.register(Process, ProcessAdmin)


class EconomicEventAdmin(admin.ModelAdmin):
    date_hierarchy = 'event_date'
    list_display = ('event_type', 'event_date', 'from_agent', 'to_agent', 'resource_type', 'resource', 'process', 'amount')
    list_filter = ['event_type', 'from_agent', 'to_agent', 'resource_type', 'process',]
    search_fields = ['name', 'event_type__name', 'from_agent__name', 'to_agent__name', 'resource_type__name']
    
admin.site.register(EconomicEvent, EconomicEventAdmin)

